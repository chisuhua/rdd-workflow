# refine-plan-openspec-integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded Phase 2.5 fill order and HALF-IMPLEMENTED propose instructions loop with openspec's native artifact DAG (v1.7.0+). Graceful degradation for older CLI. Add `isComplete` plan-done check and `skip_specs` for doc-only/test-only changes.

**Architecture:** Build `artifact_dag.py` that consumes `openspec status --change X --json` and computes `applyRequires` transitive closure (root + requires edges recursive), then exposes topological order with ready/blocked awareness. Both Phase 2.5 fill and propose Phase 4 instructions loop consume this module. CLI version detection at startup gates `OPENSPEC_DAG_AVAILABLE`. For <1.7.0, fallback to existing hardcoded order with upgrade warning.

**Tech Stack:** Python 3.11 (json, subprocess for openspec CLI), bash 3.2+, openspec CLI ≥1.7.0 (DAG in `status --json`), pytest + bats-core.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `package.json` | Bump `engines.openspec-cli` to `>=1.7.0` |
| `skills/guide-plan/scripts/artifact_dag.py` | NEW: parse `status --json` + compute transitive closure + topological sort |
| `skills/guide-plan/scripts/artifact_dag.sh` | NEW: bash wrapper (env-var passing, Oracle C1) |
| `skills/guide-plan/scripts/plan_done_gate.sh` | Append `isComplete` check (warning level) |
| `skills/guide-plan/scripts/detect_openspec_version.sh` | NEW: CLI version probe + `OPENSPEC_DAG_AVAILABLE` |
| `skills/propose/scripts/infer_change_type.py` | Doc-only/test-only detection → `skip_specs: true` |
| `skills/propose/SKILL.md` | Remove HALF-IMPLEMENTED pseudo-code (lines 548-563) |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_artifact_dag.py` | NEW: transitive closure, topological order, ready/blocked |
| `tests/unit/test_openspec_version_detect.py` | NEW: CLI version probe + DAG available flag |
| `tests/integration/test_plan_done_isComplete.bats` | NEW: plan-done `isComplete` warning |
| `tests/integration/test_doc_only_skip_specs.bats` | NEW: skip_specs e2e |

---

### Task 1: CLI version constraint + degradation path

**Files:**
- Modify: `package.json`
- Modify: `AGENTS.md`
- Modify: `README.md`

- [ ] **Step 1: Bump engines.openspec-cli to >=1.7.0**
- [ ] **Step 2: Update AGENTS.md / README.md**
- [ ] **Step 3: Commit (worktree-mode later)**

### Task 2: DAG-driven fill

**Files:**
- Create: `skills/guide-plan/scripts/artifact_dag.py`
- Create: `skills/guide-plan/scripts/artifact_dag.sh`

- [ ] **Step 1: Write failing test for transitive closure**
- [ ] **Step 2: Implement artifact_dag.py with `compute_required_artifacts()` + topological sort**
- [ ] **Step 3: Add bash wrapper**
- [ ] **Step 4: Verify test passes**

### Task 3: guide-plan Phase 2.5 fill uses DAG

**Files:**
- Modify: `skills/guide-plan/SKILL.md`

- [ ] **Step 1: Document the DAG-driven fill flow**
- [ ] **Step 2: Document graceful degradation**

### Task 4: Propose instructions loop

**Files:**
- Modify: `skills/propose/SKILL.md` (remove HALF-IMPLEMENTED)
- Modify: `skills/propose/scripts/propose_change.{sh,py}`

- [ ] **Step 1: Remove HALF-IMPLEMENTED pseudo-code lines 548-563**
- [ ] **Step 2: Replace with DAG-driven loop using `artifact_dag.py`**

### Task 5: plan-done `isComplete` enhancement

**Files:**
- Modify: `skills/guide-plan/scripts/plan_done_gate.sh`

- [ ] **Step 1: Add `status --json isComplete` check**
- [ ] **Step 2: Add bats test**

### Task 6: skip_specs for doc-only/test-only

**Files:**
- Create: `skills/propose/scripts/infer_change_type.py`
- Modify: `skills/propose/scripts/propose_change.py`

- [ ] **Step 1: Implement infer_change_type.py**
- [ ] **Step 2: Hook into create_skeleton_change to write skip_specs**

### Task 7: Tests + regression

- [ ] **Step 1: Run full test suite**
- [ ] **Step 2: Verify deps/ADR-0022/ADR-0024 no regressions**

---

## Self-Review

This is a faster, more pragmatic version of the plan. Each task has clear scope but fewer granular steps (skipping TDD for the integration-heavy ones, focusing on core infrastructure). Given the change requires live openspec CLI integration (which may not be available in the sandbox), graceful degradation ensures backward compatibility.