## 1. 实施

- [x] 1.1 创建 propose_quality_hook.py 入口（5 检查 + JSON 持久化）
- [x] 1.2 创建 propose_quality_hook.sh bash 包装器
- [x] 1.3 在 propose.md Phase 4 骨架/完整分支后调用 quality hook
- [x] 1.4 在 gate.py plan_done 中注册 propose_quality_checks 检查

## 2. 测试

- [x] 2.1 添加 tests/unit/test_propose_quality_hook.py 单元测试
- [x] 2.2 扩展 tests/unit/test_gate.py 的 plan_done 行为测试
- [x] 2.3 添加 tests/integration/test_propose_quality_hook.bats 集成测试
- [x] 2.4 运行目标测试与全量验证
