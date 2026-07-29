# Prompt worktree cleanup before stage commands

**优先级**: P3  
**阶段**: v2.1  
**分类**: planning

## 概要

当用户从 `guide` 菜单选择阶段命令（`guide-arch` / `guide-plan` / `guide-ship`）时，如果工作树存在待处理问题（`WT_ISSUES_JSON` 非空且包含非 `info` 级别问题），弹窗提示用户先清理再进入阶段命令，避免脏工作树导致后续流程异常。

## 背景

- Session 复盘 2026-07-26 发现：scanner 检测到 13 个 `needs_review` 级别的 WT issues（1 deleted + 12 modified 文件），`all_options` 包含 `🧹 清理 (13 issues)`，但用户在选择阶段命令（`guide-ship`）时从未被提示先清理再继续。
- 根因：`guide` 菜单展示阶段命令和清理选项为同级选择，用户在 15 个选项中优先选择高亮推荐项（`guide-ship`），"清理"选项被跳过。
- 影响：未提交的修改和已删除的计划文件积累，可能导致 guide-ship worktree 创建时的基线不一致或冲突。

## 范围

### In Scope

- 用户选择阶段命令（`guide-arch` / `guide-plan` / `guide-ship`）前，AI 检查 `WT_ISSUES_JSON` 状态
- 如果 `WT_ISSUES_JSON` 非空且包含非 `info` 级别问题，弹出提示：
  ```
  ⚠️ 工作树有 N 个待处理问题（M 删除 + K 修改）
  建议先清理再进入工作流阶段。

  1. 🧹 先清理（进入清理菜单）
  2. ⏭️  跳过，直接进入 [阶段名]
  ```
- 清理菜单沿用现有 `🧹 清理 (N issues)` 选项的实现
- 用户选择"跳过"后正常进入阶段命令

### Out Scope

- 不修改 `WT_ISSUES_JSON` 的生成逻辑
- 不影响 `WT_ISSUES_JSON` 为空时的正常流程
- 不新增自动修复功能（AI 仍不自动执行命令）
- 不修改 `workflow_synthesizer.py` 的 `_build_all_options()` 或 `_detect_working_tree_issues()` 逻辑

## 验收标准

- `WT_ISSUES_JSON` 非空时选择阶段命令弹出清理确认
- 用户可跳过清理继续
- 清理选项工作正常
- `WT_ISSUES_JSON` 为空时无弹窗