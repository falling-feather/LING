"""CLI 入口：python -m ling_server.cli <subcommand>

子命令：
- sync     执行一次 git sync + index + tick
- index    单独跑一次 indexer
- tick     单独跑一次 scheduler tick
- serve    启动 Flask API（同时启动后台 syncd）
- testrun  本地端到端 smoke test（不连远端 git，不 push）
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from . import indexer, scheduler, syncd
from .api import create_app
from .config import load_config


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ling-server")
    parser.add_argument("-c", "--config", default=str(Path(__file__).resolve().parents[1] / "config.yaml"),
                        help="server config yaml (default: server/python/config.yaml)")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync", help="run git sync + index + tick once")
    sub.add_parser("index", help="run indexer once")
    sub.add_parser("tick", help="run scheduler tick once")
    serve = sub.add_parser("serve", help="start API server")
    serve.add_argument("--no-push", action="store_true", help="disable git push on writes")
    serve.add_argument("--no-syncd", action="store_true", help="do not start background sync")
    sub.add_parser("testrun", help="local smoke test")

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    cfg = load_config(args.config)

    if args.cmd == "sync":
        r = syncd.sync_once(cfg)
        print(r)
        return 0
    if args.cmd == "index":
        r = indexer.reindex(cfg)
        print(r)
        return 0
    if args.cmd == "tick":
        r = scheduler.tick(cfg)
        print(r)
        return 0
    if args.cmd == "serve":
        push = not args.no_push
        # 1) 先尝试本地 index（不强行联网）
        if cfg.tasks_yaml_path.exists():
            indexer.reindex(cfg)
        # 2) 起后台 syncd
        if not args.no_syncd:
            try:
                syncd.start_background(cfg)
            except Exception as e:
                logging.getLogger(__name__).warning("syncd failed to start: %s", e)
        app = create_app(cfg, push_on_write=push)
        app.run(host=cfg.server.host, port=cfg.server.port, debug=False, use_reloader=False)
        return 0
    if args.cmd == "testrun":
        from .testrun import run_smoke_test
        return run_smoke_test(cfg)
    return 2


if __name__ == "__main__":
    sys.exit(main())
