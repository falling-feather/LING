## server/python — LING 云端服务（Python MVP-1 实现）

各模块的设计契约见 `server/{syncd,indexer,scheduler,api}/DESIGN.md`，本目录是它们的 Python 实现。

### 目录结构

- `ling_server/config.py`     配置加载（server/config.yaml + memory_repo/ops/config.yaml）
- `ling_server/db.py`         SQLite schema 与连接帮助
- `ling_server/gitwork.py`    Git clone/pull/commit/push 封装（subprocess）
- `ling_server/indexer.py`    解析 `tasks.yaml` -> `tasks` 与 `reminders` 表
- `ling_server/scheduler.py`  扫描 `reminders`，写入 `events`（pending）
- `ling_server/api.py`        Flask HTTP API（与 `server/api/DESIGN.md` 一致）
- `ling_server/syncd.py`      APScheduler 心跳：`sync` + `tick`
- `ling_server/yamlio.py`     `tasks.yaml` / `inbox/capture.md` 的写回工具
- `ling_server/cli.py`        命令行入口
- `ling_server/testrun.py`    端到端冒烟测试（无需联网）
- `config.example.yaml`       配置样例
- `requirements.txt`          运行依赖

### 安装与配置

```bash
python -m pip install -r requirements.txt
copy config.example.yaml config.yaml      # Windows
# 或：cp config.example.yaml config.yaml  # Linux/macOS
```

按需修改 `config.yaml`：
- `server.api_key`：Android/CLI 调用所需 X-API-Key
- `memory_repo.repo_url`：你的私有“记忆仓库” URL（如 `https://github.com/<user>/LING-AGENT-memory.git`）
- `memory_repo.workdir_path`：服务器本地的 MemoryWorkdir 路径

如果 `repo_url` 是 https，需要 push/pull，请 export `GITHUB_TOKEN`：

```bash
$env:GITHUB_TOKEN="ghp_xxx"   # PowerShell
# 或 export GITHUB_TOKEN=ghp_xxx
```

### 命令

```bash
python -m ling_server.cli -c config.yaml index     # 解析一次 tasks.yaml -> SQLite
python -m ling_server.cli -c config.yaml tick      # 跑一次 scheduler，把命中的提醒写入 events
python -m ling_server.cli -c config.yaml sync      # git pull + index + tick（联网）
python -m ling_server.cli -c config.yaml serve     # 起 HTTP API（默认 127.0.0.1:8765）
python -m ling_server.cli -c config.yaml testrun   # 本地冒烟测试，不联网，不 push
```

### 接口

所有接口要求 header `X-API-Key: <token>`：
- `GET /healthz`
- `GET /tasks` / `GET /tasks/<id>`
- `POST /tasks/<id>/complete`（写回 tasks.yaml -> commit/push）
- `POST /tasks/<id>/snooze` body：`{"minutes": 15}`
- `POST /tasks/<id>/reschedule` body：`{"deadline": "2026-05-12T10:00:00+08:00"}`
- `GET /reminders/pending?limit=20`（投递后立即标记 delivered）
- `POST /capture` body：`{"text": "..."}`（追加 inbox/capture.md -> commit/push）

### C++ 迁移路径（一期不实现）

`server/{syncd,indexer,scheduler,api}/DESIGN.md` 都是语言无关的契约。
当 Python 在性能/部署上不够时，可按目录逐个替换为 C++ 实现，只要保留：
- `index/db.sqlite` schema 不变（`tasks/reminders/events/workdir_state`）
- HTTP 接口签名不变
就可以与 Android 客户端无缝兼容。
