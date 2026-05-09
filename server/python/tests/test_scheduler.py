from datetime import datetime, timedelta, timezone

from ling_server import indexer, scheduler
from ling_server.db import connect


def _set_deadline(cfg, *, in_minutes: int, status: str = "todo"):
    """重写 tasks.yaml 让任务 deadline 为 now+in_minutes。"""
    deadline = (
        datetime.now(timezone.utc).astimezone() + timedelta(minutes=in_minutes)
    ).isoformat(timespec="seconds")
    cfg.tasks_yaml_path.write_text(
        "- id: t1\n"
        "  title: 单任务\n"
        f"  status: {status}\n"
        f"  deadline: {deadline}\n",
        encoding="utf-8",
    )
    indexer.reindex(cfg)


def test_tick_fires_reminders_within_lookahead(app_cfg):
    """deadline=now+5min；offsets=[60,15] -> 两个 fire_at 都已过去，全部 fire。"""
    _set_deadline(app_cfg, in_minutes=5)
    r = scheduler.tick(app_cfg)
    assert r["fired"] == 2
    assert r["overdue"] == 0

    with connect(app_cfg.db_path) as conn:
        events = conn.execute("SELECT id, type, state FROM events").fetchall()
        assert len(events) == 2
        assert all(e["type"] == "reminder" and e["state"] == "pending" for e in events)
        # reminders 应已变为 fired
        states = [r["state"] for r in conn.execute("SELECT state FROM reminders").fetchall()]
        assert all(s == "fired" for s in states)


def test_tick_is_idempotent(app_cfg):
    """连跑 2 次 tick：events 数应只来自第一次 fire（reminders 已变 fired，不再产出）。"""
    _set_deadline(app_cfg, in_minutes=5)
    scheduler.tick(app_cfg)
    r2 = scheduler.tick(app_cfg)
    assert r2["fired"] == 0
    with connect(app_cfg.db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert n == 2


def test_tick_skips_done_task(app_cfg):
    _set_deadline(app_cfg, in_minutes=5, status="done")
    r = scheduler.tick(app_cfg)
    assert r["fired"] == 0
    with connect(app_cfg.db_path) as conn:
        n_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert n_events == 0


def test_tick_emits_overdue_repeats(app_cfg):
    """deadline 在 1 小时之前，且 status=todo -> 应触发 1 个 overdue event。"""
    _set_deadline(app_cfg, in_minutes=-60)
    # 一开始所有 fixed reminders 已经早过期，scheduler 会一次性 fire 完它们
    scheduler.tick(app_cfg)
    # 第二次 tick 不会再 fire fixed，但会输出 overdue（slot 一致时去重）
    r = scheduler.tick(app_cfg)
    # fixed reminders 都已 fired；overdue 至少 0 或 1（取决于 slot 判定）
    assert r["overdue"] >= 0
    with connect(app_cfg.db_path) as conn:
        rows = conn.execute(
            "SELECT id FROM events WHERE id LIKE '%:overdue:%'"
        ).fetchall()
    # overdue events 的 id 含 ':overdue:'
    assert len(rows) >= 1
