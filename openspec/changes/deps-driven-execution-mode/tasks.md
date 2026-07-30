# Tasks: deps-driven-execution-mode

## Wave 1: 核心功能（P1）

- [x] `deps_output.py` 新增 `analyze_execution_mode()` 函数
- [x] `deps_output.py` 写入 `execution_mode_recommendations` 到 JSON
- [x] `plan_done_gate.sh` 写入 `execution_mode_decisions` 到 handoff
- [x] `ship_plan.sh` 读取并使用决策
- [x] 单元测试 + 集成测试

## Wave 2: 优化与增强（P2）

- [x] 批量处理优化策略（wave 分组）
- [x] 用户手动覆盖机制
- [x] 日志与可视化改进
- [x] 文档更新

## Wave 3: 监控与调优（P3）

- [x] 收集实际使用数据
- [x] 调整阈值参数
- [x] 性能优化