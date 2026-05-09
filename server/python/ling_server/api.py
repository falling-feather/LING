"""HTTP API（Flask）。

接口（与 server/api/DESIGN.md 对齐）：
- GET  /healthz
- GET  /tasks
- GET  /tasks/<id>
- POST /tasks/<id>/complete
- POST /tasks/<id>/snooze
- POST /tasks/<id>/reschedule
- GET  /reminders/pending?limit=20
- POST /capture

鉴权：所有请求要求 header `X-API-Key: <token>`。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional

from dateutil import parser as dtparser
from flask import Flask, abort, g, jsonify, request

from . import fcm as fcm_mod
from . import gitwork, indexer, scheduler, yamlio
from .config import AppConfig
from .db import connect, init_db


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


def create_app(
    cfg: AppConfig,
    *,
    push_on_write: bool = True,
    fcm_sender: Optional["fcm_mod.FcmSender"] = None,
) -> Flask:
    app = Flask("ling-server")
    app.config["LING_CFG"] = cfg
    app.config["LING_PUSH"] = push_on_write
    if fcm_sender is None:
        fcm_sender = fcm_mod.build_sender(
            enabled=cfg.fcm.enabled,
            project_id=cfg.fcm.project_id,
            service_account=cfg.fcm.service_account,
        )
    app.config["LING_FCM"] = fcm_sender
    init_db(cfg.db_path)

    def require_key(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = request.headers.get("X-API-Key", "")
            if not cfg.server.api_key or key != cfg.server.api_key:
                abort(401, description="invalid X-API-Key")
            return fn(*args, **kwargs)
        return wrapper

    @app.errorhandler(401)
    def _h401(e):
        return jsonify({"error": "unauthorized", "message": str(e.description)}), 401

    @app.errorhandler(404)
    def _h404(e):
        return jsonify({"error": "not_found", "message": str(e.description)}), 404

    @app.errorhandler(400)
    def _h400(e):
        return jsonify({"error": "bad_request", "message": str(e.description)}), 400

    @app.errorhandler(Exception)
    def _h500(e):
        log.exception("unhandled error: %s", e)
        return jsonify({"error": "internal", "message": str(e)}), 500

    @app.get("/healthz")
    def healthz():
        return jsonify({"ok": True})

    @app.get("/tasks")
    @require_key
    def list_tasks():
        with connect(cfg.db_path) as conn:
            rows = conn.execute(
                "SELECT id,title,status,deadline,notes,updated_at FROM tasks ORDER BY "
                "CASE WHEN deadline IS NULL THEN 1 ELSE 0 END, deadline ASC"
            ).fetchall()
            return jsonify([dict(r) for r in rows])

    @app.get("/tasks/<task_id>")
    @require_key
    def get_task(task_id: str):
        with connect(cfg.db_path) as conn:
            row = conn.execute(
                "SELECT id,title,status,deadline,notes,updated_at FROM tasks WHERE id=?",
                (task_id,),
            ).fetchone()
        if row is None:
            abort(404, description=f"task {task_id} not found")
        return jsonify(dict(row))

    def _writeback_tasks_yaml(message: str):
        if not app.config["LING_PUSH"]:
            return None
        try:
            return gitwork.write_back(
                _git_cfg(cfg),
                [cfg.tasks_yaml_path],
                message,
                do_push=True,
            )
        except gitwork.GitError as e:
            log.warning("git write_back failed: %s", e)
            return None

    @app.post("/tasks/<task_id>/complete")
    @require_key
    def complete_task(task_id: str):
        item = yamlio.update_task(cfg.tasks_yaml_path, task_id, {"status": "done"})
        if item is None:
            abort(404, description=f"task {task_id} not found in tasks.yaml")
        indexer.reindex(cfg)
        sha = _writeback_tasks_yaml(f"[assistant] complete task {task_id}")
        return jsonify({"ok": True, "task": item, "git_sha": sha})

    @app.post("/tasks/<task_id>/snooze")
    @require_key
    def snooze_task(task_id: str):
        body = request.get_json(silent=True) or {}
        try:
            minutes = int(body.get("minutes", 0))
        except (TypeError, ValueError):
            abort(400, description="minutes must be int")
        if minutes <= 0:
            abort(400, description="minutes must be > 0")
        # 一期：snooze 仅在 events 表追加一个 fire_at = now+minutes 的事件，不改 yaml
        fire_at = (datetime.now(timezone.utc).astimezone()
                   + timedelta(minutes=minutes)).isoformat(timespec="seconds")
        event_id = f"{task_id}:snooze:{fire_at}"
        with connect(cfg.db_path) as conn:
            task = conn.execute(
                "SELECT id,title,deadline FROM tasks WHERE id=?", (task_id,)
            ).fetchone()
            if task is None:
                abort(404, description=f"task {task_id} not found")
            payload = json.dumps(
                {
                    "task_id": task_id,
                    "title": task["title"],
                    "deadline": task["deadline"],
                    "fire_at": fire_at,
                    "snooze": True,
                },
                ensure_ascii=False,
            )
            conn.execute(
                "INSERT OR IGNORE INTO events(id,type,payload,state,created_at) "
                "VALUES(?, 'reminder', ?, 'pending', ?)",
                (event_id, payload, datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")),
            )
        return jsonify({"ok": True, "fire_at": fire_at})

    @app.post("/tasks/<task_id>/reschedule")
    @require_key
    def reschedule_task(task_id: str):
        body = request.get_json(silent=True) or {}
        new_deadline = body.get("deadline")
        if not new_deadline:
            abort(400, description="deadline required (ISO-8601)")
        try:
            dt = dtparser.parse(str(new_deadline))
        except Exception:
            abort(400, description="invalid deadline")
        new_iso = dt.isoformat(timespec="seconds")
        item = yamlio.update_task(cfg.tasks_yaml_path, task_id, {"deadline": new_iso})
        if item is None:
            abort(404, description=f"task {task_id} not found in tasks.yaml")
        indexer.reindex(cfg)
        sha = _writeback_tasks_yaml(f"[assistant] reschedule task {task_id} -> {new_iso}")
        return jsonify({"ok": True, "task": item, "git_sha": sha})

    @app.get("/reminders/pending")
    @require_key
    def pending_reminders():
        try:
            limit = int(request.args.get("limit", "20"))
        except ValueError:
            limit = 20
        limit = max(1, min(limit, 200))
        # 先尝试做一次 tick，让"即将到来"的提醒立刻可见
        scheduler.tick(cfg, sender=app.config["LING_FCM"])
        out = []
        with connect(cfg.db_path) as conn:
            rows = conn.execute(
                "SELECT id,type,payload,state,created_at FROM events "
                "WHERE state='pending' AND type='reminder' "
                "ORDER BY created_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
            ids = [r["id"] for r in rows]
            for r in rows:
                d: Dict[str, Any] = {
                    "event_id": r["id"],
                    "type": r["type"],
                    "state": r["state"],
                    "created_at": r["created_at"],
                }
                try:
                    d.update(json.loads(r["payload"]))
                except Exception:
                    d["payload_raw"] = r["payload"]
                out.append(d)
            if ids:
                conn.executemany(
                    "UPDATE events SET state='delivered' WHERE id=?",
                    [(i,) for i in ids],
                )
        return jsonify(out)

    @app.post("/capture")
    @require_key
    def capture():
        body = request.get_json(silent=True) or {}
        text = (body.get("text") or "").strip()
        if not text:
            abort(400, description="text required")
        yamlio.append_capture(cfg.capture_md_path, text)
        sha = None
        if app.config["LING_PUSH"]:
            try:
                sha = gitwork.write_back(
                    _git_cfg(cfg),
                    [cfg.capture_md_path],
                    "[assistant] capture",
                    do_push=True,
                )
            except gitwork.GitError as e:
                log.warning("git write_back capture failed: %s", e)
        return jsonify({"ok": True, "git_sha": sha, "appended": text})

    @app.post("/devices/register")
    @require_key
    def register_device():
        body = request.get_json(silent=True) or {}
        device_id = (body.get("device_id") or "").strip()
        fcm_token = (body.get("fcm_token") or "").strip()
        platform = (body.get("platform") or "android").strip().lower()
        label = body.get("label")
        if not device_id or not fcm_token:
            abort(400, description="device_id and fcm_token are required")
        now_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        with connect(cfg.db_path) as conn:
            conn.execute(
                "INSERT INTO devices(device_id, fcm_token, platform, label, registered_at, updated_at) "
                "VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(device_id) DO UPDATE SET fcm_token=excluded.fcm_token, "
                "platform=excluded.platform, label=excluded.label, updated_at=excluded.updated_at",
                (device_id, fcm_token, platform, label, now_iso, now_iso),
            )
        return jsonify({"ok": True, "device_id": device_id, "updated_at": now_iso})

    @app.post("/devices/unregister")
    @require_key
    def unregister_device():
        body = request.get_json(silent=True) or {}
        device_id = (body.get("device_id") or "").strip()
        if not device_id:
            abort(400, description="device_id required")
        with connect(cfg.db_path) as conn:
            conn.execute("DELETE FROM devices WHERE device_id=?", (device_id,))
        return jsonify({"ok": True})

    @app.post("/devices/test_push")
    @require_key
    def test_push():
        """给所有已注册设备发一条测试推送，并返回每台设备的结果。"""
        body = request.get_json(silent=True) or {}
        title = (body.get("title") or "LING 测试推送").strip()
        text = (body.get("body") or "如果你看到这条通知，说明 FCM 链路通畅。").strip()
        sender: fcm_mod.FcmSender = app.config["LING_FCM"]

        results: list[dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        with connect(cfg.db_path) as conn:
            devices = conn.execute(
                "SELECT device_id, fcm_token FROM devices"
            ).fetchall()
            if not devices:
                return jsonify({"ok": True, "devices": 0, "results": []})
            msgs = [
                fcm_mod.FcmMessage(
                    token=d["fcm_token"],
                    title=title,
                    body=text,
                    data={"event_id": "test", "task_id": "test"},
                )
                for d in devices
            ]
            sent = sender.send_many(msgs)
            for d, r in zip(devices, sent):
                conn.execute(
                    "INSERT INTO push_log(event_id, device_id, ok, detail, created_at) VALUES(?,?,?,?,?)",
                    ("test", d["device_id"], 1 if r.ok else 0, r.detail, now_iso),
                )
                results.append({"device_id": d["device_id"], "ok": r.ok, "detail": r.detail})
        return jsonify({"ok": True, "devices": len(results), "results": results})

    return app
