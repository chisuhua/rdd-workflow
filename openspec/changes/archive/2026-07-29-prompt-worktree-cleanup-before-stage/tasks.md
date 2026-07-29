# Prompt worktree cleanup before stage commands — 实施任务

## Task 1: 在 `guide/SKILL.md` 中新增"阶段命令门控"步骤 [DONE]

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_guide_worktree_gate.bats`，验证：
   - 当 `WT_ISSUES_JSON` 非空且有非 `info` 级别 issue 时，`guide_entry` 输出中包含清理提示
   - 当 `WT_ISSUES_JSON` 为空时，`guide_entry` 输出中不包含清理提示
2. 验证测试失败（门控步骤未实现）
3. 在 `skills/guide/SKILL.md` 的"执行选择"章节（第 173-191 行）中，在阶段命令执行前新增门控步骤：
   - 在 `### 执行选择` 章节开头增加：
     ```
     ### 阶段命令门控（工作树检查）
     
     当用户选择阶段命令（`guide-arch` / `guide-plan` / `guide-ship`）时，AI 必须在执行 `skill_use()` 前检查 `WT_ISSUES_JSON`：
     
     - 如果 `WT_ISSUES_JSON` 为空或仅含 `info` 级别 issue → 直接执行，无提示
     - 如果 `WT_ISSUES_JSON` 非空且包含非 `info` 级别 issue → 展示提示：
       ```
       ⚠️ 工作树有 N 个待处理问题（M 删除 + K 修改）
       建议先清理再进入工作流阶段。
       
       1. 🧹 先清理（进入清理菜单）
       2. ⏭️  跳过，直接进入 [阶段名]
       ```
     - 用户选择"跳过"后正常执行 `skill_use()`
     - 用户选择"清理"后，引导用户选择 `🧹 清理 (N issues)` 菜单项
     ```
   - 在阶段命令执行列表（`guide-arch` / `guide-plan` / `guide-ship`）前增加引用门控步骤的注释
4. 验证测试通过
5. Commit

## Task 2: 更新 `guide/SKILL.md` 的"工作树清理分析"章节，与门控步骤联动 [DONE]

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_guide_worktree_gate_flow.bats`，验证：
   - 完整流程：菜单展示 → 用户选择阶段命令 → 门控弹窗 → 用户选择"清理" → 进入清理菜单
   - 完整流程：菜单展示 → 用户选择阶段命令 → 门控弹窗 → 用户选择"跳过" → 进入阶段命令
2. 验证测试失败（联动逻辑未实现）
3. 在 `skills/guide/SKILL.md` 的"工作树清理分析"章节（第 69-87 行）末尾，增加与门控步骤的联动说明：
   - 清理分析结果不仅用于菜单展示前的分析，也用于阶段命令门控
   - 门控步骤在"执行选择"阶段触发，使用相同的数据（`WT_ISSUES_JSON`）
4. 验证测试通过
5. Commit

## Task 3: 端到端 bats 测试——验证清理门控在三种阶段命令下均生效 [DONE]

**TDD 步骤**:
1. 在 `tests/integration/` 中编写 `test_guide_worktree_gate_e2e.bats`，验证：
   - 模拟 `WT_ISSUES_JSON` 有 5 个 issues，用户选择 `guide-ship` → 弹窗 → 选择"跳过" → 进入 `guide-ship`
   - 模拟 `WT_ISSUES_JSON` 有 5 个 issues，用户选择 `guide-plan` → 弹窗 → 选择"跳过" → 进入 `guide-plan`
   - 模拟 `WT_ISSUES_JSON` 有 5 个 issues，用户选择 `guide-arch` → 弹窗 → 选择"跳过" → 进入 `guide-arch`
   - 模拟 `WT_ISSUES_JSON` 为空，用户选择 `guide-ship` → 无弹窗 → 直接进入
   - 模拟 `WT_ISSUES_JSON` 有 5 个 issues，用户选择 `guide-ship` → 弹窗 → 选择"清理" → 进入清理菜单
2. 验证测试失败（门控逻辑未完全实现）
3. 实现端到端测试，确保新步骤与现有 `guide_entry` 流程兼容
4. 验证测试通过
5. Commit