# Detect suggestions-approved inconsistency — 实施任务

## Task 1: DONE - 在 `skills/_lib/state.sh` 中添加 `detect_approved_inconsistency()` 函数

**TDD 步骤**:
1. 在 `tests/integration/test_approved_inconsistency.bats` 中编写测试，定义函数行为：
   - 当 `proposal-suggestions.md` 有 "completed" 条目且 `proposal-approved.md` 无对应记录时，输出包含 "⚠️" 的警告
   - 当 `proposal-suggestions.md` 有 "completed" 条目且 `proposal-approved.md` 也有对应记录时，无警告
   - 当 `proposal-suggestions.md` 不存在时，无输出（静默退出）
   - 当 `proposal-suggestions.md` 无 "completed" 条目时，无警告
2. 验证测试失败（函数不存在）
3. 在 `skills/_lib/state.sh` 中实现 `detect_approved_inconsistency()` 函数（env-var passing per Oracle C1）
4. 验证测试通过
5. Commit `feat(state): add detect_approved_inconsistency() for audit trail gaps`

## Task 2: DONE - 将检测集成到 `guide_entry.sh` 的 `guide_entry()` 扫描输出

**TDD 步骤**:
1. 在 `tests/integration/test_approved_inconsistency.bats` 中编写测试，验证：
   - `guide_entry.sh` 中存在 `detect_approved_inconsistency` 调用
   - `guide_entry.sh` source 了 state.sh
2. 验证测试失败
3. 在 `skills/guide/scripts/guide_entry.sh` 的 `guide_entry()` 函数中，在项目状态概览之后、`scan_session_binding` 之前，插入 `detect_approved_inconsistency` 调用（含 state.sh fallback sourcing）
4. 验证测试通过
5. Commit `feat(guide-entry): wire detect_approved_inconsistency into entry scan`

## Task 3: DONE - 端到端 bats 测试

**TDD 步骤**:
1. 在 `tests/integration/test_approved_inconsistency.bats` 中编写 e2e smoke 回归测试，验证：
   - 干净项目（无 proposal-suggestions.md）无误报
   - state.sh 既有函数（list_improvements）仍正常工作
2. 运行全部 9 个测试通过 + `bats tests/smoke.bats` 回归通过
3. Commit `test(approved-inconsistency): add e2e smoke regression tests`