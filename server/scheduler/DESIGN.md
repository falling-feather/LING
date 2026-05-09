## ReminderScheduler 设计（MVP-1）

### 目标
- **分钟级**扫描数据库中的 `reminders`，把即将触发的提醒变成“待提醒事件（pending）”
- 支持超期重复提醒（每 4 小时一次，直到完成/延期/关闭）
- 提供给 API 一个简单的拉取接口：App 轮询 `GET /reminders/pending`

### 输入
- `db_path`：SQLite 数据库
- `poll_interval_seconds`：默认 60
- `lookahead_seconds`：建议 120（扫描未来两分钟内应触发的提醒，避免抖动）
- `overdue_repeat_minutes`：默认 240

### 输出（事件队列）
在 SQLite 里用 `events` 表承载“待提醒事件”，Scheduler 负责写入；API 负责读取并标记已投递。

#### `events`
- `id TEXT PRIMARY KEY`（uuid 或 `${task_id}:${fire_at}:${seq}`）
- `type TEXT NOT NULL`（一期只用 `reminder`）
- `payload TEXT NOT NULL`（JSON：task_id/title/deadline/fire_at）
- `state TEXT NOT NULL`（`pending|delivered|done|error`）
- `created_at TEXT NOT NULL`

### 触发逻辑（一期）
1. 扫描 `reminders` 中 `state='pending'` 且 `fire_at <= now + lookahead` 的记录\n
2. 对每条记录写入一条 `events`（state=pending）\n
3. 将该 `reminders.state` 置为 `fired`\n

### 超期重复（一期）
- 当任务 `deadline < now` 且 `status` 不是 done：\n
  - 每隔 `overdue_repeat_minutes` 生成一个 `events`（payload 标记 overdue=true）\n
  - 重复调度用 `workdir_state` 或 `events` 最近一次 overdue 的时间做去重\n

### 幂等性与去重
- `events.id` 设计为稳定可预测：\n
  - fixed reminders：`${task_id}:${fire_at}`\n
  - overdue repeats：`${task_id}:overdue:${floor(now/overdue_repeat_minutes)}`\n
这样 Scheduler 重跑不会刷爆重复事件。

