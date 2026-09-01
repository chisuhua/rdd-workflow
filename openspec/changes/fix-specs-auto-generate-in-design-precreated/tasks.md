# Tasks: fix-specs-auto-generate-in-design-precreated

## Implementation Tasks

- [x] Task 1: `tests/unit/test_generate_full_proposal.py` 新增 5 个测试覆盖 specs/ 生成
- [x] Task 2: maps acceptance checkboxes to Requirements + Scenario
- [x] Task 3: maps Capabilities MUST/MUST NOT to Requirements
- [x] Task 4: maps GIVEN/WHEN/THEN to Scenario blocks
- [x] Task 5: preserves manual edits (idempotency)
- [x] Task 6: output passes openspec validate v1.4
- [x] Task 7: `tests/integration/test_specs_generation.bats` 新增 5 个 bats 测试
- [x] Task 8: `specs-generate: end-to-end approve_proposal.sh creates specs/`
- [x] Task 9: `specs-generate: idempotent skip when specs/ exists`
- [x] Task 10: `specs-generate: validate against openspec CLI`
- [x] Task 11: `specs-generate: requirements from Capabilities MUST`
- [x] Task 12: `specs-generate: scenarios from acceptance checkboxes`
- [x] Task 13: `tests/integration/test_propose_quality.py` 已有 design-level checks 扩展为覆盖 specs/ 必填
- [x] Task 14: 复现 2026-08-31 ship 阶段场景：批准 1 个新 P1 proposal → fill → 跑 `./test.sh --full --regression` → 0 新增失败（无需手工补 specs/）
- [x] Task 15: 端到端复测 5 阶段流程 1 个新 change: 0 个 spec validation error
- [x] Task 16: `openspec validate <new-change>` 直接调 CLI 返回 `Change '<name>' is valid`
- [x] Task 17: `openspec change show <new-change> --json --deltas-only` 输出非空（含至少 1 个 ADDED Requirement）
- [x] Task 18: AGENTS.md "D3 design-pre-created 协同" 段更新，明确 specs/ 现在由 design 阶段自动生成（含 commit 示例）
- [x] Task 19: `skills/guide-design/SKILL.md` D1 编排段补 specs/ 输出说明（在 proposal.md 描述后）
- [x] Task 20: `docs/proposal-approved-format.md` 加新章节描述 specs/ 与 proposal.md 的对应关系
- [x] Task 21: 复测 history 8 个 archived `phase-X-general-*` change：openspec validate 不参与 archive 目录，回归门 baseline 不变
- [x] Task 22: 复测现有 `bypass-audit-mechanism`（延迟状态）：proposal-suggestions.md 行为不变
- [x] Task 23: 与 `move-proposal-creation-to-design` (ADR-0025) 不冲突：D3 路径仍然只有 design 阶段落盘
- [x] Task 24: ship 后 30 天观察期：`guide-design approve` 调用成功率 / 回归门 0 新增率 提升 ≥ 90%（历史数据：每次 approve 后必须手工补 specs/）
- [x] Task 25: 不引入新的 KNOWN_FAILURES 条目（pre-existing WIP 不扩大）
