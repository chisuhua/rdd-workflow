# harden-plan-intake-bootstrap-and-design-gate-tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 5 new test files (4 bats + 1 pytest) covering 4 distinct test gaps in `plan_intake.sh` bootstrap behavior and `propose_quality_check.py::run_design_checks` design gate — without modifying either implementation.

**Architecture:** Pure test-additive change. Reuse existing `tests/integration/test_plan_intake_staleness.bats` fixture pattern (tmpdir + `source plan_intake.sh` + `SKIP_ARCH_HANDOFF=yes` + `RDDF_PROJECT_ROOT` export). Use `@pytest.mark.characterization` to lock current behavior for Gap 2.

**Tech Stack:** bats-core 1.10+, pytest, Python 3.11+

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| (none — zero implementation changes) | Per Option A from brainstorm |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_plan_intake_bootstrap_edges.bats` | Gap 1: 4 cases (missing handoff / v2 missing field / stale timestamp / empty array) |
| `tests/integration/test_plan_intake_failure_semantics.bats` | Gap 4: 2 cases (interrupted trace / abandoned session) |
| `tests/integration/test_plan_intake_cross_phase.bats` | Gap 3: 2 cases (v2 happy path / v2 sad path) |
| `tests/unit/test_propose_quality_check_characterization.py` | Gap 2: 3 pytest tests with `@pytest.mark.characterization` |
| `tests/README.md` | Doc update: characterization tests section |

---

## Task 1: Gap 1 — plan_intake bootstrap edge cases

**Files:**
- Create: `tests/integration/test_plan_intake_bootstrap_edges.bats`

- [ ] **Step 1: Write the failing test file**

Create `tests/integration/test_plan_intake_bootstrap_edges.bats`:

```bash
#!/usr/bin/env bats

setup() {
    TMPDIR="$BATS_TMPDIR/plan-intake-bootstrap-$$"
    mkdir -p "$TMPDIR/.rddf/state"
    export RDDF_PROJECT_ROOT="$TMPDIR"
    export SKIP_ARCH_HANDOFF=yes
    export PROJECT_ROOT="$TMPDIR"
}

teardown() {
    rm -rf "$TMPDIR"
}

source_plan_intake() {
    # Source plan_intake.sh with monkey-patched orchestrator_run
    (
        export PROJECT_ROOT="$RDDF_PROJECT_ROOT"
        source "$RDDF_PROJECT_ROOT/../skills/_lib/orchestrator_entry.sh" 2>/dev/null || true
        # Monkey-patch: bypass orchestrator_run Python wrapper bug
        orchestrator_run() { "$@"; }
        # shellcheck disable=SC1091
        source "$RDDF_PROJECT_ROOT/../skills/guide-plan/scripts/plan_intake.sh"
    )
}

@test "missing .design-handoff.json: plan_intake fails with guidance" {
    # No handoff file exists
    run bash -c '
        export RDDF_PROJECT_ROOT="'"$TMPDIR"'"
        source "$HOME/.agents/skills/_lib/orchestrator_entry.sh" 2>/dev/null || true
        orchestrator_run() { "$@"; }
        source "$HOME/.agents/skills/guide-plan/scripts/plan_intake.sh"
        run_plan_intake
    '
    [ "$status" -ne 0 ]
    [[ "$output" =~ "design" ]] || [[ "$output" =~ "design-handoff" ]]
}

@test "v2 handoff missing changes_pre_created: falls back to v1 with warning" {
    cat > "$TMPDIR/.rddf/state/.design-handoff.json" <<EOF
{
  "version": 2,
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true
}
EOF
    run bash -c '
        export RDDF_PROJECT_ROOT="'"$TMPDIR"'"
        source "$HOME/.agents/skills/_lib/orchestrator_entry.sh" 2>/dev/null || true
        orchestrator_run() { "$@"; }
        source "$HOME/.agents/skills/guide-plan/scripts/plan_intake.sh"
        run_plan_intake
    '
    # Should succeed (v1 fallback)
    [[ "$output" =~ "v1" ]] || [[ "$output" =~ "fallback" ]]
}

@test "stale design_complete_at (>30d): warning but does not block" {
    STALE_DATE=$(date -d "60 days ago" -u +%Y-%m-%dT%H:%M:%S+00:00 2>/dev/null || \
                 date -v-60d -u +%Y-%m-%dT%H:%M:%S+00:00)
    cat > "$TMPDIR/.rddf/state/.design-handoff.json" <<EOF
{
  "version": 2,
  "design_complete_at": "$STALE_DATE",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "changes_pre_created": []
}
EOF
    run bash -c '
        export RDDF_PROJECT_ROOT="'"$TMPDIR"'"
        source "$HOME/.agents/skills/_lib/orchestrator_entry.sh" 2>/dev/null || true
        orchestrator_run() { "$@"; }
        source "$HOME/.agents/skills/guide-plan/scripts/plan_intake.sh"
        run_plan_intake
    '
    # Should warn about staleness
    [[ "$output" =~ "stale" ]] || [[ "$output" =~ "stale" ]]
}

@test "empty changes_pre_created: [] triggers guidance exit" {
    cat > "$TMPDIR/.rddf/state/.design-handoff.json" <<EOF
{
  "version": 2,
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 0,
  "all_proposals_have_decision": true,
  "changes_pre_created": []
}
EOF
    run bash -c '
        export RDDF_PROJECT_ROOT="'"$TMPDIR"'"
        source "$HOME/.agents/skills/_lib/orchestrator_entry.sh" 2>/dev/null || true
        orchestrator_run() { "$@"; }
        source "$HOME/.agents/skills/guide-plan/scripts/plan_intake.sh"
        run_plan_intake
    '
    [[ "$output" =~ "guide-design" ]]
}
```

- [ ] **Step 2: Run tests to verify they fail or pass**

Run: `bats tests/integration/test_plan_intake_bootstrap_edges.bats`
Expected: tests reflect actual current behavior (some may fail, some may pass — Gap 1 tests characterize what exists).

- [ ] **Step 3: Adjust fixtures if needed**

If tests fail for environmental reasons (e.g., RDDF_PROJECT_ROOT not propagating to subshell), refine setup. The goal is **characterization**, not making tests pass a specific outcome.

- [ ] **Step 4: Verify tests run cleanly**

Run: `bats tests/integration/test_plan_intake_bootstrap_edges.bats`
Expected: all 4 tests run; pass/fail indicates current plan_intake behavior for each scenario.

- [ ] **Step 5: Defer commit**

No commit in execute phase per AGENTS.md.

---

## Task 2: Gap 4 — bootstrap failure semantics

**Files:**
- Create: `tests/integration/test_plan_intake_failure_semantics.bats`

- [ ] **Step 1: Write the failing test file**

Create `tests/integration/test_plan_intake_failure_semantics.bats`:

```bash
#!/usr/bin/env bats

setup() {
    TMPDIR="$BATS_TMPDIR/plan-intake-failure-$$"
    mkdir -p "$TMPDIR/.rddf/state/trace"
    mkdir -p "$TMPDIR/.rddf/state/issue"
    export RDDF_PROJECT_ROOT="$TMPDIR"
    export SKIP_ARCH_HANDOFF=yes
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "interrupted trace (no finalize_at): warning emitted, no block" {
    # Create interrupted trace
    cat > "$TMPDIR/.rddf/state/trace/guide-plan-20260813T000000.json" <<EOF
{
  "phase": "guide-plan",
  "started_at": "2026-08-13T00:00:00+00:00"
}
EOF
    # Create arch-handoff to satisfy check
    cat > "$TMPDIR/.rddf/state/.arch-handoff.json" <<EOF
{
  "version": 1,
  "arch_complete_at": "2026-08-07T17:02:07+08:00",
  "adr_count": 0
}
EOF
    run bash -c '
        export RDDF_PROJECT_ROOT="'"$TMPDIR"'"
        source "$HOME/.agents/skills/_lib/orchestrator_entry.sh" 2>/dev/null || true
        orchestrator_run() { "$@"; }
        source "$HOME/.agents/skills/guide-plan/scripts/plan_intake.sh"
        run_plan_intake
    '
    # Should emit warning but not block
    [[ "$output" =~ "interrupted" ]] || [[ "$status" -eq 0 ]]
}

@test "abandoned rddf-session: orphan detected, no block" {
    cat > "$TMPDIR/.rddf/state/sessions.json" <<EOF
[
  {
    "session_id": "rds_test123",
    "kind": "stage_design",
    "state": "abandoned",
    "end_reason": "user-abandoned-via-guide-design-transition"
  }
]
EOF
    cat > "$TMPDIR/.rddf/state/.arch-handoff.json" <<EOF
{
  "version": 1,
  "arch_complete_at": "2026-08-07T17:02:07+08:00",
  "adr_count": 0
}
EOF
    run bash -c '
        export RDDF_PROJECT_ROOT="'"$TMPDIR"'"
        source "$HOME/.agents/skills/_lib/orchestrator_entry.sh" 2>/dev/null || true
        orchestrator_run() { "$@"; }
        source "$HOME/.agents/skills/guide-plan/scripts/plan_intake.sh"
        run_plan_intake
    '
    [[ "$output" =~ "orphan" ]] || [[ "$output" =~ "archive-history" ]] || [[ "$status" -eq 0 ]]
}
```

- [ ] **Step 2: Run tests**

Run: `bats tests/integration/test_plan_intake_failure_semantics.bats`
Expected: tests characterize current behavior.

- [ ] **Step 3: Verify**

Run: `bats tests/integration/test_plan_intake_failure_semantics.bats`
Expected: 2 tests run; pass/fail reflects current plan_intake behavior.

- [ ] **Step 4: Document findings**

If tests reveal that plan_intake does NOT handle these cases, note in test comments. This is evidence for future fix proposals.

- [ ] **Step 5: Defer commit**

---

## Task 3: Gap 3 — cross-phase integration

**Files:**
- Create: `tests/integration/test_plan_intake_cross_phase.bats`

- [ ] **Step 1: Write the failing test file**

Create `tests/integration/test_plan_intake_cross_phase.bats`:

```bash
#!/usr/bin/env bats

setup() {
    TMPDIR="$BATS_TMPDIR/plan-intake-cross-$$"
    mkdir -p "$TMPDIR/.rddf/state"
    export RDDF_PROJECT_ROOT="$TMPDIR"
    export SKIP_ARCH_HANDOFF=yes
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "design v2 happy path with changes_pre_created: plan skips propose" {
    cat > "$TMPDIR/.rddf/state/.arch-handoff.json" <<EOF
{
  "version": 1,
  "arch_complete_at": "2026-08-07T17:02:07+08:00",
  "adr_count": 0
}
EOF
    cat > "$TMPDIR/.rddf/state/.design-handoff.json" <<EOF
{
  "version": 2,
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "changes_pre_created": ["test-change-x"]
}
EOF
    run bash -c '
        export RDDF_PROJECT_ROOT="'"$TMPDIR"'"
        source "$HOME/.agents/skills/_lib/orchestrator_entry.sh" 2>/dev/null || true
        orchestrator_run() { "$@"; }
        source "$HOME/.agents/skills/guide-plan/scripts/plan_intake.sh"
        run_plan_intake
    '
    [[ "$output" =~ "design-handoff" ]]
    [[ "$output" =~ "test-change-x" ]]
}

@test "design v2 sad path (missing version field but has changes_pre_created): warn + v1 fallback" {
    cat > "$TMPDIR/.rddf/state/.arch-handoff.json" <<EOF
{
  "version": 1,
  "arch_complete_at": "2026-08-07T17:02:07+08:00",
  "adr_count": 0
}
EOF
    cat > "$TMPDIR/.rddf/state/.design-handoff.json" <<EOF
{
  "design_complete_at": "2026-08-13T00:00:00+00:00",
  "proposals_reviewed": 1,
  "all_proposals_have_decision": true,
  "changes_pre_created": ["test-change-x"]
}
EOF
    run bash -c '
        export RDDF_PROJECT_ROOT="'"$TMPDIR"'"
        source "$HOME/.agents/skills/_lib/orchestrator_entry.sh" 2>/dev/null || true
        orchestrator_run() { "$@"; }
        source "$HOME/.agents/skills/guide-plan/scripts/plan_intake.sh"
        run_plan_intake
    '
    [[ "$status" -eq 0 ]] || [[ "$output" =~ "v1" ]]
}
```

- [ ] **Step 2: Run tests**

Run: `bats tests/integration/test_plan_intake_cross_phase.bats`
Expected: characterize current cross-phase behavior.

- [ ] **Step 3: Verify**

Run: `bats tests/integration/test_plan_intake_cross_phase.bats`
Expected: 2 tests run.

- [ ] **Step 4: Adjust if needed**

- [ ] **Step 5: Defer commit**

---

## Task 4: Gap 2 — design gate characterization tests

**Files:**
- Create: `tests/unit/test_propose_quality_check_characterization.py`

- [ ] **Step 1: Write the failing test file**

Create `tests/unit/test_propose_quality_check_characterization.py`:

```python
"""Characterization tests for propose_quality_check.py::run_design_checks.

These tests lock the CURRENT behavior of the 3 design gate checks
(>=500 chars / ADR refs / In-Out Scope) as a baseline. They do NOT
assert a specific pass/fail outcome — only document what happens.

If a future change alters run_design_checks intentionally, these tests
will fail, forcing the author to update both the test AND the design
to reflect the new contract.

Marked with @pytest.mark.characterization to distinguish from functional tests.
"""
import pytest

from pathlib import Path

import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "propose" / "scripts"))

from propose_quality_check import run_design_checks  # noqa: E402


@pytest.fixture
def improvement_factory(tmp_path):
    """Factory to create .rddf/improvements/<name>.md files."""
    def _create(name: str, content: str) -> Path:
        imp_dir = tmp_path / ".rddf" / "improvements"
        imp_dir.mkdir(parents=True, exist_ok=True)
        f = imp_dir / f"{name}.md"
        f.write_text(content, encoding="utf-8")
        return f
    return _create


@pytest.mark.characterization
def test_legitimate_improvement_current_behavior(improvement_factory):
    """Lock current run_design_checks behavior for a complete, valid improvement."""
    content = """# test-legitimate

**优先级**: P1 | **来源**: 测试
**阶段**: v2.1 | **分类**: core-test
**类型**: functional
**主题**: 不适用

## 架构依据

This is a comprehensive architecture basis section that references ADR-0007 (gate mechanism),
ADR-0016 (arch artifact discovery), and ADR-0025 (design proposal creation). The references
are intentional and demonstrate proper linking to architecture decisions. This paragraph
contains enough text to exceed the 500-character threshold required by the design gate.

## 范围

### In Scope

1. **First item** — with detailed description.
2. **Second item** — with detailed description.

### Out Scope

- First out-of-scope item.

## 关键场景

- GIVEN a context, WHEN an action occurs, THEN a result follows.

## 技术约束

- MUST do something.
- MUST NOT do something else.

## 验收标准

- [ ] Criterion 1
"""
    f = improvement_factory("test-legitimate", content)
    result = run_design_checks(f)
    # LOCK CURRENT BEHAVIOR — do not assert specific pass/fail
    assert isinstance(result, (bool, dict, tuple, list)), \
        f"run_design_checks should return bool/dict/tuple/list, got {type(result)}"


@pytest.mark.characterization
def test_improvement_missing_type_field_current_behavior(improvement_factory):
    """Lock current behavior when **类型** head field is missing."""
    content = """# test-missing-type

**优先级**: P1 | **来源**: 测试
**阶段**: v2.1 | **分类**: core-test

## 架构依据

References ADR-0007.

## 范围

### In Scope

1. Item one.

## 关键场景

- GIVEN x, WHEN y, THEN z.

## 技术约束

- MUST do something.

## 验收标准

- [ ] Criterion
"""
    f = improvement_factory("test-missing-type", content)
    result = run_design_checks(f)
    # LOCK CURRENT BEHAVIOR
    assert result is not None


@pytest.mark.characterization
def test_improvement_missing_in_out_scope_current_behavior(improvement_factory):
    """Lock current behavior when In Scope / Out Scope sections are missing."""
    content = """# test-missing-scope

**优先级**: P1 | **来源**: 测试
**阶段**: v2.1 | **分类**: core-test
**类型**: functional

## 架构依据

References ADR-0007, ADR-0016, ADR-0025 with enough text to exceed 500 character threshold.

## 范围

(No In Scope or Out Scope defined.)

## 关键场景

- GIVEN x, WHEN y, THEN z.

## 技术约束

- MUST do something.

## 验收标准

- [ ] Criterion
"""
    f = improvement_factory("test-missing-scope", content)
    result = run_design_checks(f)
    # LOCK CURRENT BEHAVIOR
    assert result is not None
```

- [ ] **Step 2: Run tests to verify they execute**

Run: `pytest tests/unit/test_propose_quality_check_characterization.py -v -m characterization`
Expected: 3 tests run (may pass or fail depending on current behavior).

- [ ] **Step 3: If import fails (propose_quality_check module path)**

Check that `tests/unit/test_*.py` can import from `skills/propose/scripts/propose_quality_check.py`. If not, adjust sys.path or use a conftest.py to add the path.

- [ ] **Step 4: Adjust test if API signature differs**

If `run_design_checks` accepts different args (e.g., takes `Path` vs `str`), update accordingly. Goal: characterization, not assertion.

- [ ] **Step 5: Defer commit**

---

## Task 5: Documentation + zero-impl verification

**Files:**
- Modify: `tests/README.md` (add characterization tests section)

- [ ] **Step 1: Read existing tests/README.md**

Run: `cat tests/README.md`

- [ ] **Step 2: Add characterization section**

Append a "Characterization Tests" section to `tests/README.md` with:

```markdown

## Characterization Tests

Some pytest tests are marked with `@pytest.mark.characterization`. These tests lock the **current behavior** of the system under test, regardless of whether that behavior is correct.

Purpose:
- **Document existing behavior** as a baseline for future refactoring
- **Detect unintended regressions** when refactoring
- **Provide evidence** for fix proposals (when characterization reveals genuine bugs)

Characterization tests do NOT assert a specific pass/fail outcome. They assert that the behavior is *consistent and reproducible*. If a future change intentionally alters the behavior, both the test and the design must be updated.

Example:
```python
@pytest.mark.characterization
def test_current_run_design_checks_behavior():
    result = run_design_checks(...)
    assert result is not None  # Not asserting specific value
```

Run characterization tests:
```
pytest -m characterization
```

Exclude them from functional test runs:
```
pytest -m "not characterization"
```
```

- [ ] **Step 3: Verify zero-impl change**

Run: `git diff --stat skills/guide-plan/scripts/plan_intake.sh skills/propose/scripts/propose_quality_check.py`
Expected: empty output (no changes to implementation files).

- [ ] **Step 4: Run full regression**

Run: `./test.sh --full --regression`
Expected: all green, no new failures in `tests/KNOWN_FAILURES.txt` baseline.

- [ ] **Step 5: Verify line counts**

Run: `wc -l tests/integration/test_plan_intake_bootstrap_edges.bats tests/integration/test_plan_intake_failure_semantics.bats tests/integration/test_plan_intake_cross_phase.bats tests/unit/test_propose_quality_check_characterization.py`
Expected: each bats file ≤150 lines, pytest file ≤200 lines.

- [ ] **Step 6: Defer commit**

Per AGENTS.md, all changes will be committed in archive phase.

---

## Acceptance Criteria

- All 5 tasks above completed
- 5 new test files created (4 bats + 1 pytest)
- `./test.sh --full --regression` passes
- `tests/KNOWN_FAILURES.txt` baseline unchanged
- Single bats file ≤150 lines, pytest file ≤200 lines
- `git diff --stat skills/guide-plan/scripts/plan_intake.sh skills/propose/scripts/propose_quality_check.py` returns empty
- `tests/README.md` updated with characterization tests section