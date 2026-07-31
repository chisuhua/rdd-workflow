## Why

会话复盘 2026-07-31 归档 3 个 change 后，proposal-approved.md 的"已实施"表从 83 条审计记录坍缩到 1 条（仅剩最后归档的 change），**历史审计数据被静默破坏**。

根因：`skills/propose/scripts/update_proposal_status.py:41-58` 的插入逻辑在遇到 `## 已实施` 章节时插入新行后 `break`，导致该行之后的所有内容（表头、分隔线、全部旧条目）**从未写入输出文件**。`update_proposal_status.py`（由 `archive-update-proposal-status` 改进引入）在归档时更新 proposal-approved.md，其"从已批准区移除 + 插入已实施区"语义在已实施表非空时丢失全部历史记录。

## What Changes

- `skills/propose/scripts/update_proposal_status.py` — 修复插入逻辑：插入新行后继续保留剩余行（不再 `break` 丢弃），使已实施表的旧条目全部保留。
- `tests/integration/test_archive_proposal_status.bats` — 补充"已实施表非空"场景测试（现有测试只覆盖空表，未暴露此 bug）。

## Capabilities

### New Capabilities
- `update-proposal-status-data-preservation`: 归档时正确保留已实施表的历史条目（`final = original + archived_count`）

### Modified Capabilities
<!-- 无 spec 级行为变更 -->

## Impact

**In Scope:**
- `skills/propose/scripts/update_proposal_status.py` — 插入逻辑修复（插入新行后继续写剩余行）
- `tests/integration/test_archive_proposal_status.bats` — 新增非空表场景测试
- 已损坏的 proposal-approved.md 用修复后的脚本重跑恢复

**Out of Scope:**
- 不修改 `state.sh::mark_approved_completed`（另一条写入路径，已验证幂等正常）
- 不修改 proposal-approved.md 文件格式/schema
- 不涉及 proposals-suggestions.md
