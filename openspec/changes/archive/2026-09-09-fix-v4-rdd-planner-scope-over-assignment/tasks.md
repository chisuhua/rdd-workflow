# fix-v4-rdd-planner-scope-over-assignment Tasks

Per Oracle architectural review `ses_f7a9e01dbffe2Lqu8jYjg4YvL2` (Verdict B). Implemented directly without rdd-builder 6-phase pipeline per user instruction (2026-09-09).

## Phase B — Implementation (load-bearing, must precede Phase A)

- [x] **Task 1: Restore `generate_full_proposal.py` from git history (B1)**
  - Restored `skills/rdd-builder/scripts/generate_full_proposal.py` from commit `6587b98` (pre-`1095cec` Wave 3 removal)
  - Extended section mapping to accept both 中文 (legacy) and English (current) headings
  - Added: References section passthrough + 优先级 metadata + Impact/Scope fallback
  - Test: `tests/unit/test_generate_full_proposal.py` (12 unit tests, all PASS)

- [x] **Task 2: Wire `phase0_approval.sh` approve branch (B1)**
  - Replaces D3 placeholder stub with `generate_full_proposal.py` invocation
  - Before: proposal.md stays as skeleton, D3 spec-delta writes fake Requirement
  - After: proposal.md populated from .rddf/improvements/<name>.md 5-段 content
  - Test: `tests/integration/test_phase0_approval_pipeline.bats` (1 e2e, PASS)

- [x] **Task 3: Delete broken `rdd-arch/scripts/approve_proposal.sh` shim (B2)**
  - Shim was pointing to deleted `guide-design/scripts/approve_proposal.sh` (Wave 3 hard removal)
  - Grep confirms no .sh/.py/.md callers outside the proposal docs
  - Test: `tests/integration/test_rdd_arch_approve_proposal_shim.bats` (skip-ok when deleted)

## Phase B — Cleanup

- [x] **Task 4: Rename `proposals_authored` → `proposals_ready` (B3 + A3)**
  - `_lib/schemas/planner_handoff_schema.json` v1.1: field + description
  - `_lib/planner_handoff.py`: param + env-var `PROPOSALS_READY`; added `awaiting_builder` field
  - `skills/rdd-planner/scripts/planner_stage_{entry,exit}.sh`: derive from planner-state `active_projects` (not grep from roadmap list)
  - Tests: `tests/unit/test_planner_handoff_schema_v1_rename.py` (4 tests, PASS) + `tests/unit/test_planner_handoff.py` (9 tests, sed-renamed, PASS)

## Phase A — Documentation patches (must land after Phase B; per Oracle order)

- [x] **Task 5: Update spec §3.2 row 165 + 166 + §3.4 Phase 0 input (A1, A2, A4)**
  - Row 165 (rdd-planner): remove `proposal.md (authoring only)` from owns; remove `proposal.md content` from Writes; HIL → "proposal lifecycle review / sprint governance"
  - Row 166 (rdd-builder): add `proposal.md (authoring via P0 approve, per ADR-0025)` to owns
  - §3.4 Phase 0 input: "from rdd-planner" → "authored at P0 approve per ADR-0025 D1/D2"

- [x] **Task 6: Rewrite spec §9 demo (A5)**
  - Replace `rddf planner new/brainstorm/accept` scaffold tasks.md (contradictory with §3.4)
  - New flow: `rddf planner attach` → `rdd-builder phase0 approve` (generates proposal.md via Task 1+2) → P1 writes tasks.md

- [x] **Task 7: Update rdd-planner SKILL.md role.owns (A6)**
  - Remove `openspec/changes/<name>/proposal.md (authoring only)` from owns (line 14 + 41)
  - Add `openspec/changes/<name>/proposal.md` to not_owns (line 45-50)
  - Description: "proposal authoring orchestrator" → "sprint proposal orchestrator"

- [x] **Task 8: Update rdd-builder SKILL.md role.owns/not_owns (A7)**
  - Add `proposal.md (authoring via P0 approve, per ADR-0025)` to owns (lines 20-25)
  - Remove `proposal.md (authoring)` from not_owns (line 28)

- [x] **Task 9: ADR-0025 evolution note (A8)**
  - Added Evolution section: v4 per ADR-0043 (design merged into rdd-builder P0); D1-D4 continue; generate_full_proposal.py restored per B1

- [x] **Task 10: ADR-0038 amendment (A9)**
  - Added AMENDMENT note: "NOT a sixth phase" clause superseded by ADR-0043 dual identity (sequential stage + cross-cutting orchestrator)
  - Out-of-scope clarification: rdd-planner does NOT author proposal.md

## Phase B — Optional

- [x] **Task 11: planner-state schema v1.1 `recommended_route` advisory (B4)**
  - Added `recommended_route: simple|complex|unknown` enum field to `_lib/schemas/planner_state_schema.json`
  - **Planner handoff schema UNTOUCHED** (rdd-quick never reads it; advisory only for user discovery)

## Phase A — Regression

- [x] **Task 12: Full regression gate (AC-14 + AC-15)**
  - 34 tests pass (12 generate_full_proposal + 9 planner_handoff + 8 doc_alignment + 5 schema_rename)
  - `bash skills/rdd-doctor/scripts/doctor.sh --quiet` → CRITICAL: 6 (no new findings, baseline preserved)
  - 7 pre-existing pytest failures verified NOT introduced by this change (git stash comparison)
    - 5× `test_planner_feedback_id_uniqueness.py` (date-sensitive fixtures)
    - 1× `test_cli_all_subcommands.py` (filled_at removed in earlier refactor)
    - 1× `test_adr_index_gate.py` (ADR-0001 duplicate baseline)

## Administrative

- [x] **Task A: Register in proposal-suggestions.md**
- [x] **Task B: Clean D3 stub at `openspec/specs/fix-doc-drift-followup-3/spec.md`**
- [x] **Task C: 9 atomic commits (6dc27ef..670626e)**
- [x] **Task D: Archive via openspec archive** (per user instruction: skip rdd-builder pipeline)

## Status

**Implementation complete.** All 12 plan Tasks + 4 administrative Tasks finished. Change ready for `openspec archive` (Task D).
