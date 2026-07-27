# prompt-worktree-cleanup-before-stage

**优先级**: P3 | **来源**: Session 复盘 2026-07-26 — 13 WT issues 无人处理
**阶段**: v2.1 | **分类**: planning
**类型**: improvement

## 架构依据
- Session 复盘：scanner 检测到 13 个 `needs_review` 级别的 WT issues（1 deleted + 12 modified AGENTS.md 文件），`all_options` 包含 `🧹 清理 (13 issues)`，但用户在选择阶段命令（`guide-ship` → `guide-plan`）时从未被提示先清理再继续。
- 根因：`guide` 菜单展示阶段命令和清理选项为同级选择，用户在 15 个选项中优先选择高亮推荐项（`guide-ship`），"清理"选项被跳过。worktree 的脏状态在工作流阶段执行前未做阻断。
- 影响：未提交的 AGENTS.md 修改和已删除的计划文件积累，可能导致 guide-ship worktree 创建时的基线不一致或冲突。

## 范围
- **In Scope**:
  - 用户选择阶段命令（`guide-arch` / `guide-plan` / `guide-ship`）前，增加一步确认：
    - 如果 `WT_ISSUES_JSON` 非空且包含非 `info` 级别问题，弹出提示：
      ```
      ⚠️ 工作树有 13 个待处理问题（1 删除 + 12 修改）
      建议先清理再进入工作流阶段。
      
      1. 🧹 先清理（进入清理菜单）
      2. ⏭️  跳过，直接进入 [阶段名]
      ```
  - 清理菜单沿用现有 `🧹 清理 (13 issues)` 选项的实现
  - 用户选择"跳过"后正常进入阶段命令
- **Out Scope**:
  - 不修改 `WT_ISSUES_JSON` 的生成逻辑
  - 不影响 `WT_ISSUES_JSON` 为空时的正常流程
  - 不新增自动修复功能

## 关键场景
- GIVEN `WT_ISSUES_JSON` 有 13 个 issues WHEN 用户选择 `guide-ship` THEN 弹出清理确认步骤
- GIVEN `WT_ISSUES_JSON` 为空 WHEN 用户选择 `guide-ship` THEN 无弹窗直接进入
- GIVEN 用户选择"跳过" WHEN 确认弹窗展示 THEN 正常进入阶段命令

## 技术约束
- MUST 不阻塞流程——用户应能选择跳过
- MUST 不自动执行任何清理命令
- MUST 与现有 `all_options` 的清理选项实现一致

## 验收标准
- WT issues 非空时选择阶段命令弹出清理确认
- 用户可跳过清理继续
- 清理选项工作正常
- WT issues 为空时无弹窗