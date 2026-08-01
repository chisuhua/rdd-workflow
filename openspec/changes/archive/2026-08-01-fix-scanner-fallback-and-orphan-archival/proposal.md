## Why

The rdd-workflow `guide` recommender silently failed in a downstream consumer project (HydraForge, 2026-07-31) because `skills/guide/scripts/scan-state.sh` and `skills/guide/scripts/guide_entry.sh` hard-coded `source "$PROJECT_ROOT/skills/_lib/state.sh"`. When the consumer project is installed globally (no local `skills/_lib/state.sh`), the source fails without a visible warning, leaving users with an empty menu and no actionable path. At the same time, rddf-session heartbeat-timeout sessions are marked `orphaned`, but `archive_history(keep=0)` does not archive them because `_TERMINAL_STATES` only contains `completed`, `failed`, and `abandoned`. This left seven orphaned sessions behind in the HydraForge case, requiring a manual schema workaround.

## What Changes

- `skills/guide/scripts/scan-state.sh:67`: replace the hard-coded `source "$PROJECT_ROOT/skills/_lib/state.sh"` with a local-then-global fallback (`$PROJECT_ROOT/skills/_lib/state.sh` → `${HOME}/.agents/skills/_lib/state.sh`) and a non-blocking stderr warning when both are missing.
- `skills/guide/scripts/guide_entry.sh:185`: apply the same fallback for `detect_approved_inconsistency` / `sweep_stale_suggestions` helpers.
- `skills/rddf-session/scripts/rddf_session_pkg/_types.py:42`: add `"orphaned"` to `_TERMINAL_STATES` while keeping the existing `completed`, `failed`, and `abandoned` states.
- Add `tests/integration/test_scanner_fallback.bats` covering the four presence/absence combinations of the local and global `state.sh` copies.
- Add `tests/unit/test_terminal_states_orphan.bats` covering the four terminal states (completed, failed, abandoned, orphaned) and the archive contract.
- Update `AGENTS.md` "常见陷阱" and `CHANGELOG.md` to document the scanner fallback behavior and the orphaned terminal state.

## Capabilities

### New Capabilities

- `scanner-fallback`: The `guide` recommender scanner can load shared bash helpers from a global rdd-workflow install when the consumer project has no local `skills/_lib/state.sh`, and emits a non-blocking stderr warning when neither copy exists.
- `orphan-session-archival`: The rddf-session coordinator treats heartbeat-timeout `orphaned` sessions as terminal, so `archive_history(keep=0)` moves them to `.archive.json` instead of leaving them in `sessions.json`.

### Modified Capabilities

(none — no existing spec-level behavior changes)

## Impact

- Affects two source lines in `skills/guide/scripts/scan-state.sh` and `guide_entry.sh` and one constant in `_types.py`. No changes to helper logic or install layout. Existing rdd-workflow projects (local `state.sh` present) see zero behavioral change. Downstream consumer projects with a global install now get a working recommender menu instead of silent failure. The orphaned-session archive fixes the HydraForge 11-session cleanup without manual schema workaround.
