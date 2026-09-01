# Tasks: fix-design-done-gate-status-prefix-match

## Implementation Tasks

- [ ] Task 1: `tests/unit/test_design_done_gate.sh` 5 个单元测试 PASS（含延迟带后缀回归测试）
- [ ] Task 2: `tests/integration/test_design_done_gate.bats` 2 个集成测试 PASS
- [ ] Task 3: 复测 `proposal-suggestions.md` 当前含 `延迟 (2026-08-28...)` 状态时 gate 通过
- [ ] Task 4: 模拟 2 个带后缀状态 + 1 个待审查：gate 正确列出仅 1 个 pending
- [ ] Task 5: 模拟全部带后缀（已批准* / 延迟* / 已拒绝*）：gate 通过
- [ ] Task 6: 与 `fix-specs-auto-generate-in-design-precreated` (P0-1) 无交互：approve 流程不变，仅 gate 检查修复
- [ ] Task 7: `skills/guide-design/SKILL.md` Phase 4 更新为 source helper（或明确前缀匹配语义注释）
- [ ] Task 8: `docs/change-quality-guide.md` 加"proposal 状态后缀"说明段（状态可带 `(日期, 理由)` 后缀，gate 用前缀匹配）
- [ ] Task 9: 复测 `bypass-audit-mechanism`（延迟 + 后缀）design-done 通过，无需人工 Python 绕过
- [ ] Task 10: 复测 `proposal-approved.md` 的 `已实施` 状态不受影响（那是 approve 后的归档状态，不走 design-done）
- [ ] Task 11: 与 `design_done_gate.py`（Hub gates）不冲突：check-hub-pending / check-cross-repo-approvals 仍接线
- [ ] Task 12: ship 后 30 天观察期：design-done gate 人工绕过次数降至 0（历史：每次 3-5 分钟）
- [ ] Task 13: 不引入新的 KNOWN_FAILURES 条目
