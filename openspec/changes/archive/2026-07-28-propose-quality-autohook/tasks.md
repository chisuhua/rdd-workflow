## 1. 实施

- [x] 1.1 propose_quality_hook.py + .sh — Phase 4 质量检查钩子
- [x] 1.2 propose.md — 继骨架/完整分支后调用 hook
- [x] 1.3 gate.py — 注册 propose_quality_checks 到 plan_done

## 2. 测试

- [x] 2.1 Python 单元测试（26 用例）：propose_quality_hook + gate
- [x] 2.2 bats 集成测试（6 用例）：wrapper 存在 / 有效/损坏 proposal 退出码
