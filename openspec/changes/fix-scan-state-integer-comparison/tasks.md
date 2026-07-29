# Fix scan-state integer comparison — 实施任务

## Task 1: 修复 `scan-state.sh` 中 2 处 `wc -l` 赋值 + 添加 bats 测试

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_scan_state_integer_comparison.bats`，定义修复行为：
   - `FS_ACTIVE_COUNT` 的 `wc -l` 输出经过 `tr -d '[:space:]'` 清理，当 `openspec/changes/` 只有 `archive/` 时，`$FS_ACTIVE_COUNT` 为纯数字 `0`
   - `DETACHED` 的 `wc -l` 输出经过 `tr -d '[:space:]'` 清理，当无 worktree 时，`$DETACHED` 为纯数字 `0`
   - 模拟 `wc -l` 输出含有尾随换行符的边缘情况，验证 `-eq` 和 `-gt` 比较不会报错
2. 验证测试失败（当前代码无 sanitize）
3. 在 `skills/guide/scripts/scan-state.sh` 中修复：
   - L95：`FS_ACTIVE_COUNT=$(cd "$PROJECT_ROOT" 2>/dev/null && ls -d openspec/changes/*/ 2>/dev/null | grep -v 'archive/' | wc -l || echo 0)` → 追加 `| tr -d '[:space:]'` 在 `wc -l` 之后
   - L127：`DETACHED=$(git worktree list 2>/dev/null | awk 'index($3, "[openspec/") == 1' | wc -l)` → 追加 `| tr -d '[:space:]'` 在 `wc -l` 之后
4. 验证测试通过
5. Commit

## Task 2: 修复所有 `skills/*/scripts/` 中 `wc -l` 赋值

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_scripts_wc_l_sanitize.bats`，验证：
   - `skills/guide-arch/scripts/arch_env_check.sh` L91/93/94 的 `wc -l` 赋值有 `tr -d '[:space:]'` 保护
   - `skills/guide-arch/scripts/arch_gap_analysis.sh` L73 的 `wc -l` 赋值有 `tr -d '[:space:]'` 保护
   - `skills/guide-plan/scripts/plan_done_gate.sh` L91 的 `wc -l` 赋值有 `tr -d '[:space:]'` 保护
   - `skills/guide-plan/scripts/plan_intake.sh` L22 的 `wc -l` 赋值有 `tr -d '[:space:]'` 保护
   - `skills/guide-ship/scripts/ship_done.sh` L23/25 的 `wc -l` 赋值有 `tr -d '[:space:]'` 保护
   - `skills/guide-ship/scripts/ship_plan.sh` L181/184 的 `wc -l` 赋值有 `tr -d '[:space:]'` 保护
2. 验证测试失败（当前代码无 sanitize）
3. 修复全部 6 个脚本文件中的 10 处 `wc -l` 赋值，每处追加 `| tr -d '[:space:]'`
4. 验证测试通过
5. Commit

## Task 3: 修复 SKILL.md 内联代码中的 `wc -l` 赋值 + 边缘情况 bats 测试

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_skill_md_wc_l_sanitize.bats`，验证：
   - `skills/guide-arch/SKILL.md` L173 的 `ADR_COUNT` 赋值有 `tr -d '[:space:]'` 保护
   - `skills/guide-ship/SKILL.md` L209 的 `WORKTREE_COUNT` 赋值有 `tr -d '[:space:]'` 保护
   - `skills/roadmap/SKILL.md` L211 的 `ADR_COUNT` 赋值有 `tr -d '[:space:]'` 保护
   - 模拟 `wc -l` 输出 `"0\n"`（含尾随换行符）的边缘情况，验证 `$FS_ACTIVE_COUNT` 在 `-eq` 比较中不报错
2. 验证测试失败（当前代码无 sanitize）
3. 修复 3 个 SKILL.md 文件中的内联 `wc -l` 赋值：
   - `skills/guide-arch/SKILL.md` L173：`... | wc -l` → `... | wc -l | tr -d '[:space:]'`
   - `skills/guide-ship/SKILL.md` L209：`... | wc -l || echo 0` → `... | wc -l | tr -d '[:space:]' || echo 0`
   - `skills/roadmap/SKILL.md` L211：`... | wc -l` → `... | wc -l | tr -d '[:space:]'`
4. 验证测试通过
5. Commit