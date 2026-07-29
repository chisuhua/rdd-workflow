# Fix plan-done gate zero stale count - 实施任务

## Task 1: 修复 Gate 0 使用文件系统扫描 [DONE]

**TDD 步骤**:
1. 在 `tests/integration/test_plan_done_gate_zero_stale_count.bats` 中编写测试，定义修复行为：
   - `run_plan_done_gate` 在 `openspec/changes/` 有 3 个 active change 时，Gate 0 计数为 3
   - `run_plan_done_gate` 在 `openspec/changes/` 只有 `archive/` 时，Gate 0 计数为 0 -> 返回 1（拒绝）
   - `run_plan_done_gate` 在 `openspec/changes/` 有 1 个 active change + 2 个 archived 时，Gate 0 计数为 1
2. 验证测试失败（当前从 iteration.json 读取，计数不准确）
3. 修改 `skills/guide-plan/scripts/plan_done_gate.sh` L69-L79：
   - 替换 `PY_PROJECT_ROOT` 内联 Python 调用为文件系统扫描
   - 新代码：`PROPOSED_COUNT=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l | tr -d '[:space:]')`
   - 保持 `PROPOSED_COUNT` 变量名和下游 `-eq 0` 判断不变
   - 保持 `SKIP_GATE_0` 跳过逻辑不变
4. 验证测试通过
5. Commit

## Task 2: 添加归档后计数正确性 bats 测试 [DONE]

**TDD 步骤**:
1. 在 `tests/integration/test_plan_done_gate_zero_stale_count.bats` 中追加测试（延续 Task 1 的同文件），定义：
   - GIVEN 3 个 fixture change（`test-a`、`test-b`、`test-c`）已在 `openspec/changes/` 下创建
   - WHEN `test-a` 和 `test-b` 被归档（移动到 `archive/`）
   - THEN `run_plan_done_gate` 的 Gate 0 输出 `ready-for-ship: 1`
2. 验证测试失败（当前 Gate 0 读取 iteration.json 仍返回 3）
3. 修复已在 Task 1 完成，此步验证 Gate 0 修复后归档场景正确
4. 验证测试通过
5. 追加边界测试：
   - GIVEN 0 个 active change（全部归档）
   - WHEN `run_plan_done_gate` 执行
   - THEN Gate 0 返回 0 且函数返回 1（拒绝）
6. 验证所有测试通过
7. Commit

## Task 3: 集成测试 - 验证 plan_done_gate.py 传递后归档 [DONE]

**TDD 步骤**:
1. 在 `tests/integration/test_plan_done_gate_zero_stale_count.bats` 中追加集成测试：
   - 模拟完整 plan-done 流程：创建 2 个 change -> 运行 `plan_done_gate.sh` 的 `write_plan_handoff` -> 归档 1 个 change -> 再次运行 Gate 0
   - 验证归档后 Gate 0 计数从 2 降为 1
2. 验证测试通过
3. 运行 `bats tests/integration/test_plan_done_gate_extraction.bats` 确认现有测试不受影响
4. Commit
