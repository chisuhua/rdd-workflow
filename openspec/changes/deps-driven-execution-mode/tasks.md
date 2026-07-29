# Tasks: deps-driven-execution-mode

## Wave 1: 核心功能（P1）

- [ ] `deps_output.py` 新增 `analyze_execution_mode()` 函数
- [ ] `deps_output.py` 写入 `execution_mode_recommendations` 到 JSON
- [ ] `plan_done_gate.sh` 写入 `execution_mode_decisions` 到 handoff
- [ ] `ship_plan.sh` 读取并使用决策
- [ ] 单元测试 + 集成测试

## Wave 2: 优化与增强（P2）

- [ ] 批量处理优化策略（wave 分组）
- [ ] 用户手动覆盖机制
- [ ] 日志与可视化改进
- [ ] 文档更新

## Wave 3: 监控与调优（P3）

- [ ] 收集实际使用数据
- [ ] 调整阈值参数
- [ ] 性能优化