## Context

会话复盘 2026-07-31 实测：归档 `fix-plan-deps-candidates-import-guard` / `fix-rddf-session-lifecycle-binding` / `fix-test-infrastructure-and-skill-registration` 3 个 change 后，proposal-approved.md 的"已实施"表从 83 条审计记录坍缩到 1 条。根因是 `update_proposal_status.py:41-58` 的插入逻辑在遇到 `## 已实施` 章节时插入新行后 `break`，该行之后的所有内容从未写入输出文件。

## Goals / Non-Goals

**Goals:**
- `update_proposal_status(change_name, project_root) -> bool` 在已实施表非空时正确保留全部历史条目
- 连续归档多个 change 后，已实施表条目数满足 `final = original + archived_count`
- 新增"已实施表非空"场景的测试，锁定数据保留行为

**Non-Goals:**
- 不修改 `state.sh::mark_approved_completed`（另一条归档写入路径）
- 不修改 proposal-approved.md 文件格式/schema
- 不涉及 proposals-suggestions.md

## Decisions

1. **插入后继续写剩余行**：在 `## 已实施` 章节插入新行后，将原行之后的所有剩余行（表头、分隔线、旧条目）一并写入输出，而非 `break` 丢弃。
2. **保持语义不变**："从已批准区移除 + 插入已实施区"的语义与函数签名 `update_proposal_status(change_name, project_root) -> bool` 均不改变。
3. **测试覆盖**：在 `tests/integration/test_archive_proposal_status.bats` 新增用例——已实施表含 N 条历史记录时归档 1 个 change，断言 N 条旧记录全部保留、新条目插入表头之后。

## Risks / Trade-offs

- **修复面最小**：仅改动插入循环的控制流（`break` → 继续写剩余行），不触碰文件解析与行格式逻辑。
- **回归验证**：现有 `bats tests/integration/test_archive_proposal_status.bats`（空表用例）+ 新增非空表用例双覆盖；`python3 -m pytest tests/unit/ -q --tb=short` 全量回归确认无破坏。
- **数据恢复**：已损坏的 proposal-approved.md 可用修复后的脚本重跑恢复（重新标记已归档 change），无需手工修复文件。
