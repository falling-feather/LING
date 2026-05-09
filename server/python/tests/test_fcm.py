from datetime import datetime, timedelta, timezone

from ling_server import fcm, indexer, scheduler
from ling_server.api import create_app
from ling_server.db import connect


HEADERS = {"X-API-Key": "test-key"}


def test_build_sender_disabled():
    s = fcm.build_sender(enabled=False, project_id="x", service_account="x")
    assert isinstance(s, fcm.NullFcmSender)


def test_build_sender_missing_credentials():
    s = fcm.build_sender(enabled=True, project_id="", service_account="")
    assert isinstance(s, fcm.NullFcmSender)


def test_build_sender_missing_file(tmp_path):
    s = fcm.build_sender(
        enabled=True,
        project_id="proj",
        service_account=str(tmp_path / "missing.json"),
    )
    assert isinstance(s, fcm.NullFcmSender)


def test_in_memory_sender_records():
    s = fcm.InMemoryFcmSender()
    r = s.send(fcm.FcmMessage(token="abc", title="t", body="b", data={"x": "1"}))
    assert r.ok and r.token == "abc"
    assert len(s.sent) == 1
    assert s.sent[0].data == {"x": "1"}


def test_register_device_endpoint(app_cfg):
    indexer.reindex(app_cfg)
    app = create_app(app_cfg, push_on_write=False, fcm_sender=fcm.InMemoryFcmSender())
    with app.test_client() as c:
        r = c.post(
            "/devices/register",
            headers=HEADERS,
            json={"device_id": "dev-1", "fcm_token": "tok-1", "label": "phone-A"},
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["ok"] and body["device_id"] == "dev-1"

        # 重复注册（更新 token）
        r2 = c.post(
            "/devices/register",
            headers=HEADERS,
            json={"device_id": "dev-1", "fcm_token": "tok-2"},
        )
        assert r2.status_code == 200

    with connect(app_cfg.db_path) as conn:
        rows = conn.execute("SELECT device_id, fcm_token FROM devices").fetchall()
        assert len(rows) == 1
        assert rows[0]["fcm_token"] == "tok-2"


def test_register_requires_fields(app_cfg):
    app = create_app(app_cfg, push_on_write=False, fcm_sender=fcm.InMemoryFcmSender())
    with app.test_client() as c:
        r = c.post("/devices/register", headers=HEADERS, json={"device_id": "x"})
        assert r.status_code == 400


def test_test_push_records_in_log(app_cfg):
    sender = fcm.InMemoryFcmSender()
    app = create_app(app_cfg, push_on_write=False, fcm_sender=sender)
    with app.test_client() as c:
        c.post(
            "/devices/register",
            headers=HEADERS,
            json={"device_id": "d1", "fcm_token": "t1"},
        )
        c.post(
            "/devices/register",
            headers=HEADERS,
            json={"device_id": "d2", "fcm_token": "t2"},
        )
        r = c.post("/devices/test_push", headers=HEADERS, json={"title": "hi", "body": "yo"})
        assert r.status_code == 200
        body = r.get_json()
        assert body["devices"] == 2
        assert all(x["ok"] for x in body["results"])

    assert {m.token for m in sender.sent} == {"t1", "t2"}
    assert all(m.title == "hi" for m in sender.sent)

    with connect(app_cfg.db_path) as conn:
        rows = conn.execute(
            "SELECT event_id, device_id, ok FROM push_log WHERE event_id='test'"
        ).fetchall()
        assert len(rows) == 2
        assert all(r["ok"] == 1 for r in rows)


def test_test_push_no_devices(app_cfg):
    sender = fcm.InMemoryFcmSender()
    app = create_app(app_cfg, push_on_write=False, fcm_sender=sender)
    with app.test_client() as c:
        r = c.post("/devices/test_push", headers=HEADERS)
        assert r.status_code == 200
        assert r.get_json()["devices"] == 0
    assert sender.sent == []


def test_scheduler_pushes_on_fire(app_cfg):
    """deadline=5min, offsets=[60,15] => 2 fire；注册了 1 个设备 => 应有 2 条 push 记录。"""
    indexer.reindex(app_cfg)
    sender = fcm.InMemoryFcmSender()
    app = create_app(app_cfg, push_on_write=False, fcm_sender=sender)
    with app.test_client() as c:
        c.post(
            "/devices/register",
            headers=HEADERS,
            json={"device_id": "d1", "fcm_token": "t1"},
        )
    r = scheduler.tick(app_cfg, sender=sender)
    assert r["fired"] == 2
    assert r["pushed"] == 2
    assert len(sender.sent) == 2
    titles = {m.title for m in sender.sent}
    assert all("5 分钟后到期" in t for t in titles)

    with connect(app_cfg.db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM push_log").fetchone()[0]
    assert n == 2


def test_scheduler_no_devices_no_push(app_cfg):
    indexer.reindex(app_cfg)
    sender = fcm.InMemoryFcmSender()
    r = scheduler.tick(app_cfg, sender=sender)
    assert r["fired"] == 2
    assert r["pushed"] == 2  # pushed 计数 = events 数量；但 sent 实际为 0
    assert sender.sent == []


def test_unregister_device(app_cfg):
    sender = fcm.InMemoryFcmSender()
    app = create_app(app_cfg, push_on_write=False, fcm_sender=sender)
    with app.test_client() as c:
        c.post("/devices/register", headers=HEADERS, json={"device_id": "d1", "fcm_token": "t1"})
        c.post("/devices/unregister", headers=HEADERS, json={"device_id": "d1"})

    with connect(app_cfg.db_path) as conn:
        rows = conn.execute("SELECT device_id FROM devices").fetchall()
    assert rows == []
