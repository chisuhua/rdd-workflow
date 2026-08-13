# Design: harden-plan-intake-bootstrap-and-design-gate-tests

## Context

ADR-0016 and ADR-0025 introduced the `.arch-handoff.json` v1 schema (5 discovery fields + fallback chain) and `.design-handoff.json` v2 schema (`changes_pre_created` + `version: 2`). Both shipped with happy-path tests but lacked coverage for:

1. **Bootstrap edge cases**: Missing/stale handoffs, v1↔v2 schema mixing, empty `changes_pre_created`
2. **Failure semantics**: Trace interruption, rddf-session abandon during plan phase
3. **Cross-phase integration**: design-done → plan-intake handoff pass-through
4. **Design gate false positives**: `propose_quality_check.py::run_design_checks` 3 checks (≥500 chars / ADR refs / In-Out Scope) under `STRICT_DESIGN_GATE=yes` may have false positives not currently characterized

Current state has `.plan-handoff.json::current_change` pointing to an archived change while `openspec/changes/` is empty — a real-world instance of gap-1's "stale handoff" scenario.

## Decisions

### Test-only scope (Option A from brainstorm)

This proposal adds **tests only**. No implementation changes to `plan_intake.sh` or `propose_quality_check.py`. Rationale:
- Existing tests already use `test_plan_intake_staleness.bats` pattern (tmpdir + `source plan_intake.sh` + `SKIP_ARCH_HANDOFF=yes` + `RDDF_PROJECT_ROOT`)
- Refactoring (`plan_intake.sh` → `validate_design_handoff()` etc.) is out of scope; would require its own proposal
- Characterization tests document current behavior, providing baseline for future fix proposals

### Gap priority (per Oracle review)

| Priority | Gap | Test file | Cases |
|----------|-----|-----------|-------|
| 1 (entry gate) | plan_intake bootstrap edges | `test_plan_intake_bootstrap_edges.bats` | ≥4 |
| 2 | bootstrap failure semantics | `test_plan_intake_failure_semantics.bats` | ≥2 |
| 3 | cross-phase integration | `test_plan_intake_cross_phase.bats` | ≥2 |
| 4 (opt-in) | design gate false positives | `test_propose_quality_check_characterization.py` | ≥3 |

### Test fixture pattern

Reuse existing `tests/integration/test_plan_intake_staleness.bats` pattern:

```bash
setup() {
    TMPDIR="$BATS_TMPDIR/test-$$"
    mkdir -p "$TMPDIR/.rddf/state"
    export RDDF_PROJECT_ROOT="$TMPDIR"
    export SKIP_ARCH_HANDOFF=yes
}

teardown() {
    rm -rf "$TMPDIR"
}
```

For Gap 2 (design gate), use pytest with `@pytest.mark.characterization`:

```python
import pytest

@pytest.mark.characterization
def test_500_char_threshold_current_behavior(improvement_factory):
    # Document whatever current behavior is — no specific assertion
    ...
```

### What "characterization" means here

Tests that **lock the current behavior**, not enforce a specific outcome. If `run_design_checks` returns `False` for a given input today, the characterization test asserts `False`. If the behavior later changes intentionally, the test fails and forces the author to update both the test and the design.

This approach:
- Documents existing behavior (post-mortem clarity)
- Catches unintended regressions
- Provides evidence for future fix proposals (if characterization reveals genuine bugs)

### Schema version tolerance

`plan_intake.sh::check_design_handoff` accepts both v1 and v2 per ADR-0025 D3. Tests should:
- Validate v1 → v2 fallback path (missing `changes_pre_created` field)
- Validate v1 explicit `version: 1` is treated as v1
- Validate v2 with empty `changes_pre_created: []` is accepted but emits warning

### Empty changes folder + stale handoff

A specific test for the current real-world state (`.plan-handoff.json::current_change = "complete-third-party-replay-and-upstream-reporting"` is archived, but `openspec/changes/` is empty):

```bash
@test "stale plan-handoff referencing archived change with empty openspec/changes" {
    # Create stale plan-handoff pointing to archived change
    # Verify plan_intake emits warning but does not block
}
```

## Risks

| Risk | Mitigation |
|------|-----------|
| Tests pass on stale code without catching real bugs | Characterization tests are explicit; future fix proposals use them as evidence |
| Plan_intake.sh bug in production that tests don't cover | Gap 1-3 tests cover the most likely real-world scenarios |
| Test flakiness from PIPE / tmpdir races | Use isolated TMPDIR per test; no shared state |
| Bats test slowdown (10+ new tests) | Each test ≤5s; total ≤45s for new tests |

## Out-of-scope decisions

- **Refactoring `plan_intake.sh`**: deferred to separate proposal if tests reveal structural issues
- **Property-based testing**: rejected per `tests/README.md` "do not add mocking/coverage frameworks"
- **Fixing gate false positives**: deferred; characterization tests will document them for future fix
- **Backward compat for v0 design-handoff**: deprecated; tests focus on v1/v2 per ADR-0025 D3

## Migration

1. Add 4 test files in `tests/integration/` and 1 in `tests/unit/`
2. Verify all tests pass
3. Update `tests/README.md` with `characterization` marker docs
4. If characterization tests reveal real bugs, file separate `fix-propose-quality-check-false-positives.md` proposal