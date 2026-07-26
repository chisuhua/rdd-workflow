## Why

`propose_quality_check.py` (5 structural checks) has been a dead asset since it was introduced by the prior change `add-propose-output-validation`. The unit-test suite (`tests/unit/test_propose_quality_check.py`) covers the 5 checks, but no caller in the propose flow or in any gate invokes it. As a result, low-quality proposals enter the change pipeline with no automatic signal to the author or reviewer.

Oracle code review 2026-07-21 identified this as a P0 issue (ADR-0019 §strict pattern, ADR-0007 §warning-does-not-block): a 226-line module with 5 meaningful structural checks exists but is never wired into any workflow entry point. The `propose_quality_hook.py` and `propose_quality_hook.sh` modules already exist as part of the implementation, as does the `propose_quality_checks` Check registration in `gate.py` plan_done.

## In Scope

- Wire the existing `propose_quality_check.py` into propose.md Phase 4 artifact creation flow (skeleton and full branches)
- Wire the same check into `gate.py` plan_done as a warning-level Check with `strict_wrap(env_var="STRICT_PROPOSE_GATE")`
- Persist check results to `.rddf/state/propose-quality.json` as a machine-readable view file
- Unit tests for the hook module (`tests/unit/test_propose_quality_hook.py`)
- Gate tests for the new Check (`tests/unit/test_gate.py`)
- Integration tests (`tests/integration/test_propose_quality_hook.bats`)

## Out of Scope

- Modifying the 5 check functions in `propose_quality_check.py` (untouched)
- Adding new check categories
- Content review (see separate `add-propose-content-review` improvement)
- Wiring into `ship_done` gate (only `plan_done`, per ADR-0007 §phase-gates)

## Capabilities

### New Capabilities
- `propose-quality-autohook`: Automatic quality check of proposal artifacts after creation in Phase 4, with results persisted to `.rddf/state/propose-quality.json`

### Modified Capabilities
- `propose.md Phase 4`: Now automatically invokes quality checks after artifact creation (non-blocking by default)
- `gate.py plan_done`: Now includes `propose_quality_checks` Check (warning-level; `STRICT_PROPOSE_GATE=yes` upgrades to error)

## Impact

- **New code**: ~80 lines (hook.py) + ~15 lines (hook.sh) + ~80 lines (unit tests) + ~70 lines (integration tests) + ~40 lines (gate.py) = ~285 lines
- **Dependencies**: None — reuses existing `propose_quality_check.py` and `gate.py` infrastructure
- **Compatibility**: 100% backward compatible — default mode is warning-only, no flow blocked
- **Risk**: Low — additive wiring; the checker module itself is untouched
- **Source**: Oracle 代码审查 2026-07-21, improvement `propose-quality-autohook`
- **References**: ADR-0007 §warning-does-not-block, ADR-0019 §strict pattern