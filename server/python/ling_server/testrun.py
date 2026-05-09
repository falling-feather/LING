"""本地端到端冒烟测试。

不依赖远端 GitHub：把 cfg.workdir 当作普通目录跑一遍 index/tick/api。
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from . import indexer, scheduler, yamlio
from .api import create_app
from .config import AppConfig
from .db import connect


log = logging.getLogger(__name__)


def _ensure_workdir_skeleton(workdir: Path) -> None:
    """如果 workdir 是空的，写入最小骨架（用于纯本地 smoke test）。"""
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "ops").mkdir(exist_ok=True)
    (workdir / "inbox").mkdir(exist_ok=True)
    (workdir / "index").mkdir(exist_ok=True)
    if not (workdir / "ops" / "config.yaml").exists():
        (workdir / "ops" / "config.yaml").write_text(
            "timezone: \"Asia/Shanghai\"\n"
            "sync_interval_hours: 4\n"
            "poll_interval_seconds: 60\n"
            "default_remind_offsets_minutes: [60, 15]\n"
            "overdue_repeat_minutes: 240\n",
            encoding="utf-8",
        )
    if not (workdir / "tasks.yaml").exists():
        soon = (datetime.now(timezone.utc).astimezone() + timedelta(minutes=12)).isoformat(timespec="seconds")
        future = (datetime.now(timezone.utc).astimezone() + timedelta(days=1)).isoformat(timespec="seconds")
        items = [
            {
                "id": "smoke-1",
                "title": "冒烟任务A：12分钟后到期",
                "status": "todo",
                "deadline": soon,
                "notes": "scheduler 应该立刻产生一个 reminder event",
            },
            {
                "id": "smoke-2",
                "title": "冒烟任务B：明天到期",
                "status": "todo",
                "deadline": future,
                "notes": "应有多个未来 reminder 计划",
            },
        ]
        yamlio.dump_tasks(workdir / "tasks.yaml", items)
    if not (workdir / "inbox" / "capture.md").exists():
        (workdir / "inbox" / "capture.md").write_text("## capture\n\n", encoding="utf-8")


def run_smoke_test(cfg: AppConfig) -> int:
    print("=== smoke test: workdir =", cfg.workdir)
    _ensure_workdir_skeleton(cfg.workdir)

    print("\n[1] reindex")
    r1 = indexer.reindex(cfg)
    print("   ", r1)

    print("\n[2] scheduler.tick")
    r2 = scheduler.tick(cfg)
    print("   ", r2)

    print("\n[3] DB stats")
    with connect(cfg.db_path) as conn:
        for tbl in ("tasks", "reminders", "events"):
            n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            print(f"    {tbl}: {n}")

    print("\n[4] API in-process test")
    app = create_app(cfg, push_on_write=False)
    client = app.test_client()
    headers = {"X-API-Key": cfg.server.api_key}

    r = client.get("/healthz")
    print("    GET /healthz ->", r.status_code, r.get_json())

    r = client.get("/tasks", headers=headers)
    print("    GET /tasks ->", r.status_code)
    tasks = r.get_json()
    for t in tasks:
        print("      -", t["id"], t["title"], t["status"], t.get("deadline"))

    r = client.get("/reminders/pending?limit=5", headers=headers)
    print("    GET /reminders/pending ->", r.status_code)
    pendings = r.get_json()
    for p in pendings:
        print("      *", p.get("event_id"), p.get("task_id"), p.get("fire_at"), "overdue=", p.get("overdue"))

    r = client.post("/capture", headers=headers, json={"text": "smoke test capture line"})
    print("    POST /capture ->", r.status_code, r.get_json())

    r = client.post("/tasks/smoke-1/complete", headers=headers)
    print("    POST /tasks/smoke-1/complete ->", r.status_code, r.get_json())

    print("\n[5] verify writes on disk")
    print("    tasks.yaml ->")
    for line in (cfg.tasks_yaml_path.read_text(encoding="utf-8")).splitlines():
        print("      |", line)
    print("    capture.md ->")
    for line in (cfg.capture_md_path.read_text(encoding="utf-8")).splitlines():
        print("      |", line)

    return 0
