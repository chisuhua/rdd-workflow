## 1. 实施

- [x] 1.1 移除 append_approved 内部 echo（已由 commit 0232805 修复）
- [x] 1.2 验证单行输出：echo 不再产生重复行

## 2. 测试

- [x] 2.1 添加回归测试：test_state_append_approved.bats（3 用例）
- [x] 2.2 测试通过：单行输出 / return 0 / row insertion
