# fix-update-proposal-status-data-loss

**优先级**: P0 | **来源**: 会话复盘 2026-07-31 — 归档 3 个 change 后 proposal-approved.md 已实施表从 83 条坍缩到 1 条
**阶段**: v2.1 | **分类**: core-impl
**类型**: fix

## 架构依据

- `skills/propose/scripts/update_proposal_status.py`（`archive-update-proposal-status` 改进引入）在归档时更新 proposal-approved.md
- 会话复盘 2026-07-31 实测：归档 `fix-plan-deps-candidates-import-guard` / `fix-rddf-session-lifecycle-binding` / `fix-test-infrastructure-and-skill-registration` 3 个 change 后，proposal-approved.md 的"已实施"表从 83 条审计记录坍缩到 1 条（仅剩最后归档的 change）——**历史审计数据被静默破坏**
- 根因：`update_proposal_status.py:41-58` 的插入逻辑在遇到 `## 已实施` 章节时插入新行后 `break`，导致该行之后的所有内容（表头、分隔线、全部旧条目）**从未写入输出文件**

## 范围

- **In Scope**:
  - `skills/propose/scripts/update_proposal_status.py` — 修复插入逻辑（插入新行后继续保留剩余行，而非 break 丢弃）
  - `tests/integration/test_archive_proposal_status.bats` — 补充"已实施表非空"场景测试（现有测试只覆盖空表，未暴露此 bug）
- **Out Scope**:
  - 不修改 `state.sh::mark_approved_completed`（另一条写入路径，本会话验证幂等正常）
  - 不修改 proposal-approved.md 文件格式/schema
  - 不涉及 proposals-suggestions.md

## 关键场景

- GIVEN proposal-approved.md 已实施表有 N 条历史记录, WHEN 归档 1 个 change 调用 `update_proposal_status`, THEN 新条目正确插入表头之后, 且 N 条旧记录**全部保留**（当前：旧记录全部丢失）
- GIVEN 连续归档多个 change, WHEN 每次调用 `update_proposal_status`, THEN 已实施表条目数 = 原始数 + 归档数（当前：每次归档后条目数递减）
- GIVEN 已实施表为空（仅表头）, WHEN 归档, THEN 新条目插入表头之后（保持现有行为不变）

## 技术约束

- MUST 修复后已实施表条目数满足：`final = original + archived_count`
- MUST NOT 改变"从已批准区移除 + 插入已实施区"的语义
- MUST NOT 改变函数签名 `update_proposal_status(change_name, project_root) -> bool`
- MUST 补充单元/bats 测试覆盖"已实施表非空"场景（现有 `test_archive_proposal_status.bats:9-49` 只测空表）
- SHOULD 在修复前用脚本验证当前文件条目数，修复后对比确认恢复

## 验收标准

- 归档 1 个 change 后已实施表旧条目全部保留，新条目插入表头之后
- 连续归档 3 个 change 后条目数 = 原始数 + 3
- `bats tests/integration/test_archive_proposal_status.bats` 全部通过（含新增非空表用例）
- `python3 -m pytest tests/unit/ -q --tb=short` 全量回归通过
- 已损坏的 proposal-approved.md 可用修复后的脚本重跑恢复（重新标记已归档 change）
