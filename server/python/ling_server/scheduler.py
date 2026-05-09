"""ReminderScheduler：把 reminders -> events（pending）。

事件 id 设计为稳定可预测：
- fixed reminder: ${task_id}:${fire_at}
- overdue repeat: ${task_id}:overdue:${floor(now/overdue_repeat_minutes)}
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from dateutil import parser as dtparser

from .config import AppConfig, load_ops_config
from .db import connect, init_db


log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def _parse_iso(s: str) -> datetime:
    dt = dtparser.parse(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def tick(cfg: AppConfig) -> Dict[str, Any]:
    """跑一次扫描：把命中 fire_at 的 reminders 转成 events.pending。"""
    init_db(cfg.db_path)
    ops = load_ops_config(cfg.workdir)
    now = _now()
    lookahead = cfg.scheduler.lookahead_seconds
    overdue_min = ops.overdue_repeat_minutes or cfg.scheduler.overdue_repeat_minutes
    horizon = now + timedelta(seconds=lookahead)

    fired = 0
    overdue_emitted = 0

    with connect(cfg.db_path) as conn:
        cur = conn.cursor()
        # 1) fixed reminders
        rows = cur.execute(
            "SELECT id, task_id, fire_at FROM reminders "
            "WHERE state='pending' AND fire_at <= ? ORDER BY fire_at ASC",
            (horizon.isoformat(timespec="seconds"),),
        ).fetchall()
        for row in rows:
            task = cur.execute(
                "SELECT id,title,deadline,status FROM tasks WHERE id=?",
                (row["task_id"],),
            ).fetchone()
            if task is None:
                cur.execute("UPDATE reminders SET state='cancelled' WHERE id=?", (row["id"],))
                continue
            if str(task["status"]).lower() == "done":
                cur.execute("UPDATE reminders SET state='cancelled' WHERE id=?", (row["id"],))
                continue
            event_id = f"{task['id']}:{row['fire_at']}"
            payload = json.dumps(
                {
                    "task_id": task["id"],
                    "title": task["title"],
                    "deadline": task["deadline"],
                    "fire_at": row["fire_at"],
                    "overdue": False,
                },
                ensure_ascii=False,
            )
            cur.execute(
                "INSERT OR IGNORE INTO events(id,type,payload,state,created_at) "
                "VALUES(?, 'reminder', ?, 'pending', ?)",
                (event_id, payload, now.isoformat(timespec="seconds")),
            )
            cur.execute("UPDATE reminders SET state='fired' WHERE id=?", (row["id"],))
            fired += 1

        # 2) overdue repeats
        if overdue_min > 0:
            slot = int(now.timestamp() // (overdue_min * 60))
            overdue_tasks = cur.execute(
                "SELECT id,title,deadline,status FROM tasks "
                "WHERE deadline IS NOT NULL AND status != 'done'"
            ).fetchall()
            for task in overdue_tasks:
                try:
                    dl = _parse_iso(task["deadline"])
                except Exception:
                    continue
                if dl >= now:
                    continue
                event_id = f"{task['id']}:overdue:{slot}"
                payload = json.dumps(
                    {
                        "task_id": task["id"],
                        "title": task["title"],
                        "deadline": task["deadline"],
                        "fire_at": now.isoformat(timespec="seconds"),
                        "overdue": True,
                    },
                    ensure_ascii=False,
                )
                cur.execute(
                    "INSERT OR IGNORE INTO events(id,type,payload,state,created_at) "
                    "VALUES(?, 'reminder', ?, 'pending', ?)",
                    (event_id, payload, now.isoformat(timespec="seconds")),
                )
                if cur.rowcount > 0:
                    overdue_emitted += 1

    log.info("scheduler tick: fired=%d overdue=%d", fired, overdue_emitted)
    return {"fired": fired, "overdue": overdue_emitted, "ts": now.isoformat(timespec="seconds")}
