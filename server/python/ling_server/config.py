"""配置加载与默认值。

- server/config.yaml 是部署侧配置（端口/api_key/repo_url/...）
- memory_repo/ops/config.yaml 是用户侧配置（提醒偏移、轮询周期、时区）

二者合并后给所有子模块使用。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


DEFAULT_OPS_CONFIG: Dict[str, Any] = {
    "timezone": "Asia/Shanghai",
    "sync_interval_hours": 4,
    "poll_interval_seconds": 60,
    "default_remind_offsets_minutes": [1440, 240, 60, 15],
    "overdue_repeat_minutes": 240,
}


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    api_key: str = "change-me-please"


@dataclass
class MemoryRepoConfig:
    workdir_path: Path = Path("./workdir")
    repo_url: str = ""
    branch: str = "main"
    git_author_name: str = "ling-assistant"
    git_author_email: str = "ling-assistant@example.com"
    github_token_env: str = "GITHUB_TOKEN"


@dataclass
class SchedulerConfig:
    sync_interval_hours: int = 4
    poll_interval_seconds: int = 60
    lookahead_seconds: int = 120
    overdue_repeat_minutes: int = 240


@dataclass
class IndexConfig:
    db_path: Path = Path("./workdir/index/db.sqlite")


@dataclass
class FcmConfig:
    enabled: bool = False
    project_id: str = ""
    service_account: str = ""  # service account JSON 文件路径


@dataclass
class OpsConfig:
    timezone: str = "Asia/Shanghai"
    default_remind_offsets_minutes: List[int] = field(
        default_factory=lambda: list(DEFAULT_OPS_CONFIG["default_remind_offsets_minutes"])
    )
    overdue_repeat_minutes: int = 240
    poll_interval_seconds: int = 60
    sync_interval_hours: int = 4


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    memory_repo: MemoryRepoConfig = field(default_factory=MemoryRepoConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    index: IndexConfig = field(default_factory=IndexConfig)
    ops: OpsConfig = field(default_factory=OpsConfig)
    fcm: FcmConfig = field(default_factory=FcmConfig)
    config_path: Optional[Path] = None

    @property
    def workdir(self) -> Path:
        return self.memory_repo.workdir_path

    @property
    def tasks_yaml_path(self) -> Path:
        return self.workdir / "tasks.yaml"

    @property
    def capture_md_path(self) -> Path:
        return self.workdir / "inbox" / "capture.md"

    @property
    def ops_config_path(self) -> Path:
        return self.workdir / "ops" / "config.yaml"

    @property
    def db_path(self) -> Path:
        return self.index.db_path


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(server_config_path: str | os.PathLike[str]) -> AppConfig:
    """加载 server 端配置；ops/config.yaml 在 indexer 里运行时再加载（因为它是仓库内容）。"""
    server_path = Path(server_config_path).resolve()
    raw = _load_yaml(server_path)

    cfg = AppConfig()
    cfg.config_path = server_path

    s = raw.get("server", {})
    cfg.server.host = s.get("host", cfg.server.host)
    cfg.server.port = int(s.get("port", cfg.server.port))
    cfg.server.api_key = s.get("api_key", cfg.server.api_key)

    m = raw.get("memory_repo", {})
    base = server_path.parent
    workdir_raw = m.get("workdir_path", str(cfg.memory_repo.workdir_path))
    cfg.memory_repo.workdir_path = (base / workdir_raw).resolve()
    cfg.memory_repo.repo_url = m.get("repo_url", cfg.memory_repo.repo_url)
    cfg.memory_repo.branch = m.get("branch", cfg.memory_repo.branch)
    cfg.memory_repo.git_author_name = m.get("git_author_name", cfg.memory_repo.git_author_name)
    cfg.memory_repo.git_author_email = m.get("git_author_email", cfg.memory_repo.git_author_email)
    cfg.memory_repo.github_token_env = m.get("github_token_env", cfg.memory_repo.github_token_env)

    sc = raw.get("scheduler", {})
    cfg.scheduler.sync_interval_hours = int(sc.get("sync_interval_hours", cfg.scheduler.sync_interval_hours))
    cfg.scheduler.poll_interval_seconds = int(sc.get("poll_interval_seconds", cfg.scheduler.poll_interval_seconds))
    cfg.scheduler.lookahead_seconds = int(sc.get("lookahead_seconds", cfg.scheduler.lookahead_seconds))
    cfg.scheduler.overdue_repeat_minutes = int(sc.get("overdue_repeat_minutes", cfg.scheduler.overdue_repeat_minutes))

    ix = raw.get("index", {})
    db_raw = ix.get("db_path", str(cfg.index.db_path))
    cfg.index.db_path = (base / db_raw).resolve()

    fc = raw.get("fcm", {})
    cfg.fcm.enabled = bool(fc.get("enabled", cfg.fcm.enabled))
    cfg.fcm.project_id = fc.get("project_id", cfg.fcm.project_id)
    sa_raw = fc.get("service_account", cfg.fcm.service_account)
    if sa_raw:
        cfg.fcm.service_account = str((base / sa_raw).resolve())

    return cfg


def load_ops_config(workdir: Path) -> OpsConfig:
    """加载仓库内 ops/config.yaml，缺省值兜底。"""
    raw = _load_yaml(workdir / "ops" / "config.yaml")
    merged: Dict[str, Any] = dict(DEFAULT_OPS_CONFIG)
    merged.update(raw or {})
    return OpsConfig(
        timezone=merged.get("timezone", "Asia/Shanghai"),
        default_remind_offsets_minutes=list(merged.get("default_remind_offsets_minutes", [])),
        overdue_repeat_minutes=int(merged.get("overdue_repeat_minutes", 240)),
        poll_interval_seconds=int(merged.get("poll_interval_seconds", 60)),
        sync_interval_hours=int(merged.get("sync_interval_hours", 4)),
    )
