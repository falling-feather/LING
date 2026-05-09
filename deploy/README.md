## deploy — LING 服务端部署

提供 3 种方式：

1. **`systemd/`**：在 Linux 服务器上以系统服务方式运行（推荐生产用）
2. **`docker/`**：容器化部署（推荐你想"一键起停"且环境隔离时）
3. **`scripts/`**：本地开发/调试脚本

每种方式都共享同一份配置：`server/python/config.yaml`（从 `config.example.yaml` 复制）。

---

### 公共准备

服务依赖一个 `GITHUB_TOKEN`（具备目标记忆仓库的 `repo` 权限的 Personal Access Token），用于无交互 push/pull。

> 强烈建议把 token 放在系统级配置文件 / docker secret / `.env` 里，**不要**写进 `config.yaml` 后提交。

`config.yaml` 关键字段：

```yaml
server:
  host: "0.0.0.0"          # 容器/远程访问改成 0.0.0.0
  port: 8765
  api_key: "请改成长随机串"

memory_repo:
  workdir_path: "/data/workdir"
  repo_url: "https://github.com/<you>/LING-AGENT-memory.git"
  branch: "main"
  github_token_env: "GITHUB_TOKEN"
```

---

### 方式 1：systemd（Linux）

```bash
# 1. 把代码 clone 到服务器
sudo mkdir -p /opt/ling && sudo chown $USER /opt/ling
git clone https://github.com/falling-feather/LING.git /opt/ling

# 2. 一键安装（建虚拟环境、装依赖、写 systemd unit、启动）
cd /opt/ling
sudo bash deploy/scripts/install_linux.sh
```

`install_linux.sh` 会：
- 在 `/opt/ling/.venv` 创建虚拟环境并 `pip install -r server/python/requirements.txt`
- 把 `deploy/systemd/ling-server.service` 装到 `/etc/systemd/system/`
- 提示你编辑 `/etc/ling/ling.env`（GITHUB_TOKEN 写在这里）
- `systemctl daemon-reload && systemctl enable --now ling-server`

完成后：

```bash
systemctl status ling-server      # 查看状态
journalctl -u ling-server -f      # 跟踪日志
curl -H "X-API-Key: $key" http://localhost:8765/tasks
```

---

### 方式 2：Docker

```bash
cd deploy/docker
cp .env.example .env       # 写 GITHUB_TOKEN
docker compose up -d
docker compose logs -f
```

或直接 `docker run`：

```bash
docker build -t ling-server -f deploy/docker/Dockerfile .
docker run -d --name ling-server \
    -p 8765:8765 \
    -e GITHUB_TOKEN=ghp_xxx \
    -v ling_workdir:/data/workdir \
    -v $(pwd)/server/python/config.yaml:/etc/ling/config.yaml:ro \
    ling-server
```

容器内 `config.yaml` 的 `workdir_path` 应该写绝对路径 `/data/workdir`，并通过 volume 持久化。

---

### 方式 3：本地开发/调试

```powershell
# Windows PowerShell
cd deploy\scripts
.\run_dev.ps1
```

```bash
# Linux/macOS
bash deploy/scripts/run_dev.sh
```

会自动 `pip install`、设置 `GITHUB_TOKEN=$(gh auth token)`（如果你装了 gh）、用 `server/python/config.yaml` 启动。

---

### 升级流程

**systemd**：

```bash
cd /opt/ling && git pull
sudo systemctl restart ling-server
```

**docker**：

```bash
cd /opt/ling && git pull
cd deploy/docker
docker compose build && docker compose up -d
```

如果数据库 schema 有变更：删除 `workdir/index/db.sqlite`（可重建）后重启即可。
