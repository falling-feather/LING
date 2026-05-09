"""LING server (Python MVP-1).

模块拆分（与 server/{syncd,indexer,scheduler,api}/DESIGN.md 对应）：

- config:    加载 ops/config.yaml 与 server/config.yaml
- gitwork:   封装 git clone/pull/commit/push（subprocess）
- indexer:   解析 tasks.yaml -> SQLite，生成 reminders
- scheduler: 分钟级扫描 reminders -> events
- api:       HTTP API（Flask），写回 tasks.yaml 与 inbox/capture.md
- syncd:     APScheduler 后台心跳，串起 sync->index->schedule
"""
