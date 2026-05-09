## 未来规划（roadmap）

### MVP-1（提醒闭环）
- `tasks.yaml` 解析入库
- 分钟级调度提醒
- Android 轮询拉取提醒并触发本地通知
- App 完成/延期写回 `tasks.yaml` 并提交到 Git

### MVP-2（日记与捕获）
- App 一句话捕获到 `inbox/capture.md`
- 日志归档到 `daily/YYYY/YYYY-MM-DD.md`
- 从 capture/daily 提取候选 TODO（规则版，人工确认落盘）

### MVP-3（全局记忆与检索）
- SQLite FTS5 关键词检索
-（可选）向量检索与混合召回
- 偏好沉淀到 `core/identity.md`（带确认流程）

### 多端与可靠性
- 推送从“轮询”升级为 FCM（减少耗电、更及时）
- iOS 客户端（复用同一 API）
- 桌面托盘客户端（快速捕获 + 本地工作区联动）

