## 里程碑验收标准与时间预估（建议）

> 目标是“可跑、可追溯、可迭代”。下面以**单人开发**为基准预估；如果你对 C++/Android 都很熟，时间可再压缩 20–30%。

### MVP-1：提醒闭环（建议 3–5 天）
**范围**（必须全部完成才算 MVP-1 完成）：\n
- 记忆仓库：根目录 `tasks.yaml` + `ops/config.yaml`（按模板）\n
- 云端：\n
  - 能 clone 指定 GitHub 私有仓库到服务器 workdir\n
  - 能解析 `tasks.yaml` 入库到 SQLite（或等价存储）\n
  - Scheduler 分钟级生成 pending reminder 事件（不依赖 4 小时心跳）\n
  - API 提供 `GET /tasks`、`GET /reminders/pending`、`POST /tasks/{id}/complete`、`POST /tasks/{id}/reschedule`\n
  - 完成/延期会写回 `tasks.yaml` 并 `commit/push`（Git 历史可见）\n
- Android：\n
  - 可配置 baseUrl + API_KEY\n
  - 拉取任务列表并展示\n
  - 周期轮询 pending reminders 并弹系统通知\n
  - 点击通知可打开对应任务\n
\n
**验收用例**：\n
1. 在 `tasks.yaml` 新增一个 30 分钟后到期的任务（deadline）\n
2. 云端解析入库并产生提醒事件\n
3. App 在到点前能收到通知\n
4. 在 App 点“完成”，`tasks.yaml` 任务状态变更为 done，GitHub 上能看到 `[assistant]` 提交\n
\n
**时间预估**：\n
- 云端（最小可用）2–3 天\n
- Android（最小可用）1–2 天\n
\n
### MVP-2：日记与捕获（建议 5–7 天）\n
**范围**：\n
- `POST /capture`：App 一句话追加到 `inbox/capture.md` 并写回 Git\n
- 每日归档：每天固定时间在 `daily/YYYY/YYYY-MM-DD.md` 追加“今日摘要段”（规则模板即可）\n
- 候选 TODO：从 capture 里识别“截止/最晚/前/明天/周五”等关键词，生成候选任务列表（人工确认后写入 `tasks.yaml`）\n
\n
**验收用例**：\n
1. App 输入“周五前把 A 接口联调完”\n
2. `inbox/capture.md` 出现该行（Git 可追溯）\n
3. 服务器生成候选 TODO，App 可确认生成任务，写入 `tasks.yaml`\n
\n
### MVP-3：全局记忆检索与多端扩展（持续迭代）\n
**范围**：\n
- SQLite FTS5：对 `daily`、`core` 做关键词检索\n
-（可选）向量检索：embedding + 混合检索\n
- 推送升级：App 从高频轮询升级为 FCM\n
- iOS/桌面端：复用同一 API\n
\n
**验收用例**：\n
1. 在 App 输入关键词，能检索到相关 daily 片段与对应任务\n
2. 推送在设备休眠/省电模式下依然能可靠到达（FCM）\n

