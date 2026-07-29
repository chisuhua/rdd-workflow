# Filter guide-ship when no active changes — 实施任务

## Task 1: 在 `workflow_synthesizer.py` 中为 `all_options` 添加 `FS_ACTIVE_COUNT` 条件过滤

**TDD 步骤**:
1. 在 `tests/unit/` 中编写 `test_workflow_synthesizer_filter_guide_ship.py`，验证：
   - 当 `FS_ACTIVE_COUNT == 0` 时，`all_options()` 返回的选项中不包含 `group: "stages"` 的 `guide-ship`（或 `group: "disabled"`）
   - 当 `FS_ACTIVE_COUNT > 0` 时，`guide-ship` 正常出现（`group: "stages"`）
2. 验证测试失败（条件未实现）
3. 在 `skills/_lib/workflow_synthesizer.py` 的 `all_options()` 中新增条件判断：
   - 读取 `FS_ACTIVE_COUNT` 状态
   - 若 `== 0`，将 `guide-ship` 的 `group` 设为 `"disabled"`，`command` 设为 `None`，description 追加 `"(无活跃 change)"`
   - 若 `> 0`，保持现有行为
4. 验证测试通过
5. Commit

## Task 2: 更新 `scan-state.sh` 决策树，无活跃 change 时不推荐 `guide-ship`

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_scan_state_no_active_changes.bats`，验证：
   - 模拟 `openspec/changes/` 仅含 `archive/` 的场景
   - 扫描结果中不包含 `guide-ship` 推荐
2. 验证测试失败（推荐仍存在）
3. 在 `skills/guide/scan-state.sh` 中，检查 `FS_ACTIVE_COUNT == 0` 的路径：
   - path 7、8、9、10 等可能推荐 `guide-ship` 的路径，改为推荐 `guide-arch` 或 `guide-plan`
   - 或添加全局哨兵：在路径选择前若 `FS_ACTIVE_COUNT == 0`，则跳过所有 `guide-ship` 推荐
4. 验证测试通过
5. Commit

## Task 3: 端到端 bats 测试

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_filter_guide_ship_e2e.bats`，验证：
   - 模拟无活跃 change 环境，运行 `guide_entry`，确认菜单不包含 `guide-ship` 或显示为 disabled
   - 模拟有活跃 change 环境，运行 `guide_entry`，确认 `guide-ship` 正常出现
2. 验证测试失败
3. 实现端到端测试
4. 验证测试通过
5. Commit