# Harden Doc & Code Consistency

## Why

rdd-workflow v1.1 已发布（v1.0 → v1.1 拆分记录在 ADR-0001），但代码与文档之间存在 13+ 处不一致，导致：
- 用户在 USAGE.md 看到的工作流 ≠ `guide-ship.md` 实际实现
- bats 测试 `test_doc_phase_consistency.bats` 失败（ship-side phase 列表错误）
- 4 个 `_lib/` bash helper 存在但从未被调用（dead code / DRY 违反）
- `find_default_branch` 在 worktree 上下文中 fallback 到错误分支（潜在自合并 bug）
- `status.md` 示例输出仍使用 `/path/to/CppHDL`（旧项目名残留）

## What Changes

**In Scope**:
- 修复 USAGE.md 与 guide-ship.md 之间的 phase 编号/命名不一致
- 修复所有 skill 中硬编码的 `main` 分支引用（应动态检测 default branch）
- 删除或 wire-up 4 个 orphan `_lib/` bash helper（`safe_python_json`/`safe_python_yaml`/`read_suggestions`/`write_suggestions`/`is_change_committed`）
- 修复 `find_default_branch` 在 worktree 上下文中的 fallback bug
- 替换 `status.md`/`execute.md` 中重复定义的 `wt_path_for_branch_inline`
- 同步 ADR-0001 与当前实际架构（stage 列表 + subskill 数量）
- 同步 INSTALL.md 版本与 skill 列表
- 同步 `tests/README.md` 与实际文件布局
- 添加 ADR 引用格式 `ADR-NNNN` (4 位) 的一致性
- 同步 `proposal-suggestions-format.md` consumer 列表（添加 `deps.md`）

**Out of Scope**:
- 不重构整个 rdd-workflow 状态机
- 不修改 OpenSpec CLI 行为
- 不创建新的 ADR（只同步 ADR-0001 与代码现状）
- 不删除任何 skill（仅修正引用）
- 不修改 `proposal-suggestions.md` 格式
- 不修改 `tests/smoke.bats` 或 `tests/test_helper.bash`（基础设施）

## Capabilities

### New Capabilities

- `general`: harden-doc-consistency 实施的代码与文档一致性能力

### Modified Capabilities

<!-- Existing capabilities whose REQUIREMENTS are changing. Leave empty if no requirement changes. -->

## Impact

- **代码影响**: skills/*.md (11 个文件已修复) + skills/_lib/*.sh (3 个文件) + tests/README.md
- **依赖影响**: 0 (内部一致性硬化)
- **来源**: 2026-06-09 手动审计 + explore agent 报告
- **测试影响**: 预计 test_doc_phase_consistency.bats 全部通过；test_adr_directory.bats 13/14 通过
- **风险**: 低（纯修复性变更，无架构变更）
