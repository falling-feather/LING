## 开发者文档（developer docs）

这份文档面向开发者，目标是把“文件架构、实现逻辑、接口关系、短期规划”讲清楚。

### 模块拆分

- `server/syncd`：Git 同步守护进程（4小时心跳）
- `server/indexer`：解析器（tasks/daily/inbox -> 数据库）
- `server/scheduler`：提醒调度器（分钟级扫描触发提醒事件）
- `server/api`：HTTP API（Android 轮询、任务操作、捕获输入）
- `android/`：Android 客户端（轮询 + 本地通知 + 最小页面）

### 数据真相与索引

- **真相**：记忆仓库里的 Markdown/YAML 文件（见 `memory_repo_template/`）
- **索引**：服务器 `index/db.sqlite`（可删重建；一期用 SQLite）

### 一期 API（最小）

- `GET /tasks`
- `GET /tasks/{id}`
- `POST /tasks/{id}/complete`
- `POST /tasks/{id}/snooze`（minutes）
- `POST /tasks/{id}/reschedule`（deadline）
- `GET /reminders/pending`（App 轮询）
- `POST /capture`（追加到 `inbox/capture.md`）

### 全局记忆（长期）

一期先实现：结构化任务 + 可靠提醒。\n
二期再加：SQLite FTS5 / 向量检索、记忆治理、推送升级、iOS/桌面端。

