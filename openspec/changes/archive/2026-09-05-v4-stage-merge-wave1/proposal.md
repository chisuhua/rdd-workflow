# v4 Stage Merge Wave 1

## Why

Stage 1 of the v4 architecture (per spec `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md`).

This Wave delivers:
- **rdd-arch slim**: remove `_check_roadmap_defined` + 3 roadmap fields from `.arch-handoff.json` (per spec §6.2 batch 2).
- **rdd-planner stage promotion**: wrap existing `_lib/planner_*.py` with `skills/rdd-planner/SKILL.md` + `planner_handoff.py` schema v1 (per spec §3.3).
- **rdd-builder NEW**: 6-phase internal state machine (P0/P1/P1.5/P2/P2.5/P3) with verifier retry loop, per-change handoff layout, feedback single-writer contract (per spec §3.4).
- **Cross-stage feedback routing**: `rdd-builder → rdd-arch` via `_lib/builder_feedback_router.py` (per spec §3.5 batch 4).
- **Install surface**: 4-stage skill symlinks, INSTALL.md update, global install test extension (per spec §4.1 + Oracle H5).
- **rddf-session stage mapping**: 4 canonical stages recognized, legacy intent shim deferred to Wave 2 (per ADR-0042 §6 pattern).

87 spec AC items must be `[x]` for Wave 1 ship gate.

## What changes

**New files (production)**:
- `skills/rdd-planner/SKILL.md`
- `skills/rdd-planner/scripts/{planner_stage_entry,planner_stage_exit}.sh`
- `skills/rdd-builder/SKILL.md`
- `skills/rdd-builder/scripts/{phase0_approval,phase1_plan,phase1_5_deps,phase2_execute,phase2_5_review,phase3_archive}.sh` (6 phase scripts)
- `_lib/planner_handoff.py`
- `_lib/builder_handoff.py`
- `_lib/builder_deps.py`
- `_lib/builder_retry.py`
- `_lib/builder_feedback_router.py`
- `_lib/cli/builder_cmd.py`
- `_lib/schemas/{planner_handoff,builder_handoff,builder_retry}_schema.json`

**Modified files**:
- `skills/rdd-arch/scripts/write_arch_handoff.py` (stop emitting roadmap fields)
- `_lib/gate.py` (remove `_check_roadmap_defined` + registration)
- `_lib/schemas/arch_handoff_schema.json` (add v3 to enum)
- `_lib/state_reader.py` (tolerate removed fields)
- `install.sh` (symlink rdd-planner + rdd-builder)
- `skills/INSTALL.md` (document 4-stage install list)
- `rddf-session` schema (add stage_arch/planner/builder/verifier fields)

**New tests (≥69 unit + ≥21 bats per spec §7)**:
- `tests/unit/test_planner_handoff.py`, `test_builder_handoff.py`, `test_builder_deps.py`, `test_builder_retry.py`, `test_builder_feedback_router.py`, `test_builder_phase*.py`, `test_builder_run_pause.py`, `test_builder_cli.py`
- `tests/integration/test_rdd_builder_*.bats`, `test_rdd_planner_*.bats`, `test_cross_stage_feedback.bats`

**Modified tests**:
- `tests/integration/test_arch_discovery_contract.bats` (remove _check_roadmap_defined references)
- `tests/unit/test_write_arch_handoff.py` (drop ~13 `discovered_roadmap_path` assertions)
- `tests/unit/test_arch_handoff_schema_v2.py` (add v3 contract tests)
- `tests/integration/test_global_install_external_project.bats` (4-stage symlink completeness)

**Documentation**:
- `docs/adr/ADR-0043-rdd-workflow-v4-stage-merge.md` (decision record)

## Impact

- **Wave 2**: deprecation banners + shim (separate change).
- **Wave 3**: hard removal of `guide-design`/`guide-plan`/`guide-ship` + `_lib/cli/{design,plan,ship}_cmd.py` (separate change).

Wave 1 is fully additive; no existing skills are modified. New skills are added; old skills remain active until Wave 2/3.

**Backward compatibility**:
- `.arch-handoff.json` v1/v2 still parse via `additionalProperties: true` (per Oracle H1 finding).
- `.plan-handoff.json::execution_mode_decisions` legacy fallback in Phase 1.5 during Wave 1 (per Oracle C2).
- Legacy `rddf-session` intent names preserved literal in Wave 1; shim to `rdd-builder` deferred to Wave 2 (per Metis Q1 finding).
- `approve_proposal.sh::generate_spec_delta` (ADR-0025 D3) decoupled from `guide-design` script via inline Python helper (per Metis Q1).