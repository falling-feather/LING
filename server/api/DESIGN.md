## ApiService 设计（MVP-1）

### 目标
- 提供 Android 需要的最小 HTTP API（任务、提醒、捕获、状态变更）
- 使用简单 `API_KEY` 鉴权（Header：`X-API-Key`）
- 对“状态变更/捕获”执行**写回 Git**：修改 workdir 文件 -> commit -> push

### 认证
- 客户端每次请求带：`X-API-Key: <token>`\n
- 服务端配置：`server_api_key`（环境变量或 `server/config.yaml`）

### 接口（一期）

#### 任务
- `GET /tasks`\n
  - 返回：`[{id,title,status,deadline,notes}]`\n
- `GET /tasks/{id}`\n
  - 返回：单条任务\n

#### 任务变更（写回 `tasks.yaml`）
- `POST /tasks/{id}/complete`\n
  - body：可空\n
  - 行为：status -> done\n
- `POST /tasks/{id}/snooze`\n
  - body：`{minutes:int}`\n
  - 行为：生成“临时提醒”事件（仅改数据库，不一定写回 YAML；或写回 `remind_policy`）\n
- `POST /tasks/{id}/reschedule`\n
  - body：`{deadline:string}`\n
  - 行为：修改 YAML 中 deadline\n

#### 提醒（App 轮询）
- `GET /reminders/pending?limit=20`\n
  - 返回：`[{event_id,task_id,title,deadline,fire_at,overdue}]`\n
  - 并把这些 event 标记为 delivered（避免重复投递）\n

#### 捕获
- `POST /capture`\n
  - body：`{text:string}`\n
  - 行为：追加到 `inbox/capture.md`，commit/push\n

### 写回 Git 工作流（一期）
1. `git pull --rebase`\n
2. 修改文件（`tasks.yaml` 或 `inbox/capture.md`）\n
3. `git add`、`git commit -m "[assistant] ..."`、`git push`\n
4. 失败：落 `ops/conflicts/*.patch`，并向 `events` 写入 `type=error` 供 App 显示\n

