## 用户指南（readme）

这份文档面向日常使用者，目标是“最少配置即可用”。

### 你将得到什么

- **任务提醒**：根据 `tasks.yaml` 的 `deadline` 自动提醒（临近多次提醒 + 超期重复）
- **快速捕获**：在 App 里输入一句话，会追加到 `inbox/capture.md`
- **可审计**：所有变化都会落在 Git 历史里（可回滚）

### 一期使用流程（最小闭环）

1. 创建 GitHub 私有仓库，初始化为“记忆仓库”（目录结构见 `memory_repo_template/`）。
2. 服务器部署云端服务，并配置它 clone 你的记忆仓库到本地工作目录。
3. 在 `tasks.yaml` 新增任务并设置 `deadline`。
4. Android App 连接服务器并开启通知。
5. 到达提醒时间点，App 触发本地通知；你可在 App 上完成/延期，系统会写回 `tasks.yaml` 并推送到 GitHub。

### 记忆仓库中你最常编辑的文件

- `tasks.yaml`：任务清单（含截止时间）
- `daily/YYYY/YYYY-MM-DD.md`：每天追加的日志
- `inbox/capture.md`：随手记录区（系统会归档/提取候选任务）

