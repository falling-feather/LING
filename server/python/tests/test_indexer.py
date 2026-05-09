from datetime import datetime, timedelta, timezone

from ling_server import indexer
from ling_server.db import connect


def test_reindex_creates_tasks_and_reminders(app_cfg):
    """tasks.yaml 中 1 个 todo 任务、deadline 5 分钟后；offsets = [60, 15] -> 2 条 reminders。"""
    r = indexer.reindex(app_cfg)
    assert r["tasks"] == 1
    assert r["reminders"] == 2

    with connect(app_cfg.db_path) as conn:
        rows = conn.execute("SELECT id, status, deadline FROM tasks").fetchall()
        assert len(rows) == 1
        assert rows[0]["status"] == "todo"
        rs = conn.execute("SELECT task_id, fire_at, state FROM reminders").fetchall()
        assert len(rs) == 2
        assert all(r["state"] == "pending" for r in rs)


def test_reindex_skips_done_tasks(app_cfg):
    cfg = app_cfg
    cfg.tasks_yaml_path.write_text(
        "- id: t1\n  title: t1\n  status: done\n"
        "  deadline: 2026-05-11T10:00:00+08:00\n",
        encoding="utf-8",
    )
    r = indexer.reindex(cfg)
    assert r["tasks"] == 1
    assert r["reminders"] == 0  # done 任务不生成 reminders


def test_reindex_drops_removed_tasks(app_cfg):
    cfg = app_cfg
    indexer.reindex(cfg)
    cfg.tasks_yaml_path.write_text("[]\n", encoding="utf-8")
    indexer.reindex(cfg)

    with connect(cfg.db_path) as conn:
        n_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        n_reminders = conn.execute("SELECT COUNT(*) FROM reminders").fetchone()[0]
    assert n_tasks == 0
    assert n_reminders == 0


def test_reindex_no_deadline_no_reminders(app_cfg):
    cfg = app_cfg
    cfg.tasks_yaml_path.write_text(
        "- id: t1\n  title: 无 deadline\n  status: todo\n",
        encoding="utf-8",
    )
    r = indexer.reindex(cfg)
    assert r["tasks"] == 1
    assert r["reminders"] == 0


def test_load_tasks_yaml_empty(tmp_path):
    p = tmp_path / "tasks.yaml"
    p.write_text("", encoding="utf-8")
    assert indexer.load_tasks_yaml(p) == []


def test_load_tasks_yaml_skips_invalid_items(tmp_path):
    p = tmp_path / "tasks.yaml"
    p.write_text(
        "- id: ok\n"
        "  title: T\n"
        "- 'not a dict'\n"
        "- id: missing-title\n",
        encoding="utf-8",
    )
    items = indexer.load_tasks_yaml(p)
    assert [i["id"] for i in items] == ["ok"]
