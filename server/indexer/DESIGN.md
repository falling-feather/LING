## Indexer 设计（MVP-1）

### 目标
- 解析 MemoryWorkdir 中的 `tasks.yaml`（一期）并入库到 `index/db.sqlite`
- 生成提醒计划（Reminders），供 Scheduler 扫描触发
- 支持增量更新：只在 Git SHA 变化时解析；或只解析变更文件

### 输入
- `workdir_path`：MemoryWorkdir（Git clone）
- `db_path`：`<workdir>/index/db.sqlite` 或外置路径（推荐与 workdir 同机）
- `tasks_path`：默认 `<workdir>/tasks.yaml`
-（二期）`inbox/capture.md`、`daily/YYYY/*.md`

### 输出（SQLite 表）

#### `tasks`
- `id TEXT PRIMARY KEY`
- `title TEXT NOT NULL`
- `status TEXT NOT NULL`
- `deadline TEXT`（ISO-8601 字符串，含时区）
- `notes TEXT`
- `source TEXT`
- `updated_at TEXT NOT NULL`
- `raw_hash TEXT NOT NULL`（任务原始 YAML 片段 hash，用于快速判断变化）

#### `reminders`
- `id TEXT PRIMARY KEY`（可用 `${task_id}:${fire_at}`）
- `task_id TEXT NOT NULL`
- `fire_at TEXT NOT NULL`（ISO-8601）
- `state TEXT NOT NULL`（`pending|fired|cancelled|error`）
- `last_error TEXT`

#### `workdir_state`
- `key TEXT PRIMARY KEY`
- `value TEXT NOT NULL`
\n
其中 `workdir_state['last_git_sha']` 用于判断是否需要重新解析。

### 解析规则（一期）
- 只解析根目录 `tasks.yaml`，每个 item 是一条任务。\n
- `deadline` 为空则不生成 reminders。\n
- 生成提醒：根据 `ops/config.yaml` 的 `default_remind_offsets_minutes`，对每个任务生成 `fire_at = deadline - offset`。\n
- 超期重复：由 Scheduler 负责（Indexer 只生成“固定偏移提醒”）。

### 增量策略（一期最简单可用）
1. SyncDaemon 每次同步成功把 `last_git_sha` 写到 `ops/state.json` 或 `workdir_state`。\n
2. Indexer 每次运行读取当前 HEAD SHA（`git rev-parse HEAD`），若与库中不同则全量重建 reminders（任务数通常不大，够用）。\n
3. 如果后续任务数变多，再做“只处理变更任务”。

