## Android MVP 设计细化

### 页面（最小 3 个）
- `TaskListScreen`：展示任务列表（含近截止标识）
- `TaskDetailScreen`：完成 / 延期 / snooze
- `CaptureScreen`：一行输入提交到 `/capture`

### 后台提醒（MVP-1）
- 采用 WorkManager 周期任务轮询 `/reminders/pending`。\n
  - 现实约束：系统允许的最小周期通常是 15 分钟。\n
  - MVP-1 验证闭环：先按 15 分钟跑通。\n
  - 如果你必须 1–5 分钟：\n
    - 方案 A：前台服务（耗电+常驻通知，体验差）\n
    - 方案 B：尽快升级 FCM（推荐）\n

### 通知
- channel：`reminders`\n
- 点击通知：带 `task_id` deep link 到 `TaskDetailScreen`。\n

### 本地缓存（Room）
- `TaskEntity`：缓存 `/tasks` 返回\n
- `ReminderEventEntity`：缓存提醒事件（避免重复提示）\n

### 网络协议
- 所有请求加 header：`X-API-Key`\n
- baseUrl 用户可配置（设置页或首次启动输入）\n

