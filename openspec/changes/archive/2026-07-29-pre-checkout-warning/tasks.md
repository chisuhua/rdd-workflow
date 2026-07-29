# Pre-checkout Warning - 实施任务

> **状态: 全部完成 (DONE)** - 3/3 tasks implemented & committed on branch `openspec/pre-checkout-warning`.
> - Task 1 commit: `feat(pre-checkout): add check_dirty_key_files to state.sh`
> - Task 2 commit: `feat(pre-checkout): wire dirty check into scan-state.sh`
> - Task 3 commit: `test(pre-checkout): add end-to-end smoke test`
> - Tests: 5/5 pass (`bats tests/integration/test_pre_checkout_warning.bats`)
> - Smoke sweep: 8/8 pass (`bats tests/smoke.bats`), 0 regressions.

## Task 1: 在 `skills/_lib/state.sh` 中添加脏检查函数 [DONE]

**TDD 步骤**:
1. 在 `tests/_lib/` 中编写 `test_state_dirty_check.bats`，定义 `check_dirty_key_files()` 的行为：
   - 当 proposal-suggestions.md 有未提交更改时，输出包含 "⚠️" 的警告
   - 当 proposal-approved.md 有未提交更改时，输出包含 "⚠️" 的警告
   - 当两个文件都干净时，无输出
2. 验证测试失败（函数不存在）
3. 在 `skills/_lib/state.sh` 中实现 `check_dirty_key_files()` 函数
4. 验证测试通过
5. Commit

## Task 2: 将脏检查集成到 `guide/scan-state.sh` 的路径 4/5 [DONE]

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_scan_state_dirty_check.bats`，验证：
   - 在该路径执行时调用 `check_dirty_key_files`
   - 脏文件存在时输出警告
2. 验证测试失败
3. 在 `skills/guide/scan-state.sh` 的路径 4/5（展示 guide-ship/guide-plan 选项之前）插入 `check_dirty_key_files` 调用
4. 验证测试通过
5. Commit

## Task 3: 端到端 bats 测试 [DONE]

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_pre_checkout_warning_e2e.bats`，验证：
   - 模拟脏文件场景，运行 guide 扫描，确认警告输出
   - 验证干净文件场景无警告输出
2. 验证测试失败
3. 实现端到端测试
4. 验证测试通过
5. Commit
