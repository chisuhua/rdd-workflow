# Design: propose-quality-autohook

> Wire the existing (dead-asset) `propose_quality_check.py` into the
> propose.md Phase 4 flow and into the `plan_done` gate. The checker
> itself was implemented by the prior change `add-propose-output-validation`
> (archived 2026-07-20). This change only does the wiring.

## Why

`propose_quality_check.py` (5 structural checks) has been a dead asset
since it was introduced. The unit-test suite
(`tests/unit/test_propose_quality_check.py`) covers the 5 checks, but
no caller in the propose flow or in any gate invokes it. As a result
low-quality proposals enter the change pipeline with no automatic
signal to the author or reviewer.

This change wires the checker at two points:

1. **propose.md Phase 4** - Immediately after the skeleton / finalized
   artifacts are written (after `propose_create_change` /
   `propose_finalize_change`), invoke the checker. The result is
   printed to stdout and persisted to
   `.rddf/state/propose-quality.json` for later inspection. Default
   mode is warning-only; `STRICT_PROPOSE_GATE=yes` upgrades to a
   non-zero exit so callers can decide to abort the propose loop.

2. **gate.py plan_done** - Register a new warning-level `Check` named
   `propose_quality_checks` that re-runs the 5 checks. The check
   reuses `strict_wrap(env_var="STRICT_PROPOSE_GATE")` so the same
   env var governs both the propose-time invocation and the gate
   upgrade (per ADR-0007 §warning-does-not-block and ADR-0019 §strict
   pattern).

## Architecture

```
propose.md Phase 4 (existing)
  ├── propose_create_change / propose_finalize_change (existing)
  └── NEW: invoke_propose_quality_check()      <-- this change
        ├── subprocess: python3 -m skills.propose.scripts.propose_quality_check --change <name>
        ├── print stdout to propose.md output
        └── write .rddf/state/propose-quality.json (machine-readable view)

gate.py plan_done (existing)
  └── NEW: Check("propose_quality_checks", strict_wrap(_check_propose_quality, env_var="STRICT_PROPOSE_GATE"), ...)
                └── _check_propose_quality(ctx): read .rddf/state/propose-quality.json
                    (or re-run if missing) and emit (passed, severity)
```

### File location

```
skills/propose/scripts/
  __init__.py                       # existing
  propose_change.py                 # existing
  propose_quality_check.py          # existing (5 checks, untouched)
  propose_quality_hook.py           # NEW - Phase 4 hook (Python entrypoint)
  propose_quality_hook.sh           # NEW - bash wrapper (env-var safe, Oracle C1)

skills/_lib/
  gate.py                           # MODIFIED - add propose_quality_checks Check to plan_done
```

### Module shape

#### `propose_quality_hook.py` (NEW)

```python
def run_quality_check(project_root: str, change_name: str) -> dict:
    """Run propose_quality_check.run_all_checks and persist result.

    Returns dict:
      {
        "change": <name>,
        "warnings": list[str],
        "checked_at": ISO timestamp,
        "strict_mode": bool
      }
    Writes to: <project_root>/.rddf/state/propose-quality.json
    """

def invoke_from_propose_phase4(change_name: str) -> int:
    """Bash-callable entrypoint. Reads PROJECT_ROOT env var.
    Returns exit code: 0 (warnings-or-pass), 1 (strict + warnings).
    """
```

#### `propose_quality_hook.sh` (NEW)

Thin bash wrapper that sets env vars and delegates to Python. Oracle
C1 safe: passes arguments via env vars only, no string interpolation.

```bash
PROJECT_ROOT="$PROJECT_ROOT" CHANGE_NAME="$1" \
  python3 "$SCRIPT_DIR/propose_quality_hook.py"
```

### Integration into propose.md Phase 4

After `propose_create_change` (skeleton branch) OR
`propose_finalize_change` (full branch), add a single invocation:

```bash
# Step 4e: Quality check (propose-quality-autohook)
if [ -f "$SCRIPT_DIR/propose_quality_hook.sh" ]; then
    source "$SCRIPT_DIR/propose_quality_hook.sh"
    invoke_propose_quality_hook "<name>"
    # exit code 0 = pass or warnings-only; 1 = STRICT_PROPOSE_GATE=yes + warnings
fi
```

The hook is idempotent and never blocks the propose loop by default
(warning-level). It writes
`.rddf/state/propose-quality.json` for the gate to read later.

### Integration into gate.py plan_done

```python
def _check_propose_quality(ctx: dict) -> tuple[bool, Optional[str]]:
    """Run propose_quality_check.run_all_checks. Default warning-level;
    STRICT_PROPOSE_GATE=yes upgrades via strict_wrap.
    """
    # Read active change from state vector
    sv = ctx.get("state_vector")
    if sv is None:
        return (True, None)  # no state -> skip
    name = sv.get_field("plan_side.current_change")
    if not name:
        return (True, None)
    # Read cached report (Phase 4 wrote it); fall back to re-running
    report_path = ".rddf/state/propose-quality.json"
    if os.path.isfile(report_path):
        try:
            with open(report_path) as f:
                report = json.load(f)
            warnings = report.get("warnings", [])
        except (json.JSONDecodeError, OSError):
            warnings = run_all_checks(name, project_root)
    else:
        warnings = run_all_checks(name, project_root)
    return (len(warnings) == 0, "warning")

# In _DEFAULT_CHECKS["plan_done"]:
Check(
    "propose_quality_checks",
    strict_wrap(_check_propose_quality, env_var="STRICT_PROPOSE_GATE"),
    "propose quality checks failed",
    "Fix proposal/tasks content; see .rddf/state/propose-quality.json",
    "warning",
),
```

### Severity model (ADR-0007 §warning-does-not-block)

| Mode | Env var | Propose-time | Gate plan_done |
|------|---------|--------------|----------------|
| Default | (unset) | warnings printed, exit 0 | warning recorded, transition allowed |
| Strict | `STRICT_PROPOSE_GATE=yes` | warnings printed, exit 1 | warning auto-upgrades to error, transition blocked |

The `STRICT_PROPOSE_GATE` env var is the single control surface. This
matches ADR-0019's pattern of one env var per gate
(`STRICT_ARCH_GATE`, `STRICT_CHANGE_GATE`, `STRICT_PROPOSE_GATE`).

### State file: `.rddf/state/propose-quality.json`

```json
{
  "schema_version": 1,
  "change": "<change-name>",
  "warnings": ["proposal.md too short: 130 chars (min 500)", ...],
  "checked_at": "2026-07-21T12:34:56.789Z",
  "strict_mode": false,
  "check_count": 5,
  "passed_count": 3
}
```

- `schema_version: 1` - bumps when fields change (per AGENTS.md state-file convention)
- `warnings` - the list returned by `run_all_checks`
- `check_count: 5` / `passed_count` - derived counts (5 - len(warnings))
- `strict_mode` - whether `STRICT_PROPOSE_GATE=yes` was active when the check ran

Like `iteration.json` and `deps-analysis.json`, this is a view file
written by the propose hook and read by the gate. It is gitignored
(under `.rddf/state/`).

## STRICT_PROPOSE_GATE

| Trigger | Effect |
|---------|--------|
| unset | warning-level only (default) |
| `STRICT_PROPOSE_GATE=yes` | warnings become errors at propose-time AND in plan_done gate |
| `--strict` CLI flag (when run directly) | same as env var (CLI precedence) |

The env var is the canonical control. CLI flag is for ad-hoc manual
runs of `propose_quality_check.py`; the propose flow only relies on
the env var.

## What This Change Does NOT Do

- Does **not** modify the 5 check functions in `propose_quality_check.py`
  (per Out Scope).
- Does **not** add new check categories (per Out Scope).
- Does **not** perform content review (per Out Scope, see
  `add-propose-content-review`).
- Does **not** wire the gate into `ship_done` (only `plan_done`, per
  ADR-0007 §phase-gates).
- Does **not** change the iteration.json schema.

## Testing

### Unit tests (`tests/unit/test_propose_quality_hook.py`)

- `run_quality_check` writes a valid JSON report
- `run_quality_check` correctly aggregates warnings from underlying checker
- `invoke_from_propose_phase4` returns 0 in default mode
- `invoke_from_propose_phase4` returns 1 under `STRICT_PROPOSE_GATE=yes` + warnings
- `invoke_from_propose_phase4` returns 0 under strict mode with no warnings
- Report includes correct `schema_version`, `check_count`, `passed_count`

### Gate tests (extend `tests/unit/test_gate.py`)

- `plan_done` gate includes `propose_quality_checks` check name
- Default mode: warnings -> gate passes, warning recorded
- `STRICT_PROPOSE_GATE=yes`: warnings -> gate fails
- Missing state vector -> check skipped (returns pass)
- Missing state file -> falls back to re-running `run_all_checks`

### Integration tests (`tests/integration/test_propose_quality_hook.bats`)

- `propose_quality_hook.sh` exists with `invoke_propose_quality_hook` function
- `propose.md` Phase 4 invokes the hook (grep for `propose_quality_hook.sh`)
- Hook runs against a valid proposal -> exit 0, JSON file written
- Hook runs against a skeleton (broken) proposal -> exit 0 in default mode,
  warnings present in JSON
- Hook runs against a skeleton under `STRICT_PROPOSE_GATE=yes` -> exit 1
- `gate.py` registers `propose_quality_checks` in plan_done

## Open Questions (deferred)

1. **Should the hook also run after skeleton mode?** - Yes, it's
   invoked for both branches. A skeleton will always produce warnings
   (that's the point - surface the gap early).
2. **Should the state file carry multiple changes' reports?** - No,
   the latest report overwrites. The state file is a snapshot for the
   gate to consume; historical reports go to the event log if needed.
3. **Should we add a CI smoke that sets STRICT_PROPOSE_GATE=yes?** -
   Out of scope; CI configuration is a separate concern.

## References

- ADR-0007 §warning-does-not-block - gate severity model
- ADR-0019 §strict pattern - one env var per gate
- ADR-0015 - openspec validate integration (similar pattern: warning
  default, env-var upgrade)
- Prior change `add-propose-output-validation` (archived
  2026-07-20) - the checker module itself
- `tests/unit/test_propose_quality_check.py` - existing unit tests
  for the 5 checks (untouched by this change)
