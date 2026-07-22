---
SCOPE: shared
STATUS: PROPOSED
---

## Why

`skills/_lib/scan-state.sh::check_stale_workflow_state` has an infinite-recursion bug. The function body ends with a self-call (line 220) without a base case, causing `scan_state` to hang whenever the function is invoked from the priority 9/10 default fallback.

**Root cause** (scan-state.sh:212-221):

```bash
check_stale_workflow_state() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  if [ -f "$PROJECT_ROOT/workflow-state.md" ]; then
    echo "⚠️  Stale workflow-state.md detected (pre-refactor format)."
    echo "   This file is no longer used and will be ignored."
    echo "   Remove it manually if you want: rm workflow-state.md"
  fi

  check_stale_workflow_state "$PROJECT_ROOT"   # ← LINE 220: self-call, no return
}
```

The trailing `check_stale_workflow_state "$PROJECT_ROOT"` has no `return` statement and no base case. Each call spawns another, eventually exhausting the stack or hitting the bash call-depth limit.

**Observed impact** (2026-07-15): in a clean repo (no active changes, no arch-handoff, no plan-handoff), `scan_state` reaches the priority 9/10 default fallback and calls `check_stale_workflow_state`. The scanner hangs indefinitely. Manual reproduction:

```bash
$ time source scan-state.sh && scan_state .
# hangs forever; no RECOMMEND output
```

**User-visible impact**: `guide` recommender skill cannot return a RECOMMEND line when the repo is in clean state — exactly the state users reach AFTER a ship completes. So the recommender is unusable post-ship unless the user manually inspects state.

## What Changes

1 line deletion + 1 line addition + 1 regression test + 1 doc note.

| File | Change | Responsibility |
|---|---|---|
| `skills/_lib/scan-state.sh` | Modify | Delete line 220 (recursive self-call), replace with `return 0` to terminate function after the optional warning emission |
| `tests/integration/test_scan_state_clean_hang.bats` | New | Regression test: source scan-state.sh in a clean temp repo, run `scan_state`, assert it returns within 1s with RECOMMEND set |
| `AGENTS.md` | Modify | Append note under "常见陷阱" documenting that `check_stale_workflow_state` is read-only + terminating |

### Capabilities

#### New Capabilities

(none — this is a bug fix, not new functionality)

#### Modified Capabilities

- `skills/_lib/scan-state.sh::check_stale_workflow_state` MUST terminate (not recurse) after the optional warning emission

## Impact

- **Affected files**:
  - `skills/_lib/scan-state.sh`: 1 line replaced
  - `tests/integration/test_scan_state_clean_hang.bats`: new ~30 LOC
  - `AGENTS.md`: +3 LOC note
- **Breaking changes**: none — the function's contract (warn if workflow-state.md exists, do nothing otherwise) is preserved; only the missing termination is added.
- **API changes**: none.
- **External dependencies**: none.
- **Cross-repo impact**: none. rdd-workflow meta-repo only.

## Acceptance Criteria

- [ ] `check_stale_workflow_state` returns within <100ms when workflow-state.md is absent
- [ ] `check_stale_workflow_state` returns within <100ms when workflow-state.md is present (warning emitted, then return)
- [ ] `scan_state` returns RECOMMEND within <1s on clean state (regression test)
- [ ] existing bats tests for scan_state still pass (38 tests)
- [ ] `guide` scanner returns RECOMMEND line in <2s when run on clean repo
- [ ] AGENTS.md documents the read-only + terminating contract

## Risk

- **Behavior preservation** (low): the fix is a minimal surgical change. No logic shift. **Mitigation**: the 1-line change is testable by inspection, plus the new regression test asserts the function terminates within 1s.
- **Other scan-state.sh bugs** (low): this fix is targeted; other potential issues (e.g., the priority 1.5 ADR-count python subprocess) are out of scope. **Mitigation**: leave a comment in AGENTS.md noting that broader scan-state.sh audits are tracked separately.

## Supersession / Dependencies

- **Does not supersede** any existing change.
- **Dependencies**: none (uses existing test infrastructure).
- **Unblocks**: clean-state `guide` recommender usability post-ship.