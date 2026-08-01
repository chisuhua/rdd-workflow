## Why

`guide-ship` Phase 5 (ship-done) is the natural exit point of the execution workflow, but its menu never tells the user when orphaned rddf-sessions exist. Users only see those orphans at the `guide` recommender entry, so by the time they reach ship-done they have already missed the cue and orphaned sessions accumulate without cleanup. This change adds a read-only orphan count and a conditional menu option to the ship-done prompt so users can act before leaving the workflow.

## What Changes

- `skills/guide-ship/scripts/ship_done.sh::check_remaining_work`: add read-only orphaned rddf-session detection and a conditional option 5 (`🧹 清理 N 个 orphaned sessions`) when at least one orphaned session exists; preserve the existing 4-option menu and both header variants exactly when no orphans are present.
- New helper `skills/_lib/sessions_count.sh::count_orphaned_sessions <project_root>`: a pure read-only function that counts `state == "orphaned"` entries in `.rddf/state/sessions.json`, returns `0` silently when the file is missing or corrupt, and echoes only an integer.
- `tests/integration/test_ship_done_orphan_prompt.bats`: six-case matrix covering (orphans × changes), missing `sessions.json`, corrupt JSON, and overflow summary when more than three orphans exist.
- `skills/guide-ship/SKILL.md` Phase 5 section: add one short paragraph documenting the orphan prompt and option 5.

## Capabilities

### New Capabilities

- `ship-done-orphan-cleanup`: The `guide-ship` ship-done menu detects orphaned rddf-sessions, prints a warning that lists the first three IDs (with `+N more` overflow), and offers a conditional option 5 to launch the `rddf-session` cleanup skill. No automatic cleanup occurs; the user must explicitly choose the option. Existing menu options 1-4 and the `i. 其他输入` fallback keep their exact wording and order.

### Modified Capabilities

(none — no existing spec behavior changes; only the ship-done menu gains an extra option)

## Impact

- Affects one helper file and one menu function in `guide-ship`. No rddf-session schema, state-machine, or abandon/archive-history logic changes. Existing ship-done behavior is unchanged when no orphaned sessions exist. The menu becomes visually identical to the previous version in that case (diff = 0 bytes), preserving downstream tests that lock the 4-option layout.
