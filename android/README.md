## Android App（MVP）

一期目标：极简交互 + 后台轮询提醒 + 本地通知。\n

### MVP 功能
- 任务列表 / 任务详情（完成、延期、稍后提醒）
- 捕获输入（写入 `inbox/capture.md`）
- 后台轮询 `GET /reminders/pending`（WorkManager）
- 收到 pending reminder 后触发系统通知（点击进入任务详情）

### 实现建议（后续在工程中落地）
- UI：Jetpack Compose
- 网络：OkHttp + Kotlinx Serialization
- 本地缓存：Room
- 后台：WorkManager（PeriodicWorkRequest 15min 是系统下限；若要 1–5 分钟，可用前台服务/弹性策略，建议二期上 FCM 后取消高频轮询）

> 说明：Android 系统对高频后台轮询限制较多。\n
> MVP-1 先把“可用的提醒闭环”跑通；如果你确实需要 1–5 分钟级别稳定到达，建议尽快升级到 FCM 推送（MVP-2/3）。\n

