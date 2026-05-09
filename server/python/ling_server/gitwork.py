"""轻量 Git 工作流封装（subprocess）。

只覆盖 MVP-1 需要的能力：
- ensure_repo: 不存在则 clone；存在则 fetch
- pull_rebase: 同步远端
- write_back: 写回单个或多个文件 + commit + push（含重试 + 冲突时自动 pull --rebase）
- get_head_sha: 取 HEAD SHA

无 libgit2 依赖；要求宿主机有 `git` 可执行文件。

针对 Windows + GitHub 偶发 SSL/TLS schannel handshake 失败，所有"网络型"
git 命令都会做有限重试。也可以通过环境变量 `LING_GIT_SSL_BACKEND=openssl`
强制使用 OpenSSL 后端。
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence
from urllib.parse import urlparse, urlunparse


log = logging.getLogger(__name__)


# 命中其中任何片段，则视为可重试的瞬时网络/SSL 错误
_RETRYABLE_ERROR_HINTS = (
    "schannel",
    "ssl",
    "tls",
    "Could not resolve host",
    "Failed to connect",
    "Connection was reset",
    "Connection timed out",
    "fatal: unable to access",
    "EOF",
    "RPC failed",
    "early EOF",
)


class GitError(RuntimeError):
    pass


def _is_retryable(stderr: str) -> bool:
    s = (stderr or "").lower()
    return any(hint.lower() in s for hint in _RETRYABLE_ERROR_HINTS)


def _http_extra_config() -> List[str]:
    extra: List[str] = []
    backend = os.environ.get("LING_GIT_SSL_BACKEND", "").strip().lower()
    if backend in {"openssl", "schannel"}:
        extra += ["-c", f"http.sslBackend={backend}"]
    # HTTP/1.1 在某些公司网络/弱网络下比 HTTP/2 更稳
    if os.environ.get("LING_GIT_HTTP_VERSION", "").upper() == "HTTP/1.1":
        extra += ["-c", "http.version=HTTP/1.1"]
    return extra


@dataclass
class GitConfig:
    workdir: Path
    repo_url: str
    branch: str = "main"
    author_name: str = "ling-assistant"
    author_email: str = "ling-assistant@example.com"
    token_env: str = "GITHUB_TOKEN"


def _run(cmd: Sequence[str], cwd: Optional[Path] = None, env: Optional[dict] = None,
         check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    log.debug("git$ %s (cwd=%s)", " ".join(cmd), cwd)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        raise GitError(
            f"command failed: {' '.join(cmd)}\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return proc


def _run_net(args: Sequence[str], cwd: Optional[Path] = None, env: Optional[dict] = None,
             max_retries: int = 4, base_delay: float = 1.5) -> subprocess.CompletedProcess:
    """跑一条会联网的 git 命令；遇到瞬时 SSL/网络错误指数退避重试。"""
    cmd = ["git", *_http_extra_config(), *args]
    last: Optional[subprocess.CompletedProcess] = None
    for attempt in range(max_retries):
        proc = _run(cmd, cwd=cwd, env=env, check=False)
        if proc.returncode == 0:
            return proc
        if not _is_retryable(proc.stderr):
            raise GitError(
                f"command failed: {' '.join(cmd)}\nstdout={proc.stdout}\nstderr={proc.stderr}"
            )
        last = proc
        delay = base_delay * (2 ** attempt)
        log.warning(
            "transient network error (attempt %d/%d, sleep %.1fs): %s",
            attempt + 1, max_retries, delay, (proc.stderr or "").strip().splitlines()[-1:],
        )
        time.sleep(delay)
    assert last is not None
    raise GitError(
        f"command failed after {max_retries} retries: {' '.join(cmd)}\nstderr={last.stderr}"
    )


def _embed_token(repo_url: str, token: Optional[str]) -> str:
    """对 https url 注入 token，用于无交互 push/pull。其它（ssh/file）原样返回。"""
    if not token:
        return repo_url
    parsed = urlparse(repo_url)
    if parsed.scheme not in {"http", "https"}:
        return repo_url
    netloc = parsed.netloc
    if "@" in netloc:
        netloc = netloc.split("@", 1)[1]
    new_netloc = f"x-access-token:{token}@{netloc}"
    return urlunparse(parsed._replace(netloc=new_netloc))


def _git_env(cfg: GitConfig) -> dict:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = cfg.author_name
    env["GIT_AUTHOR_EMAIL"] = cfg.author_email
    env["GIT_COMMITTER_NAME"] = cfg.author_name
    env["GIT_COMMITTER_EMAIL"] = cfg.author_email
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def ensure_repo(cfg: GitConfig) -> None:
    """确保 workdir 是有效仓库；不存在则 clone。"""
    cfg.workdir.parent.mkdir(parents=True, exist_ok=True)
    git_dir = cfg.workdir / ".git"
    env = _git_env(cfg)
    if git_dir.exists():
        return
    if not cfg.repo_url:
        raise GitError("memory_repo.repo_url is empty; cannot clone")
    token = os.environ.get(cfg.token_env)
    url = _embed_token(cfg.repo_url, token)
    log.info("cloning %s -> %s", cfg.repo_url, cfg.workdir)
    if cfg.workdir.exists() and any(cfg.workdir.iterdir()):
        # 目标目录非空：原地 init + remote add + fetch + checkout
        _run(["git", "init", "-b", cfg.branch], cwd=cfg.workdir, env=env)
        _run(["git", "remote", "add", "origin", url], cwd=cfg.workdir, env=env)
        try:
            _run_net(["fetch", "origin", cfg.branch], cwd=cfg.workdir, env=env)
            _run(["git", "checkout", "-B", cfg.branch, f"origin/{cfg.branch}"], cwd=cfg.workdir, env=env)
        except GitError:
            log.info("remote branch not found, will push first commit later")
    else:
        cfg.workdir.mkdir(parents=True, exist_ok=True)
        try:
            _run_net(["clone", "--branch", cfg.branch, url, str(cfg.workdir)], env=env)
        except GitError:
            log.info("clone failed (likely empty remote); init locally")
            _run(["git", "init", "-b", cfg.branch], cwd=cfg.workdir, env=env)
            _run(["git", "remote", "add", "origin", url], cwd=cfg.workdir, env=env)


def get_head_sha(cfg: GitConfig) -> Optional[str]:
    try:
        proc = _run(["git", "rev-parse", "HEAD"], cwd=cfg.workdir, env=_git_env(cfg))
        return (proc.stdout or "").strip() or None
    except GitError:
        return None


def fetch(cfg: GitConfig) -> None:
    token = os.environ.get(cfg.token_env)
    url = _embed_token(cfg.repo_url, token)
    env = _git_env(cfg)
    try:
        _run_net(["fetch", url, cfg.branch], cwd=cfg.workdir, env=env)
    except GitError as e:
        log.warning("fetch failed: %s", e)


def pull_rebase(cfg: GitConfig) -> None:
    token = os.environ.get(cfg.token_env)
    url = _embed_token(cfg.repo_url, token)
    env = _git_env(cfg)
    _run_net(["pull", "--rebase", url, cfg.branch], cwd=cfg.workdir, env=env)


def write_back(cfg: GitConfig, files: Iterable[Path], message: str,
               do_push: bool = True) -> Optional[str]:
    """写回流程：add -> commit -> (pull --rebase -> push)。返回新 HEAD SHA 或 None。"""
    env = _git_env(cfg)
    rels = []
    for f in files:
        rels.append(str(Path(f).resolve().relative_to(cfg.workdir.resolve())))
    if not rels:
        return None
    _run(["git", "add", *rels], cwd=cfg.workdir, env=env)
    # 是否真的有变化
    diff = _run(["git", "diff", "--cached", "--name-only"], cwd=cfg.workdir, env=env)
    if not (diff.stdout or "").strip():
        log.info("nothing to commit for %s", rels)
        return None
    _run(["git", "commit", "-m", message], cwd=cfg.workdir, env=env)
    new_sha = get_head_sha(cfg)
    if not do_push:
        return new_sha
    token = os.environ.get(cfg.token_env)
    url = _embed_token(cfg.repo_url, token)
    try:
        _run_net(["push", url, f"HEAD:{cfg.branch}"], cwd=cfg.workdir, env=env)
    except GitError as first_err:
        log.warning("push failed even after retries; trying pull --rebase + push once: %s",
                    first_err)
        pull_rebase(cfg)
        _run_net(["push", url, f"HEAD:{cfg.branch}"], cwd=cfg.workdir, env=env)
    return get_head_sha(cfg)
