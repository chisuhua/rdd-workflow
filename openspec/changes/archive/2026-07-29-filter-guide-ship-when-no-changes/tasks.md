# Filter guide-ship when no active changes - 实施任务

## Task 1: 在 `workflow_synthesizer.py` 中为 `all_options` 添加 `FS_ACTIVE_COUNT` 条件过滤 - DONE

**TDD 步骤**:
1. 在 `tests/integration/test_filter_guide_ship.bats` 中编写测试，验证：
   - 当 `FS_ACTIVE_COUNT == 0` 时，`_build_all_options()` 返回的选项中 `guide-ship` 的 `group` 为 `"disabled"`、`action` 为 `None`
   - 当 `FS_ACTIVE_COUNT > 0` 时，`guide-ship` 正常出现（`group: "stages"`）
2. 验证测试失败（条件未实现）
3. 在 `skills/_lib/workflow_synthesizer.py` 的 `_build_all_options()` 中新增条件判断：
   - 新增 `_count_active_changes(iteration)` 辅助函数统计非 archived changes
   - 若 `== 0`，将 `guide-ship` 的 `group` 设为 `"disabled"`，`action` 设为 `None`，description 追加 `"(无活跃 change)"`
   - 若 `> 0`，保持现有行为
   - `MenuOption.action` 字段类型放宽为 `Optional[str]` 以允许 `None`
4. 验证测试通过
5. Commit: `feat(filter-guide-ship): gate guide-ship option when no active changes`

## Task 2: 更新 `scan-state.sh` 决策树，无活跃 change 时不推荐 `guide-ship` - DONE

**TDD 步骤**:
1. 在 `tests/integration/test_filter_guide_ship.bats` 中编写测试，验证：
   - 模拟 `openspec/changes/` 仅含 `archive/` 的场景
   - 扫描结果中不包含 `guide-ship` 推荐
2. 验证测试失败（推荐仍存在）
3. 在 `skills/guide/scripts/scan-state.sh` 的 default path (9/10) 中，检查 `FS_ACTIVE_COUNT == 0`：
   - 若 `== 0`，推荐 `guide-plan`（"无活跃 change -> 进入变更生成 (跳过 guide-ship)"）
   - 若 `> 0`，保持推荐 `guide-ship`
4. 验证测试通过
5. Commit: `feat(filter-guide-ship): skip guide-ship recommendation when no active changes`

## Task 3: 端到端 bats 测试 - DONE

**TDD 步骤**:
1. 在 `tests/integration/test_filter_guide_ship.bats` 中编写 smoke 回归测试，验证：
   - 无活跃 change 时 `scan_state` 不报错且不推荐 `guide-ship`
   - 有活跃 change 目录时 `scan_state` 正常推荐 `guide-ship`
2. 验证测试通过
3. 运行 `bats tests/smoke.bats` 回归检查 - 全通过
4. Commit: `test(filter-guide-ship): add smoke regression test`
