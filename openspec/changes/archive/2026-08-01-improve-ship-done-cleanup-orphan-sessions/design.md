## Context

`skills/guide-ship/scripts/ship_done.sh` exports `check_remaining_work()`, which prints one of two menu variants at the end of `guide-ship` Phase 5 (ship-done). When there are remaining worktrees or unprocessed changes it prints the `"📋 还有 ..."` header; otherwise it prints `"✅ 所有 changes 已处理完毕"`. Both variants currently print the same four numbered options (1-4) plus the `i. 其他输入` fallback. The function is intentionally small (46 lines) and its stdout is locked by `tests/integration/test_ship_done_semantics.bats`.

Separately, rddf-session lifecycle data is stored in `.rddf/state/sessions.json`. A session becomes `orphaned` when its heartbeat times out (ADR-0017 §3). The `guide` recommender entry already lists the number of orphaned sessions, but `guide-ship` ship-done never surfaces them, so users who reach the end of a workflow batch leave without being reminded to clean up.

## Goals / Non-Goals

**Goals:**
- Add a read-only helper that counts orphaned sessions in `.rddf/state/sessions.json` and returns `0` when the file is missing or unparseable.
- Extend `check_remaining_work()` to call the helper, display a non-blocking warning, and add option 5 (`🧹 清理 N 个 orphaned sessions ...`) when the count is greater than zero.
- Keep the existing four options and their wording exactly unchanged; option 5 must appear only when needed and must not alter the baseline output when the count is zero.
- List up to the first three orphaned session IDs, appending `... +N more` when more exist, to keep the menu vertically compact.
- Provide matrix bats tests covering all six required cases: orphans/no-orphans × changes/no-changes, missing sessions.json, corrupt JSON, and >3 orphans overflow.
- Document the new option in `skills/guide-ship/SKILL.md` Phase 5 with at most five lines.
- Stay within line constraints: `ship_done.sh` ≤ 30 lines, `sessions_count.sh` ≤ 20 lines, total new code ≤ 50 lines.

**Non-Goals:**
- No automatic cleanup; the user must explicitly choose option 5.
- No changes to the rddf-session skill's `abandon`, `archive-history`, or state-machine logic.
- No changes to `sessions.json` schema or `_TERMINAL_STATES`.
- No synchronization of the same prompt into `guide-arch` or `guide-plan`; those are out of scope.
- No new worktree or branch management; only menu UX changes.

## Decisions

- **New helper in `skills/_lib/sessions_count.sh`**: Cross-skill read-only utilities belong in `_lib` per ADR-0021 and the project helper convention. The helper is named `count_orphaned_sessions` and is a single atomic bash function that accepts `project_root` as its only argument.
- **Read-only + fail-silent**: The helper uses `jq` when available and falls back to `python3 -c`. If either path fails (file missing, permission denied, corrupt JSON), it echoes `0` and exits `0`. This matches the `check_stale_workflow_state` sentinel pattern and guarantees ship-done never blocks on a broken state file.
- **Human-readable list produced by caller**: The helper echoes only an integer. `check_remaining_work()` builds the warning line and the first-three ID list by reading the same JSON again, keeping the helper reusable for other callers that only need a count.
- **Option 5 placement**: Option 5 is appended after option 4 and before `i. 其他输入`, preserving the order and exact wording of options 1-4. When no orphans exist, option 5 is omitted entirely and the baseline output is identical to today.
- **No conditional warning injection into the "还有" branch header**: The orphan warning is printed as a body line between the header and the menu, consistent with the existing structure. This keeps both branches readable and avoids changing the header lines.
- **Bash implementation for line constraints**: Both files stay pure bash. Python is used only as a jq fallback inside the helper, and the helper output is parsed with simple shell tools.

## Risks / Trade-offs

- [Risk] Reading `sessions.json` twice (once for count, once for IDs) could race with a concurrent writer → Mitigation: the file is small and written atomically (write-temp + rename) per the rddf-session schema contract; worst case the ID list is slightly stale, which is acceptable for a best-effort prompt.
- [Risk] `jq` may not be installed in some environments → Mitigation: the helper falls back to `python3 -c`, which is already required by the project (Python 3.11+ per CI).
- [Risk] Adding option 5 could confuse existing tests that count four options → Mitigation: tests are added to assert option 5 only appears when orphans exist, and the existing `test_ship_done_semantics.bats` continues to pass because the baseline variant is unchanged.
- [Risk] Line-count constraint (≤50 lines total) limits defensive error handling → Mitigation: the helper defaults to `0` on any failure and the caller wraps the call in a local variable; the matrix tests cover the corrupt and missing-file cases.

## Migration Plan

N/A — this is an additive UX improvement. Existing projects without orphaned sessions see no output change. Projects with orphaned sessions will see the new prompt only when they run `guide-ship` ship-done.

## Open Questions

None.
