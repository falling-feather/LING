## GitSyncDaemon 设计（MVP-1）

### 目标
- 每 **4 小时心跳**同步 GitHub 私有仓库（pull/push）
- 发现变更后触发 Indexer 做增量解析
- 服务端写回（完成/延期/捕获）时保证“尽量自动解决冲突”，失败则落 patch 并停止自动 push

### 关键输入（建议写在 `server/config.yaml`）
- `workdir_path`：服务器本地 clone 目录（MemoryWorkdir）
- `repo_url`：GitHub 仓库地址（SSH 或 HTTPS）
- `branch`：默认 `main`
- `sync_interval_hours`：默认 4
- `git_author_name` / `git_author_email`：用于 `[assistant]` 提交

### 同步流程（心跳）
1. 确保 workdir 存在：不存在则 `git clone`。\n
2. 获取远端：`git fetch`。\n
3. 同步到远端最新：\n
   - `git pull --rebase`（优先）\n
   - 若失败：记录错误，进入“人工介入模式”（不再写回 push）\n
4. 计算增量：用 `git diff --name-only <oldsha>..<newsha>` 获取变更文件列表。\n
5. 触发 Indexer：\n
   - 最简单：写入 `index/changed_files.json` 并触发一次 indexer 扫描\n
   - 或：向本地 SQLite 写入 `workdir_state.last_git_sha` 并由 indexer 定时检测\n

### 写回（由 API 触发）
当 API 需要修改 `tasks.yaml` 或 `inbox/capture.md`：\n
1. `git pull --rebase`\n
2. 修改文件并落盘\n
3. `git add ...`\n
4. `git commit -m "[assistant] update tasks"`\n
5. `git push`\n
6. 若 push 失败（冲突）：\n
   - 生成 `ops/conflicts/<timestamp>.patch`（记录本次 intended change）\n
   - 将这次操作写入 `index/db.sqlite` 的 `events`（供 App 显示“需要处理”）\n

### 冲突策略（MVP-1）
- 默认只允许服务端写回的文件：`tasks.yaml`、`inbox/capture.md`、（二期）`daily/*.md`\n
- `tasks.yaml` 冲突时：不做智能合并（MVP-1 先保守），直接生成 patch 并要求人工解决\n

