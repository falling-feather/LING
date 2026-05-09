"""GitSyncDaemon：定时心跳同步 + 触发 Indexer。

简化版：复用 APScheduler。
- BackgroundScheduler 心跳：sync_interval_hours
- 第二个 job：每 poll_interval_seconds 跑一次 reminder tick（让提醒事件不依赖 4 小时心跳）
"""

from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from . import gitwork, indexer, scheduler
from .config import AppConfig
from .db import connect, init_db, set_state


log = logging.getLogger(__name__)


def _git_cfg(cfg: AppConfig) -> gitwork.GitConfig:
    return gitwork.GitConfig(
        workdir=cfg.workdir,
        repo_url=cfg.memory_repo.repo_url,
        branch=cfg.memory_repo.branch,
        author_name=cfg.memory_repo.git_author_name,
        author_email=cfg.memory_repo.git_author_email,
        token_env=cfg.memory_repo.github_token_env,
    )


def sync_once(cfg: AppConfig) -> Any:
    init_db(cfg.db_path)
    g = _git_cfg(cfg)
    try:
        gitwork.ensure_repo(g)
        try:
            gitwork.pull_rebase(g)
        except gitwork.GitError as e:
            log.warning("pull --rebase failed (will continue with local): %s", e)
        head = gitwork.get_head_sha(g) or ""
    except gitwork.GitError as e:
        log.error("git sync failed: %s", e)
        return {"ok": False, "error": str(e)}

    with connect(cfg.db_path) as conn:
        prev = conn.execute("SELECT value FROM workdir_state WHERE key='last_git_sha'").fetchone()
        prev_sha = prev["value"] if prev else None
        set_state(conn, "last_git_sha", head)
    changed = head != (prev_sha or "")
    if changed or not cfg.tasks_yaml_path.exists():
        indexer.reindex(cfg)
    scheduler.tick(cfg)
    return {"ok": True, "head": head, "changed": changed}


def start_background(cfg: AppConfig) -> BackgroundScheduler:
    sch = BackgroundScheduler(timezone="UTC")
    sch.add_job(
        sync_once,
        "interval",
        hours=cfg.scheduler.sync_interval_hours,
        args=[cfg],
        id="git-sync",
        next_run_time=None,  # 启动时不立刻跑（main 里会先手动跑一次）
        max_instances=1,
        coalesce=True,
    )
    sch.add_job(
        scheduler.tick,
        "interval",
        seconds=cfg.scheduler.poll_interval_seconds,
        args=[cfg],
        id="reminder-tick",
        max_instances=1,
        coalesce=True,
    )
    sch.start()
    log.info(
        "background scheduler started: sync every %dh, tick every %ds",
        cfg.scheduler.sync_interval_hours,
        cfg.scheduler.poll_interval_seconds,
    )
    return sch
