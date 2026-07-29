# Detect suggestions-approved inconsistency — 实施任务

## Task 1: 在 `skills/_lib/state.sh` 中添加 `detect_approved_inconsistency()` 函数

**TDD 步骤**:
1. 在 `tests/_lib/` 中编写 `test_approved_inconsistency_detect.bats`，定义函数行为：
   - 当 `proposal-suggestions.md` 有 "completed" 条目且 `proposal-approved.md` 无对应记录时，输出包含 "⚠️" 的警告
   - 当 `proposal-suggestions.md` 有 "completed" 条目且 `proposal-approved.md` 也有对应记录时，无警告
   - 当 `proposal-suggestions.md` 不存在时，无输出（静默退出）
   - 当 `proposal-suggestions.md` 无 "completed" 条目时，无警告
2. 验证测试失败（函数不存在）
3. 在 `skills/_lib/state.sh` 中实现 `detect_approved_inconsistency()` 函数
4. 验证测试通过
5. Commit

## Task 2: 将检测集成到 `guide_entry.sh` 的 `guide_entry()` 扫描输出

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_guide_entry_approved_inconsistency.bats`，验证：
   - 在 `guide_entry` 执行时，若存在不一致，输出包含 "⚠️" 的警告
   - 一致状态下无警告输出
2. 验证测试失败
3. 在 `skills/guide/scripts/guide_entry.sh` 的 `guide_entry()` 函数中，在项目状态概览之后、`scan_session_binding` 之前，插入 `detect_approved_inconsistency` 调用
4. 验证测试通过
5. Commit

## Task 3: 端到端 bats 测试

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_detect_approved_inconsistency_e2e.bats`，验证：
   - 模拟 suggest 有 "completed" 但 approved 缺失的场景，运行 guide_entry 确认警告输出
   - 验证 suggest 有 "completed" 且 approved 也有对应记录的场景无警告输出
   - 验证 suggest 文件不存在的场景无警告输出
2. 验证测试失败
3. 实现端到端测试
4. 验证测试通过
5. Commit