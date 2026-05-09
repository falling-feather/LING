## server（云端服务）

一期实现 4 个逻辑模块（轻量、可常驻）：
- `syncd`：Git 同步（默认 4 小时心跳）
- `indexer`：解析 `tasks.yaml`/`inbox`/`daily` 入库
- `scheduler`：分钟级扫描提醒并生成 pending 事件
- `api`：HTTP API（Android 轮询、任务操作、捕获输入），并负责写回 Git

每个模块在 `syncd/` `indexer/` `scheduler/` `api/` 子目录下都有对应的 `DESIGN.md`（语言无关的设计契约）。

### MVP-1 实现：Python

实际可运行代码在 `server/python/`，参见 `server/python/README.md`。
- 入口：`python -m ling_server.cli -c config.yaml serve`
- 全部 4 个模块以 Python 模块形式落地，共享同一个 SQLite 数据库

### 后续：C++

`DESIGN.md` 中描述的 schema 与 HTTP 接口在 C++ 实现里保持一致即可平滑迁移；本目录在引入 C++ 工程前不会包含 CMake。
