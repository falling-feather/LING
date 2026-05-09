"""Firebase Cloud Messaging（HTTP v1 API）轻量客户端。

设计要点：
- 凭据缺失时优雅退化（push_to_devices 静默 no-op，App 仍可走轮询拿提醒）
- 不引入 firebase-admin 重 SDK，只用 google-auth + requests
- 内置一个 InMemory 实现用于测试

环境变量 / 配置：
- fcm.enabled            是否启用（默认 false）
- fcm.project_id         Firebase 项目 id
- fcm.service_account    指向 service account JSON 文件路径

服务账号 JSON 由用户从 Firebase Console -> Project settings -> Service accounts 生成；
不要入库。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


log = logging.getLogger(__name__)

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_ENDPOINT_TPL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"


@dataclass
class FcmMessage:
    """送给一个 device 的一条消息。"""

    token: str
    title: str
    body: str
    data: Dict[str, str] = field(default_factory=dict)


@dataclass
class FcmResult:
    token: str
    ok: bool
    detail: str = ""


class FcmSender(ABC):
    """FCM 发送器抽象。生产用 HttpV1FcmSender；测试用 InMemoryFcmSender。"""

    @abstractmethod
    def send(self, msg: FcmMessage) -> FcmResult:  # pragma: no cover
        ...

    def send_many(self, msgs: List[FcmMessage]) -> List[FcmResult]:
        return [self.send(m) for m in msgs]


class NullFcmSender(FcmSender):
    """凭据缺失或被禁用时使用：不发送，但记日志。"""

    def __init__(self, reason: str = "fcm disabled"):
        self.reason = reason

    def send(self, msg: FcmMessage) -> FcmResult:
        log.debug("NullFcm: skip token=%s title=%r reason=%s", msg.token[:8], msg.title, self.reason)
        return FcmResult(token=msg.token, ok=False, detail=f"skipped: {self.reason}")


class InMemoryFcmSender(FcmSender):
    """测试专用：把每次 send 收到的消息追加到 sent 列表。"""

    def __init__(self):
        self.sent: List[FcmMessage] = []
        self._lock = threading.Lock()

    def send(self, msg: FcmMessage) -> FcmResult:
        with self._lock:
            self.sent.append(msg)
        return FcmResult(token=msg.token, ok=True, detail="ok")

    def reset(self) -> None:
        with self._lock:
            self.sent.clear()


class HttpV1FcmSender(FcmSender):
    """通过 HTTP v1 API 发送。凭据用 google-auth 自动刷新。"""

    def __init__(self, project_id: str, service_account_path: str):
        self.project_id = project_id
        self.service_account_path = service_account_path
        self._endpoint = FCM_ENDPOINT_TPL.format(project_id=project_id)
        self._creds = None
        self._lock = threading.Lock()

    def _get_token(self) -> str:
        # 延迟导入：让单元测试不强制依赖 google-auth
        from google.oauth2 import service_account  # type: ignore
        import google.auth.transport.requests  # type: ignore

        with self._lock:
            if self._creds is None:
                self._creds = service_account.Credentials.from_service_account_file(
                    self.service_account_path,
                    scopes=[FCM_SCOPE],
                )
            if not self._creds.valid:
                self._creds.refresh(google.auth.transport.requests.Request())
            return self._creds.token

    def send(self, msg: FcmMessage) -> FcmResult:
        try:
            import requests  # type: ignore

            token = self._get_token()
            payload = {
                "message": {
                    "token": msg.token,
                    "notification": {"title": msg.title, "body": msg.body},
                    "data": {k: str(v) for k, v in msg.data.items()},
                    "android": {"priority": "HIGH"},
                }
            }
            resp = requests.post(
                self._endpoint,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=10,
            )
            if resp.status_code == 200:
                return FcmResult(token=msg.token, ok=True, detail="ok")
            return FcmResult(
                token=msg.token,
                ok=False,
                detail=f"http {resp.status_code}: {resp.text[:200]}",
            )
        except Exception as e:  # pragma: no cover - network/credential path
            log.warning("fcm send failed: %s", e)
            return FcmResult(token=msg.token, ok=False, detail=str(e))


def build_sender(
    *,
    enabled: bool,
    project_id: Optional[str],
    service_account: Optional[str],
) -> FcmSender:
    """根据配置构建 sender。任何缺失项都会退化为 NullFcmSender。"""
    if not enabled:
        return NullFcmSender("disabled in config")
    if not project_id:
        return NullFcmSender("missing fcm.project_id")
    if not service_account:
        return NullFcmSender("missing fcm.service_account")
    if not Path(service_account).exists():
        return NullFcmSender(f"service account file not found: {service_account}")
    return HttpV1FcmSender(project_id=project_id, service_account_path=service_account)
