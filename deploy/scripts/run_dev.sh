#!/usr/bin/env bash
# Linux/macOS 本地开发：装依赖 + 注入 GITHUB_TOKEN + 启动 server
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SERVER_DIR="$ROOT/server/python"

echo "=== 安装依赖 ==="
python3 -m pip install -q -r "$SERVER_DIR/requirements.txt"

if [ ! -f "$SERVER_DIR/config.yaml" ]; then
  cp "$SERVER_DIR/config.example.yaml" "$SERVER_DIR/config.yaml"
  echo "已复制 config.example.yaml -> config.yaml；请编辑后再启动"
  exit 0
fi

if [ -z "${GITHUB_TOKEN:-}" ] && command -v gh >/dev/null 2>&1; then
  if tok="$(gh auth token 2>/dev/null)"; then
    export GITHUB_TOKEN="$tok"
    echo "已从 gh CLI 注入 GITHUB_TOKEN（仅当前进程）"
  fi
fi

echo "=== 启动 ling-server ==="
cd "$SERVER_DIR"
exec python3 -m ling_server.cli -c config.yaml --verbose serve
