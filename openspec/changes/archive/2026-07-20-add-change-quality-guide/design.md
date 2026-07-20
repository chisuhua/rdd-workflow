# Design: add-change-quality-guide

> Plan D of the improve-change-quality initiative. Creates
> `docs/change-quality-guide.md` documenting Bronze/Silver/Gold
> quality tiers for OpenSpec changes.

## Strategy

**Documentation-only change**. No new code, no new tests, no enforcement
mechanism, no schema change. The guide is a reference that authors and
reviewers consult; nothing parses it at runtime.

This is intentionally **non-prescriptive**: the guide describes good
practice, it does not block proposals that fall short of Silver or Gold.
The only enforced layer is the Bronze tier, which is already implemented
by Plan B (`propose_quality_check.py`).

## Relation to ADR-0019

ADR-0019 (`docs/adr/ADR-0019-change-arch-alignment.md`) is the
**single source of truth** for the anti-pattern checklist (3 patterns:
`单阶段|单体架构|hard.?code`, `跳过.{0,5}(架构|arch|adr|ADR)`,
`不写测试|跳过测试|skip.{0,5}test`).

This change **references** ADR-0019 for anti-patterns and **does not
duplicate** the keyword list, severity table, or `STRICT_CHANGE_GATE`
mechanism. The guide points readers to ADR-0019 §"反模式关键词清单（v1）"
and §"严重级别矩阵" instead of restating them.

Rationale: dual maintenance of the keyword list would drift; ADR-0019
already has Oracle-reviewed v1 -> v2 evolution triggers (§"v1 -> v2 扩展触发条件").

## Relation to Plan B (`propose_quality_check.py`)

Plan B (`skills/propose/scripts/propose_quality_check.py`) implements
the **enforced** Bronze tier via 5 check functions. The guide documents
what Plan B enforces and points to it as the implementation. The
thresholds in the guide MUST match the constants in
`propose_quality_check.py` exactly:

| Check | Plan B constant | Threshold |
|-------|-----------------|-----------|
| Proposal length | `MIN_PROPOSAL_LENGTH` | 500 chars (after stripping skeleton markers) |
| ADR references | `_ADR_PATTERN` | `>=1` match of `ADR-\d{4}` |
| Scope sections | `check_scope_sections` | `In Scope` + (`Out of Scope` or `Out Scope`) |
| Tasks completeness | `MIN_TASKS_COUNT` | `>=2` unchecked `- [ ]` items |
| Roadmap alignment | `check_roadmap_alignment` | change name substring in `roadmap.md` |

If Plan B thresholds change, the guide's "阈值速查表" must be updated
in the same PR. The guide's table is the human-facing mirror of the
code constants; it is not a separate decision.

## Threshold alignment with Plan B

The guide's Bronze tier lists exactly the 5 checks Plan B enforces,
mapped 1:1 to the Plan B function names:

- `check_proposal_length()` -> proposal.md >= 500 chars
- `check_adr_references()` -> proposal.md references >= 1 ADR
- `check_scope_sections()` -> proposal.md has In Scope + Out of Scope
- `check_tasks_completeness()` -> tasks.md has >= 2 unchecked items
- `check_roadmap_alignment()` -> change name appears in roadmap.md

Silver and Gold tiers are **aspirational** and have no corresponding
Plan B checks. They describe additional quality dimensions (design.md
depth, GIVEN/WHEN/THEN scenarios, integration tests, deps analysis)
that authors should aim for but reviewers should not block on.

## What this change does NOT do

- **No new gate**: the guide is not wired into `gate.py` or any
  `STRICT_*` env var. Bronze enforcement already exists via
  `STRICT_PROPOSE_GATE=yes` (Plan B); Silver/Gold are guidance only.
- **No ADR duplication**: the anti-pattern keyword list lives in
  ADR-0019 and is not copied here.
- **No new tests**: documentation-only; the existing test suite
  (`tests/unit/test_propose_quality_check.py` from Plan B) already
  locks the Bronze thresholds.
- **No propose.md / guide-plan.md edits**: the task brief scopes this
  to `docs/change-quality-guide.md` + an `AGENTS.md` reference only.

## Files touched

| File | Action | Notes |
|------|--------|-------|
| `docs/change-quality-guide.md` | Create | The guide itself |
| `AGENTS.md` | Edit | Add reference under "关键目录" docs section |
| `openspec/changes/add-change-quality-guide/design.md` | Create | This file |
| `openspec/changes/add-change-quality-guide/tasks.md` | Create | 3-task checklist |

## Verification

1. `python3 -m pytest tests/unit/ -q --tb=short` passes (no regressions;
   this change adds no Python, so the suite is unchanged).
2. `docs/change-quality-guide.md` exists and references ADR-0019 by name.
3. The Bronze tier table in the guide lists exactly the 5 Plan B
   function names with matching thresholds.
4. `AGENTS.md` "关键目录" section mentions `docs/change-quality-guide.md`.
