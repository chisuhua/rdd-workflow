# Pre-checkout Warning — 关键文件 checkout 回滚保护

**优先级**: P2  
**阶段**: v2.1  
**分类**: developer-experience  

## 概要

`git checkout -- .` 等破坏性操作会将 `proposal-suggestions.md` 和 `proposal-approved.md` 等关键文件从 Markdown 格式回滚到旧版本。本 change 在 guide/scan-state.sh 中增加关键文件脏检查，在用户执行可能导致数据丢失的 checkout 前发出警告。

## 背景

- 会话复盘 2026-07-23 发现：`git checkout -- .` 将 `proposal-suggestions.md` 从 Markdown 索引回滚到旧 JSON 格式
- 根本原因：关键文件（proposal-suggestions.md、proposal-approved.md）的 Markdown 改写未被稳定地持久化到 git
- 虽然 `archive-cleanup-working-tree` 修复了归档后的残留清理，但 checkout 回滚仍是风险

## 范围

### In Scope

- 在关键工作流操作（arch-done、plan-done、ship-done）后自动检查关键文件是否与 HEAD 一致
- 若不一致，显示 "git status -- proposal-suggestions.md proposal-approved.md" 警告
- 在 guide/scan-state.sh 中增加关键文件完整性检查

### Out Scope

- 不修改 git 行为
- 不自动提交文件（用户控制提交时机）

## 验收标准

- guide 扫描时若 proposal-suggestions.md 或 proposal-approved.md 有未提交更改，则显示警告
- 警告内容包含文件名和 `git add` 建议