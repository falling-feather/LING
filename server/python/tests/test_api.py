"""测试 HTTP API 主流程；不进行真实 git push。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ling_server import indexer
from ling_server.api import create_app


@pytest.fixture
def client(app_cfg):
    indexer.reindex(app_cfg)
    app = create_app(app_cfg, push_on_write=False)
    with app.test_client() as c:
        yield c


HEADERS = {"X-API-Key": "test-key"}


def test_healthz_no_auth(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}


def test_protected_endpoints_require_key(client):
    assert client.get("/tasks").status_code == 401
    assert client.post("/capture").status_code == 401


def test_list_and_get_task(client):
    r = client.get("/tasks", headers=HEADERS)
    assert r.status_code == 200
    tasks = r.get_json()
    assert isinstance(tasks, list) and len(tasks) == 1
    tid = tasks[0]["id"]

    r = client.get(f"/tasks/{tid}", headers=HEADERS)
    assert r.status_code == 200
    assert r.get_json()["id"] == tid

    r = client.get("/tasks/no-such", headers=HEADERS)
    assert r.status_code == 404


def test_complete_writes_yaml(client, app_cfg):
    r = client.post("/tasks/t-soon/complete", headers=HEADERS)
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    text = app_cfg.tasks_yaml_path.read_text(encoding="utf-8")
    assert "status: done" in text


def test_capture_appends_file(client, app_cfg):
    r = client.post("/capture", headers=HEADERS, json={"text": "hello 中文"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    text = app_cfg.capture_md_path.read_text(encoding="utf-8")
    assert "- hello 中文" in text


def test_capture_requires_text(client):
    r = client.post("/capture", headers=HEADERS, json={"text": "  "})
    assert r.status_code == 400


def test_snooze_creates_event(client):
    r = client.post("/tasks/t-soon/snooze", headers=HEADERS, json={"minutes": 30})
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True and "fire_at" in body


def test_reschedule_updates_yaml(client, app_cfg):
    new_deadline = (
        datetime.now(timezone.utc).astimezone() + timedelta(days=2)
    ).isoformat(timespec="seconds")
    r = client.post(
        "/tasks/t-soon/reschedule",
        headers=HEADERS,
        json={"deadline": new_deadline},
    )
    assert r.status_code == 200
    text = app_cfg.tasks_yaml_path.read_text(encoding="utf-8")
    # YAML 输出可能去掉 'T'，但日期片段一定在
    assert new_deadline[:10] in text


def test_reschedule_rejects_bad_deadline(client):
    r = client.post(
        "/tasks/t-soon/reschedule",
        headers=HEADERS,
        json={"deadline": "not-a-date"},
    )
    assert r.status_code == 400


def test_pending_reminders_returns_and_marks_delivered(client):
    """t-soon deadline=5min, offsets=[60,15] => 应有 2 条 pending；二次拉取应为空。"""
    r = client.get("/reminders/pending?limit=20", headers=HEADERS)
    assert r.status_code == 200
    pendings = r.get_json()
    assert len(pendings) == 2
    assert all(p["state"] == "pending" for p in pendings)

    r = client.get("/reminders/pending?limit=20", headers=HEADERS)
    assert r.status_code == 200
    assert r.get_json() == []
