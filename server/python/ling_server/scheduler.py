"""ReminderScheduler：把 reminders -> events（pending）。

事件 id 设计为稳定可预测：
- fixed reminder: ${task_id}:${fire_at}
- overdue repeat: ${task_id}:overdue:${floor(now/overdue_repeat_minutes)}

每个新生成的 event 都会触发一次 FCM 推送（如启用）。即使推送失败，
event 仍然会留在 events 表里，App 端轮询 fallback 仍可拿到。
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dateutil import parser as dtparser

from . import fcm as fcm_mod
from .config import AppConfig, load_ops_config
from .db import connect, init_db


log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def _parse_iso(s: str) -> datetime:
    dt = dtparser.parse(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _list_devices(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT device_id, fcm_token, platform FROM devices"
    ).fetchall()


def _fcm_push_for_event(
    conn: sqlite3.Connection,
    sender: fcm_mod.FcmSender,
    event_id: str,
    payload: Dict[str, Any],
) -> None:
    devices = _list_devices(conn)
    if not devices:
        return
    title = (payload.get("title") or payload.get("task_id") or "提醒").strip()
    if payload.get("overdue"):
        title = f"已超期 · {title}"
    body_parts = []
    if payload.get("deadline"):
        body_parts.append(f"截止：{payload['deadline']}")
    if payload.get("fire_at"):
        body_parts.append(f"提醒：{payload['fire_at']}")
    body = " · ".join(body_parts)
    data = {
        "event_id": event_id,
        "task_id": str(payload.get("task_id", "")),
        "deadline": str(payload.get("deadline") or ""),
        "fire_at": str(payload.get("fire_at") or ""),
        "overdue": "1" if payload.get("overdue") else "0",
    }
    msgs = [
        fcm_mod.FcmMessage(token=d["fcm_token"], title=title, body=body, data=data)
        for d in devices
    ]
    results = sender.send_many(msgs)
    now_iso = _now().isoformat(timespec="seconds")
    for d, r in zip(devices, results):
        conn.execute(
            "INSERT INTO push_log(event_id, device_id, ok, detail, created_at) VALUES(?,?,?,?,?)",
            (event_id, d["device_id"], 1 if r.ok else 0, r.detail, now_iso),
        )


def tick(cfg: AppConfig, sender: Optional[fcm_mod.FcmSender] = None) -> Dict[str, Any]:
    """跑一次扫描：把命中 fire_at 的 reminders 转成 events.pending。

    sender 可注入；缺省按 cfg.fcm 自动构建（生产路径）。
    """
    init_db(cfg.db_path)
    ops = load_ops_config(cfg.workdir)
    now = _now()
    lookahead = cfg.scheduler.lookahead_seconds
    overdue_min = ops.overdue_repeat_minutes or cfg.scheduler.overdue_repeat_minutes
    horizon = now + timedelta(seconds=lookahead)

    if sender is None:
        sender = fcm_mod.build_sender(
            enabled=cfg.fcm.enabled,
            project_id=cfg.fcm.project_id,
            service_account=cfg.fcm.service_account,
        )

    fired = 0
    overdue_emitted = 0
    pushed = 0

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
            payload_dict = {
                "task_id": task["id"],
                "title": task["title"],
                "deadline": task["deadline"],
                "fire_at": row["fire_at"],
                "overdue": False,
            }
            payload = json.dumps(payload_dict, ensure_ascii=False)
            cur.execute(
                "INSERT OR IGNORE INTO events(id,type,payload,state,created_at) "
                "VALUES(?, 'reminder', ?, 'pending', ?)",
                (event_id, payload, now.isoformat(timespec="seconds")),
            )
            inserted = cur.rowcount
            cur.execute("UPDATE reminders SET state='fired' WHERE id=?", (row["id"],))
            fired += 1
            if inserted:
                _fcm_push_for_event(conn, sender, event_id, payload_dict)
                pushed += 1

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
                payload_dict = {
                    "task_id": task["id"],
                    "title": task["title"],
                    "deadline": task["deadline"],
                    "fire_at": now.isoformat(timespec="seconds"),
                    "overdue": True,
                }
                payload = json.dumps(payload_dict, ensure_ascii=False)
                cur.execute(
                    "INSERT OR IGNORE INTO events(id,type,payload,state,created_at) "
                    "VALUES(?, 'reminder', ?, 'pending', ?)",
                    (event_id, payload, now.isoformat(timespec="seconds")),
                )
                if cur.rowcount > 0:
                    overdue_emitted += 1
                    _fcm_push_for_event(conn, sender, event_id, payload_dict)
                    pushed += 1

    log.info("scheduler tick: fired=%d overdue=%d pushed=%d", fired, overdue_emitted, pushed)
    return {
        "fired": fired,
        "overdue": overdue_emitted,
        "pushed": pushed,
        "ts": now.isoformat(timespec="seconds"),
    }
