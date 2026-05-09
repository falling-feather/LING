"""tasks.yaml 解析器（一期）。

读取 MemoryWorkdir/tasks.yaml -> 写入 SQLite tasks/reminders 表。
触发条件：
- 显式调用 reindex()（API 与 syncd 在 git 变更后调用）
- 或 indexer CLI（python -m ling_server.cli index）
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from dateutil import parser as dtparser

from .config import AppConfig, load_ops_config
from .db import connect, init_db, set_state


log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _hash_task(item: Dict[str, Any]) -> str:
    blob = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).strip()
    if not s:
        return None
    try:
        dt = dtparser.parse(s)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_tasks_yaml(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise ValueError(f"tasks.yaml top-level must be a list, got {type(data).__name__}")
    out: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if "id" not in item or "title" not in item:
            continue
        item.setdefault("status", "todo")
        out.append(item)
    return out


def reindex(cfg: AppConfig) -> Dict[str, Any]:
    """读取 tasks.yaml 全量重建 tasks/reminders 表。"""
    init_db(cfg.db_path)
    ops = load_ops_config(cfg.workdir)
    items = load_tasks_yaml(cfg.tasks_yaml_path)
    log.info("indexing %d tasks from %s", len(items), cfg.tasks_yaml_path)

    now_iso = _now_iso()
    seen_ids: List[str] = []

    with connect(cfg.db_path) as conn:
        cur = conn.cursor()
        for item in items:
            tid = str(item["id"])
            seen_ids.append(tid)
            deadline_dt = _parse_dt(item.get("deadline"))
            deadline_iso = deadline_dt.isoformat(timespec="seconds") if deadline_dt else None
            cur.execute(
                "INSERT INTO tasks(id,title,status,deadline,notes,source,updated_at,raw_hash) "
                "VALUES(?,?,?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET title=excluded.title, status=excluded.status, "
                "deadline=excluded.deadline, notes=excluded.notes, source=excluded.source, "
                "updated_at=excluded.updated_at, raw_hash=excluded.raw_hash",
                (
                    tid,
                    str(item.get("title", "")),
                    str(item.get("status", "todo")),
                    deadline_iso,
                    item.get("notes"),
                    "tasks.yaml",
                    now_iso,
                    _hash_task(item),
                ),
            )

        # 删除 yaml 中已不存在的任务
        if seen_ids:
            placeholders = ",".join(["?"] * len(seen_ids))
            cur.execute(f"DELETE FROM tasks WHERE id NOT IN ({placeholders})", seen_ids)
        else:
            cur.execute("DELETE FROM tasks")

        # 全量重建 reminders（一期简化做法）
        cur.execute("DELETE FROM reminders")
        offsets = ops.default_remind_offsets_minutes or []
        rebuilt = 0
        for item in items:
            if str(item.get("status", "todo")).lower() == "done":
                continue
            deadline_dt = _parse_dt(item.get("deadline"))
            if deadline_dt is None:
                continue
            tid = str(item["id"])
            for off in offsets:
                fire_at = deadline_dt - timedelta(minutes=int(off))
                rid = f"{tid}:{fire_at.isoformat(timespec='seconds')}"
                cur.execute(
                    "INSERT INTO reminders(id,task_id,fire_at,state) VALUES(?,?,?,?)",
                    (rid, tid, fire_at.isoformat(timespec="seconds"), "pending"),
                )
                rebuilt += 1

        set_state(conn, "last_index_time", now_iso)

    log.info("reindex done: tasks=%d reminders=%d", len(items), rebuilt)
    return {"tasks": len(items), "reminders": rebuilt, "indexed_at": now_iso}
