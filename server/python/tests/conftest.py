"""共享 fixture。

每个测试得到一个独立、临时的 workdir + db_path，互不影响。
所有需要远端 git 的能力都关闭（push_on_write=False / repo_url=""）。
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ling_server.config import (  # noqa: E402  (after sys.path tweak)
    AppConfig,
    IndexConfig,
    MemoryRepoConfig,
    OpsConfig,
    SchedulerConfig,
    ServerConfig,
)


def make_workdir(base: Path, *, with_demo_task: bool = True) -> Path:
    """搭建一个最小化的 MemoryWorkdir 文件结构。"""
    base.mkdir(parents=True, exist_ok=True)
    (base / "ops").mkdir(exist_ok=True)
    (base / "inbox").mkdir(exist_ok=True)
    (base / "index").mkdir(exist_ok=True)

    (base / "ops" / "config.yaml").write_text(
        "timezone: \"Asia/Shanghai\"\n"
        "sync_interval_hours: 4\n"
        "poll_interval_seconds: 60\n"
        "default_remind_offsets_minutes: [60, 15]\n"
        "overdue_repeat_minutes: 240\n",
        encoding="utf-8",
    )
    (base / "inbox" / "capture.md").write_text("## capture\n\n", encoding="utf-8")

    if with_demo_task:
        soon = (datetime.now(timezone.utc).astimezone() + timedelta(minutes=5)).isoformat(
            timespec="seconds"
        )
        (base / "tasks.yaml").write_text(
            "- id: t-soon\n"
            "  title: 5 分钟后到期\n"
            "  status: todo\n"
            f"  deadline: {soon!s}\n"
            "  notes: 立即触发 reminder\n",
            encoding="utf-8",
        )
    else:
        (base / "tasks.yaml").write_text("[]\n", encoding="utf-8")
    return base


@pytest.fixture
def app_cfg(tmp_path: Path) -> AppConfig:
    workdir = make_workdir(tmp_path / "workdir")
    cfg = AppConfig()
    cfg.server = ServerConfig(host="127.0.0.1", port=0, api_key="test-key")
    cfg.memory_repo = MemoryRepoConfig(
        workdir_path=workdir,
        repo_url="",
        branch="main",
    )
    cfg.scheduler = SchedulerConfig(
        sync_interval_hours=4,
        poll_interval_seconds=60,
        lookahead_seconds=120,
        overdue_repeat_minutes=240,
    )
    cfg.index = IndexConfig(db_path=workdir / "index" / "db.sqlite")
    cfg.ops = OpsConfig()
    return cfg
