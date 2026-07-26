## Context

`propose_quality_check.py` (in `skills/propose/scripts/`) implements 5 structural checks but was never wired into any workflow entry point since its introduction. The checker:

- Checks proposal length (≥500 chars, stripping skeleton boilerplate)
- Checks ADR references (≥1 ADR-\d{4} match)
- Checks scope sections (In Scope + Out of Scope)
- Checks roadmap alignment (change name appears in roadmap.md)
- Checks tasks completeness (≥2 unchecked items)

The propose.md Phase 4 already invokes `propose_quality_hook.sh` after artifact creation (skeleton and full branches), and `gate.py`/`_DEFAULT_CHECKS["plan_done"]` already registers a `propose_quality_checks` Check. The `propose_quality_hook.py` module and `propose_quality_hook.sh` wrapper also already exist. The code is implemented — this change documents the design decisions that led to the final implementation.

## Goals / Non-Goals

**Goals:**
- Wire the existing `propose_quality_check.py` into the propose.md Phase 4 artifact creation flow
- Wire the same check into the `plan_done` gate as a warning-level check
- Persist check results to `.rddf/state/propose-quality.json` for the gate to consume
- Use `STRICT_PROPOSE_GATE=yes` env var to upgrade warnings to errors (matching ADR-0019's strict pattern)

**Non-Goals:**
- Modifying the 5 check functions in `propose_quality_check.py`
- Adding new check categories
- Content review (see separate `add-propose-content-review` improvement)
- Wiring into `ship_done` gate (only `plan_done`, per ADR-0007 §phase-gates)

## Decisions

### Decision 1: Dedicated hook module vs. inline bash invocation

- **Why**: A dedicated Python module (`propose_quality_hook.py`) provides structured error handling, JSON serialization, and ISO timestamps. The bash wrapper (`propose_quality_hook.sh`) is a thin env-var-safe shim (Oracle C1).
- **Alternative**: Inline `python3 -c` in propose.md
- **Rejected**: Would duplicate the Python logic, making it hard to test and maintain

### Decision 2: Hook runs after both skeleton and full artifact creation

- **Why**: A skeleton proposal will always produce warnings (short, no ADR, no scope, no tasks). That's the point — surface the gap early so the author fills in the skeleton before proceeding.
- **Alternative**: Only run after full artifact creation
- **Rejected**: Would miss the opportunity to surface quality issues at the earliest possible point

### Decision 3: Gate reads cached report, falls back to re-running

- **Why**: The Phase 4 hook writes `.rddf/state/propose-quality.json`. The gate reads this cached report to avoid re-running checks. If the file is missing or corrupt, the gate falls back to calling `run_all_checks()` directly.
- **Alternative**: Always re-run checks at gate time
- **Rejected**: Redundant work; the Phase 4 hook already ran the checks moments earlier

### Decision 4: `STRICT_PROPOSE_GATE` env var controls both propose-time and gate-time severity

- **Why**: Single control surface. Matches ADR-0019's established pattern (`STRICT_ARCH_GATE`, `STRICT_CHANGE_GATE`).
- **Alternative**: Separate env vars for propose-time vs gate-time
- **Rejected**: Unnecessary complexity; the same quality bar applies at both points

### Decision 5: Gateway uses `strict_wrap` from `arch_quality_gate`

- **Why**: `strict_wrap` is the established pattern for env-var-controlled gate upgrades. It wraps any check function and returns `(False, "error")` instead of `(False, "warning")` when the env var is set.
- **Alternative**: Manual env var check inside `_check_propose_quality`
- **Rejected**: Duplicates existing infrastructure; `strict_wrap` is the standard approach per ADR-0019

## Architecture

```
propose.md Phase 4 (existing)
  ├── propose_create_change / propose_finalize_change (existing)
  └── Step 4e: invoke_propose_quality_hook <name>          <-- this change
        ├── python3 propose_quality_hook.py
        │     ├── calls propose_quality_check.run_all_checks(name, project_root)
        │     ├── prints warnings to stdout
        │     └── writes .rddf/state/propose-quality.json (machine-readable)
        └── exit code: 0 (default), 1 (STRICT_PROPOSE_GATE=yes + warnings)

gate.py plan_done (existing)
  └── Check("propose_quality_checks", strict_wrap(_check_propose_quality, env_var="STRICT_PROPOSE_GATE"))
        └── _check_propose_quality(ctx):
              ├── read plan_side.current_change from state vector
              ├── read .rddf/state/propose-quality.json (cached)
              │     └── fallback: re-run run_all_checks()
              └── return (len(warnings) == 0, "warning")
```

## API

### `propose_quality_hook.py` entrypoints

```python
def run_quality_check(project_root: str, change_name: str) -> dict:
    """Run all 5 checks and persist report.
    Returns dict with schema_version, change, warnings, checked_at, strict_mode, check_count, passed_count.
    Writes to <project_root>/.rddf/state/propose-quality.json
    """

def invoke_from_propose_phase4(change_name: str) -> int:
    """Bash-callable entrypoint. Reads PROJECT_ROOT from env.
    Returns exit code: 0 (pass or warnings-only), 1 (strict mode + warnings).
    """
```

### `propose_quality_hook.sh` entrypoint

```bash
invoke_propose_quality_hook <name>
    # Env-var only: PROJECT_ROOT, CHANGE_NAME
    # Delegates to: python3 propose_quality_hook.py
```

### `gate.py` check function

```python
def _check_propose_quality(ctx: dict) -> tuple[bool, Optional[str]]:
    """Read cached report or re-run checks. Default warning-level.
    STRICT_PROPOSE_GATE=yes upgrades via strict_wrap.
    """
```

## Severity Model

| Mode | Env var | Propose-time exit | Gate plan_done |
|------|---------|-------------------|----------------|
| Default | (unset) | 0 (warnings printed) | warning recorded, transition allowed |
| Strict | `STRICT_PROPOSE_GATE=yes` | 1 (warnings printed) | warning auto-upgrades to error, transition blocked |

## State File: `.rddf/state/propose-quality.json`

```json
{
  "schema_version": 1,
  "change": "propose-quality-autohook",
  "warnings": ["proposal.md too short: 130 chars (min 500)"],
  "checked_at": "2026-07-26T17:21:00.000Z",
  "strict_mode": false,
  "check_count": 5,
  "passed_count": 3
}
```

## Test Plan

| Test | Scenario | Expected |
|------|----------|----------|
| hook writes valid JSON | Run `run_quality_check` | `.rddf/state/propose-quality.json` exists, valid JSON |
| default mode exit 0 | Valid proposal, no STRICT env var | `invoke_from_propose_phase4` returns 0 |
| strict + warnings exit 1 | Skeleton proposal, `STRICT_PROPOSE_GATE=yes` | Returns 1 |
| strict + no warnings exit 0 | Valid proposal, `STRICT_PROPOSE_GATE=yes` | Returns 0 |
| gate includes check | Query `plan_done` checks | `propose_quality_checks` in check names |
| gate default: warning | State file has warnings, no STRICT env | Gate passes, warning recorded |
| gate strict: error | State file has warnings, `STRICT_PROPOSE_GATE=yes` | Gate fails |
| gate missing state vector | `ctx` has no state_vector | Check skipped, returns pass |
| integration: hook exists | File exists | `propose_quality_hook.sh` with `invoke_propose_quality_hook` |
| integration: propose.md invokes | grep propose.md | `propose_quality_hook.sh` referenced |
| integration: hook valid proposal | Run hook against valid artifacts | Exit 0, JSON written |
| integration: hook broken default | Run hook against skeleton | Exit 0 (default mode) |
| integration: hook broken strict | Run hook against skeleton, `STRICT_PROPOSE_GATE=yes` | Exit 1 |