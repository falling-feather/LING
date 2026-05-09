## 云端记忆助手（Git 驱动 + 提醒闭环 + Android）

这是一个“云端常驻 + Git 工作区为真相”的轻量级记忆/任务提醒系统：

- **记忆仓库**：以 Markdown/YAML 文件作为主数据（可审计、可回滚、可迁移）
- **云端服务**：定时同步 Git、解析任务与日记、分钟级调度提醒、提供 API
- **Android App**：极简交互（任务查看/完成/延期/捕获）+ 后台轮询触发本地通知

### 仓库结构

- `docs/readme/`：面向用户的操作指南
- `docs/dev/`：面向开发者的架构、接口、实现说明
- `docs/roadmap/`：长期规划与演进路线
- `memory_repo_template/`：记忆仓库模板（你自己的私有 GitHub 仓库建议按此结构初始化）
- `server/`：云端服务（C++）
- `android/`：Android App（Kotlin）

### 快速开始（概览）

1. 在 GitHub 创建一个**私有仓库**作为“记忆仓库”，并按 `memory_repo_template/` 初始化目录与文件。
2. 在服务器上部署 `server/` 下的服务（`syncd/indexer/scheduler/api`）。
3. Android 安装 `android/` 编译出的 App，配置服务器地址与 API_KEY，开启提醒权限。

更详细步骤见 `docs/readme/`。

