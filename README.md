## LING — 云端记忆助手（Git 驱动 + 提醒闭环 + Android）

这是一个"云端常驻 + Git 工作区为真相"的轻量级记忆/任务提醒系统：

- **记忆仓库**：Markdown / YAML 主数据（可审计、可回滚、可迁移）→ [LING-AGENT-memory](https://github.com/falling-feather/LING-AGENT-memory)
- **云端服务**：定时同步 Git、解析任务/日记、分钟级调度提醒、提供 HTTP API
- **Android App**：极简交互（任务查看/完成/延期/捕获）+ 后台轮询触发本地通知

### 仓库结构

| 路径 | 说明 |
|------|------|
| `docs/readme/`            | 面向用户的操作指南 |
| `docs/dev/`               | 面向开发者的架构、接口、实现说明 |
| `docs/roadmap/`           | 长期规划与演进路线 |
| `memory_repo_template/`   | 记忆仓库模板（你的私有 GitHub 仓库按此初始化） |
| `server/`                 | 云端服务设计文档 + Python MVP-1 实现 |
| `server/python/`          | Python 实现：indexer / scheduler / api / syncd |
| `deploy/`                 | systemd / Docker / 安装脚本 |
| `android/` *(此分支为占位)* | 设计文档；**Android 工程实质代码在 [`android` 分支](https://github.com/falling-feather/LING/tree/android)** |

### 分支策略

- **`main`**（当前）：服务端 + 文档 + 部署脚本 + 记忆仓库模板
- **`android`**：基于 `main`，多了完整的 Android 工程（Compose / WorkManager / OkHttp）

切换查看：

```bash
git fetch
git checkout android       # 看 Android 工程
git checkout main          # 回到服务端主线
```

二者**不会合并**：服务端和客户端独立演进，但共享同一个 HTTP API 契约（见 `server/api/DESIGN.md`）。

### 快速开始（概览）

1. 在 GitHub 创建一个**私有仓库**作为"记忆仓库"，按 `memory_repo_template/` 初始化。
2. 部署服务端：见 `deploy/README.md`（systemd / Docker / 本地开发都覆盖）。
3. 构建 Android App：`git checkout android`，然后 `cd android` 按 README 跑。
4. 在 App 里配置服务器地址 + API Key，看到任务列表即闭环。

更详细的角色分工与里程碑：`docs/dev/MILESTONES.md`。
