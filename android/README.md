## Android App（MVP-1）

一期目标：极简交互 + 后台轮询 + 系统通知。

### 功能

- **任务列表**（GET `/tasks`）：服务器拉取，下拉/按钮刷新
- **任务详情**：完成（POST `/tasks/{id}/complete`）/ 稍后提醒（snooze 15/60/240）
- **快速捕获**（POST `/capture`）：写一句话，由服务端追加到 `inbox/capture.md`
- **设置页**：服务器地址、API Key、后台轮询间隔、连接测试
- **后台轮询**：WorkManager 周期触发 `ReminderWorker`，命中 pending reminder 时通过 `NotificationManager` 弹系统通知
- **通知 deep link**：点击通知通过 `ling://task/<id>` 直接跳到对应任务详情

### 工程结构

```
android/
├── settings.gradle.kts
├── build.gradle.kts
├── gradle.properties
├── gradle/wrapper/gradle-wrapper.properties
└── app/
    ├── build.gradle.kts
    ├── proguard-rules.pro
    └── src/main/
        ├── AndroidManifest.xml
        ├── res/                       (strings/themes/colors/icons/...)
        └── java/app/ling/client/
            ├── LingApp.kt             (Application：通道初始化 + WorkManager 注册)
            ├── MainActivity.kt        (Compose host + 通知权限请求)
            ├── data/
            │   ├── Models.kt          (Task / ReminderEvent / 请求响应 DTO)
            │   └── Settings.kt        (DataStore 持久化)
            ├── net/LingClient.kt      (OkHttp + kotlinx-serialization)
            ├── notif/ReminderNotifier.kt
            ├── work/
            │   ├── ReminderWorker.kt
            │   └── WorkScheduler.kt
            └── ui/
                ├── Theme.kt
                ├── Nav.kt             (Compose Navigation + 底部 Tab + deep link)
                ├── TaskListScreen.kt
                ├── TaskDetailScreen.kt
                ├── CaptureScreen.kt
                └── SettingsScreen.kt
```

### 工具链与版本

| 项目 | 版本 |
|------|------|
| AGP  | 8.4.1 |
| Gradle | 8.7 |
| Kotlin | 1.9.24 |
| Compose Compiler | 1.5.14 |
| Compose BOM | 2024.05.00 |
| compileSdk | 34 |
| minSdk | 26 |
| targetSdk | 34 |
| Java | 17 |

### 首次构建（本地）

> 仓库不包含 `gradle-wrapper.jar`（二进制），第一次构建需要先生成它。

```powershell
# Windows PowerShell
cd android
# 用 Android Studio 打开 android/ 目录，IDE 会自动同步并生成 wrapper.jar
# 或者：用本机 gradle 生成一次（之后即可使用 ./gradlew）
gradle wrapper --gradle-version 8.7
.\gradlew.bat assembleDebug
```

```bash
# Linux/macOS
cd android
gradle wrapper --gradle-version 8.7
./gradlew assembleDebug
```

如果你没装 gradle，也可以直接用 **Android Studio 打开 `android/` 目录**，IDE 会自动同步并生成 wrapper jar，再点 Run 即可。

构建产物：`app/build/outputs/apk/debug/app-debug.apk`。

### 运行

1. 安装 APK 到手机：`adb install app/build/outputs/apk/debug/app-debug.apk`
2. 第一次启动：进入「设置」
   - 服务器地址：`http://<你的服务器 IP>:8765`
   - API Key：与服务端 `config.yaml` 中 `server.api_key` 一致
   - 点「测试连接」，看到"连接成功 ✓"即 OK
3. 回到「任务」页应该立刻能看到服务端 `tasks.yaml` 里的任务
4. 「捕获」页随便写一句，提交后服务端会 commit/push 到 `inbox/capture.md`
5. 等到任务接近 deadline，App 后台轮询会触发系统通知；点通知进详情，点完成会写回 `tasks.yaml` 并 push

### 已知约束（MVP-1）

- 后台轮询周期最低 **15 分钟**（系统对 WorkManager 的硬性下限）。如果你需要 1–5 分钟级提醒：
  - **方案 A（不推荐）**：前台服务，常驻通知 + 高耗电
  - **方案 B（推荐，二期）**：服务端接 FCM，App 取消轮询直接收推送
- 设备处于深度待机（Doze）时，轮询周期可能被系统拉长到 30 分钟+；这是 Android 的正常行为
- 当前未做本地缓存（Room）：每次进入页面都向服务端拉取。在地铁等弱网下体验会差一些，二期再加

### 设计参考

- `android/MVP_DESIGN.md`：早期 MVP 设计草案
- `server/api/DESIGN.md`：HTTP API 契约（与 `LingClient` 一一对应）
