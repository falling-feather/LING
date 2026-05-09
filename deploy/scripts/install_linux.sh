#!/usr/bin/env bash
# 在 Linux 服务器上一键安装 LING 服务（systemd 守护）。
# 假设代码已经 clone 到 /opt/ling。
set -euo pipefail

PREFIX="${PREFIX:-/opt/ling}"
SERVICE_USER="${SERVICE_USER:-ling}"
ETC_DIR="/etc/ling"
SERVICE_NAME="ling-server"

if [ "$(id -u)" -ne 0 ]; then
  echo "请使用 sudo 运行：sudo bash $0" >&2
  exit 1
fi

if [ ! -d "$PREFIX" ]; then
  echo "目录 $PREFIX 不存在；请先把代码 clone 到那里：" >&2
  echo "  sudo git clone https://github.com/<you>/LING.git $PREFIX" >&2
  exit 2
fi

echo "=== 1. 创建服务用户 $SERVICE_USER ==="
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home "$PREFIX" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

echo "=== 2. 准备目录 ==="
mkdir -p "$ETC_DIR"
mkdir -p "$PREFIX/server/python/workdir"
chown -R "$SERVICE_USER:$SERVICE_USER" "$PREFIX/server/python/workdir"

echo "=== 3. 创建虚拟环境与依赖 ==="
if [ ! -d "$PREFIX/.venv" ]; then
  python3 -m venv "$PREFIX/.venv"
fi
"$PREFIX/.venv/bin/pip" install --upgrade pip
"$PREFIX/.venv/bin/pip" install -r "$PREFIX/server/python/requirements.txt"

echo "=== 4. 配置文件 ==="
if [ ! -f "$PREFIX/server/python/config.yaml" ]; then
  cp "$PREFIX/server/python/config.example.yaml" "$PREFIX/server/python/config.yaml"
  echo "已生成 $PREFIX/server/python/config.yaml；请编辑：repo_url / api_key / workdir_path"
fi
if [ ! -f "$ETC_DIR/ling.env" ]; then
  install -m 600 "$PREFIX/deploy/systemd/ling.env.example" "$ETC_DIR/ling.env"
  chown "$SERVICE_USER:$SERVICE_USER" "$ETC_DIR/ling.env"
  echo "已生成 $ETC_DIR/ling.env；请编辑里面的 GITHUB_TOKEN"
fi

echo "=== 5. 安装 systemd unit ==="
install -m 644 "$PREFIX/deploy/systemd/ling-server.service" "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload

cat <<EOF

=== 安装完成 ===

下一步：
  1. 编辑配置：
       sudo $EDITOR $PREFIX/server/python/config.yaml
       sudo $EDITOR $ETC_DIR/ling.env
  2. 启动服务：
       sudo systemctl enable --now $SERVICE_NAME
  3. 查看状态：
       sudo systemctl status $SERVICE_NAME
       sudo journalctl -u $SERVICE_NAME -f

EOF
