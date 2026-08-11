# pre-checkout-warning

**优先级**: P2 | **来源**: 会话复盘 2026-07-23 — git checkout 破坏性回滚 proposal-suggestions.md
**阶段**: v2.1 | **分类**: developer-experience
**类型**: feature

## 架构依据

- `git checkout -- .` 将 `proposal-suggestions.md` 从 Markdown 索引回滚到旧 JSON 格式
- 根本原因：关键文件（proposal-suggestions.md、proposal-approved.md）的 Markdown 改写未被稳定地持久化到 git
- 虽然 `archive-cleanup-working-tree` 修复了归档后的残留清理，但 checkout 回滚仍是风险

## 范围

- **In Scope**:
  - 在关键工作流操作（arch-done、plan-done、ship-done）后自动检查关键文件是否与 HEAD 一致
  - 若不一致，"git status -- proposal-suggestions.md proposal-approved.md" 警告
  - 或在 guide/scan-state.sh 中增加关键文件完整性检查
- **Out Scope**:
  - 不修改 git 行为
  - 不自动提交文件（用户控制提交时机）

## 关键场景

- GIVEN proposal-suggestions.md 有未提交更改, WHEN 执行 guide/scan, THEN 提示"关键文件有未保存更改"

## 技术约束

- MUST 轻量（`git diff --name-only` 检查）
- SHOULD 在 guide 入口扫描时自动执行

## 验收标准

- guide 扫描时若 proposal-suggestions.md 有未提交更改，则显示警告