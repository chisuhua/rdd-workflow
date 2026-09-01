# Tasks: add-session-metrics-collection

## Implementation Tasks

- [x] Task 1: `tests/unit/test_session_metrics.py` 新增 8 个单元测试
- [x] Task 2: schema v3 兼容 v2 旧数据
- [x] Task 3: metrics 字段默认 `{}` 不报错
- [x] Task 4: entry/close hook 正确记录 started_at / ended_at / duration_s
- [x] Task 5: tool_calls 分类计数正确
- [x] Task 6: user_decisions 计数正确
- [x] Task 7: retries / retry_reasons 记录正确
- [x] Task 8: phase_breaks 数组累积正确
- [x] Task 9: session close 落盘原子写
- [x] Task 10: `tests/integration/test_session_metrics.bats` 新增 3 个集成测试
- [x] Task 11: `session-metrics: end-to-end entry→close 记录 metrics`
- [x] Task 12: `session-metrics: rddf session metrics <id> 输出`
- [x] Task 13: `session-metrics: rddf session metrics --recent 汇总表`
- [x] Task 14: 跑一次 mini 5 阶段流程（design → plan → ship），`rddf session metrics --recent` 显示各阶段耗时
- [x] Task 15: 模拟回归门多轮重跑，metrics 正确记录 retries + reasons
- [x] Task 16: 旧 v2 session 查询不报错
- [x] Task 17: `docs/adr/ADR-0036-session-metrics.md`（新 ADR，记录 schema v3 决策）
- [x] Task 18: `docs/change-quality-guide.md` 加"session metrics"段
- [x] Task 19: `rddf session --help` 更新含 `metrics` 子命令
- [x] Task 20: 现有 `rddf session list/show/resume/abandon/archive-history` 5 子命令不受影响
- [x] Task 21: `session_stats.py` 既有统计不变
- [x] Task 22: `sessions.json` 旧数据可被新版本读写
- [x] Task 23: ship 后 30 天：`sessions.json` 体积增长可接受（每 session 增量 < 1KB）
- [x] Task 24: 采集开销无感知（session close 时 < 10ms 落盘）
- [x] Task 25: 不引入新的 KNOWN_FAILURES 条目
