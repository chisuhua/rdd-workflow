# c-layer-4-skills Specification

## Purpose
TBD - created by archiving change add-e2e-test-plan-phase3. Update Purpose after archive.
## Requirements
### Requirement: c-layer-4-skills

The rdd-workflow repository SHALL provide C-layer (agent simulation) test coverage for all 5 user-facing skills, beyond the rdd-quick pilot (Plan 2):
- rdd-builder (12 scenarios B-E1..B-E12): covers P0-P3 6-phase state machine + verifier retry loop + cross-skill isolation
- rdd-verifier (8 scenarios V-E1..V-E8): covers AC extraction / 6-field verdict / pass / fail-gap / fail-drift / partial / 3-retry limit / credential-missing skip
- rdd-arch (8 scenarios A-E1..A-E8): covers setup-discovery / ADR-creation / gap-analysis / roadmap / arch-done-gate / 0-ADR block / handoff-stale / cross-skill isolation
- rdd-planner (8 scenarios P-E1..P-E8): covers stage-entry / intake / propose / brainstorm / approve-D3 / reject / horizontal-commands / stage-exit

#### Scenario: rdd-builder C-layer covers all 6 phase scripts

- **WHEN** `tests/e2e/agent/test_rdd_builder_e2e.bats` runs in mock mode
- **THEN** all 12 scenarios pass (P0 happy / P0 reject / P1 plan / P1.5 deps-lightweight / P1.5 deps-worktree / P2 lightweight / P2 worktree / P2.5 review / P3 archive / P3 0-commits block / P3→P1 retry / cross-skill isolation)

#### Scenario: rdd-verifier C-layer covers verdict classification routing

- **WHEN** `tests/e2e/agent/test_rdd_verifier_e2e.bats` runs in mock mode
- **THEN** all 8 scenarios pass including 2-class failure routing (implementation_gap → P2, proposal_drift → P1) and 3-retry escalation

#### Scenario: rdd-arch C-layer covers discovery + arch-done gate

- **WHEN** `tests/e2e/agent/test_rdd_arch_e2e.bats` runs in mock mode
- **THEN** all 8 scenarios pass including 0-ADR gate blocking (`至少需要 1 个 ADR` stderr)

#### Scenario: rdd-planner C-layer covers D3 spec-delta on approve

- **WHEN** `tests/e2e/agent/test_rdd_planner_e2e.bats` runs in mock mode
- **THEN** all 8 scenarios pass including approve creating both `openspec/changes/<n>/proposal.md` AND `openspec/changes/<n>/specs/<n>/spec.md` (D3 spec-delta)

