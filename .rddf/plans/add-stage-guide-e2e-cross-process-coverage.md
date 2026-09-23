# add-stage-guide-e2e-cross-process-coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 6 true cross-process end-to-end test cases to the rdd-workflow-e2e test bed, validating the core architecture promise of feat-guide-orchestrator-session-event-bus (multiple OpenCode windows observing each other via file polling on `.rddf/state/events.jsonl`).

**Architecture:** Single shared fixture (`.bats` bash helper) spawns real Python child processes via `bash &` (NOT in-process mocks). Each case asserts file-level invariants after child exit: events.jsonl line count, sessions.json field values, last_seen_offset arithmetic, fcntl.flock-derived properties. Reuses existing `setup_fake_project` + `invoke_*` pattern from rdd-workflow-e2e.

**Tech Stack:** Bash 4+ (bats + fixture), Python 3.11+ (child process scripts via `python3 -c "..."`), fcntl stdlib (POSIX file lock semantics), no new deps.

---

## File Structure

### Test Files (target repo: `/workspace/project/rdd-workflow-e2e/`)

| File | Responsibility |
|------|----------------|
| `tests/_lib/test_stage_guide_cross_process_fixture.bash` | Shared fixture: `spawn_stage_guide_session <owner>`, `spawn_event_writer <owner> <count>`, `poll_events_since <offset>`, `assert_last_seen_offset <owner> <expected>` |
| `tests/integration/test_stage_guide_cross_process_e2e.bats` | 6 @test cases (AC-1 through AC-6) |
| `README.md` | Update test suite breakdown table (36 → 42 cases) + add cross-process category |
| `KNOWN_FAILURES.txt` | Append any platform-specific skip (e.g., macOS flock behavior) |

### Auxiliary File (this repo, for traceability)

| File | Responsibility |
|------|----------------|
| `.rddf/plans/add-stage-guide-e2e-cross-process-coverage.md` | THIS plan |

---

## Tasks (TDD 5-Step × 6 cases + 1 doc + 1 integration)

> Each case follows Red-Green-Refactor. The "red" state = no fixture function yet → setup fails. "Green" = fixture exists + case passes. "Refactor" = clean up.

### Task 0 — Setup (cross-cutting)

- [ ] 0.1 Verify rdd-workflow-e2e repo at `/workspace/project/rdd-workflow-e2e` is accessible (ls, .git/ exists, current branch known)
- [ ] 0.2 Symlink check: `~/.agents/skills/rdd-workflow → /workspace/project/rdd-workflow` (existing fixture mode per install_testbed.sh)
- [ ] 0.3 Confirm Python 3.11+ available (`python3 --version`)
- [ ] 0.4 Confirm fcntl available on test runner (`python3 -c "import fcntl; print('ok')"`)
- [ ] 0.5 Branch: in `/workspace/project/rdd-workflow-e2e`, create `feat/stage-guide-cross-process-coverage` branch off master

### Task 1 — Shared fixture (AC infrastructure)

- [ ] 1.1 (RED) In `tests/integration/test_stage_guide_cross_process_e2e.bats`, write a stub `@test "AC-X placeholder"` that calls `spawn_stage_guide_session owner_X` — bats fails with "command not found"
- [ ] 1.2 (GREEN) Create `tests/_lib/test_stage_guide_cross_process_fixture.bash` with `spawn_stage_guide_session` (writes a Python script that creates stage_guide session and writes its owner to `$BATS_TEST_TMPDIR/<owner>.pid`)
- [ ] 1.3 (GREEN) Add `spawn_event_writer <owner> <count>` (Python script that appends N events to events.jsonl as that owner)
- [ ] 1.4 (GREEN) Add `poll_events_since <offset>` (read events.jsonl, return count + new event_ids)
- [ ] 1.5 (GREEN) Add `assert_last_seen_offset <owner> <expected>` (read sessions.json, assert stage_guide session owned by <owner> has goal.last_seen_offset == <expected>)
- [ ] 1.6 (REFACTOR) Move placeholder test → rename to test_AC_1 placeholder, verify bats fails meaningfully without further code

### Task 2 — AC-1 fcntl 并发写 (2 real Python child processes write 50 events each)

- [ ] 2.1 (RED) Write `@test "AC-1: two processes concurrently append_event — no row loss or duplication"`: spawn 2 child processes, each writes 50 events to same events.jsonl, wait both, assert total events == 100 with unique event_ids
- [ ] 2.2 (RED) Run bats — fail (bats fixture not yet ready or count assertion wrong)
- [ ] 2.3 (GREEN) In fixture, `spawn_event_writer` calls Python script that uses `events_log.append_event` in a loop with 0.01s sleep between writes (so processes genuinely interleave)
- [ ] 2.4 (GREEN) Helper `count_events` that reads events.jsonl line count after both processes exit
- [ ] 2.5 (GREEN) Helper `collect_event_ids` that returns set of event_ids
- [ ] 2.6 (VERIFY GREEN) Run bats — case passes

### Task 3 — AC-2 offset 轮询时序 (process A writes, process B polls with incrementing offset)

- [ ] 3.1 (RED) Write `@test "AC-2: poll reads_since(offset) monotonically advances"`: process A writes 20 events over 2s, process B polls 5 times every 400ms, assert final read_since offset ≥ 10
- [ ] 3.2 (GREEN) `spawn_event_writer` with `--rate <Hz>` flag for paced writes
- [ ] 3.3 (GREEN) `poll_events_since` returns count of new events since last poll (caller manages offset persistence)
- [ ] 3.4 (VERIFY GREEN) Run bats — case passes; offset advances monotonically

### Task 4 — AC-3 crash 残留恢复 (process A killed, process B sees residual session)

- [ ] 4.1 (RED) Write `@test "AC-3: kill -9 child leaves session active + events intact"`: spawn process A that creates stage_guide + writes 5 events, then `kill -9 $A_PID`, then spawn process B that reads sessions.json (asserts A's stage_guide state=active) + reads events.jsonl from offset=0 (asserts 5 events visible)
- [ ] 4.2 (GREEN) Fixture `kill_pid <pid>` (uses bash kill -9) + `wait_or_zombie <pid>` (returns immediately, no zombie wait)
- [ ] 4.3 (GREEN) Fixture `read_sessions_json` returns parsed sessions dict
- [ ] 4.4 (VERIFY GREEN) Run bats — case passes

### Task 5 — AC-4 H7 全局单例 (2 owners, 2nd create_session raises ConflictError)

- [ ] 5.1 (RED) Write `@test "AC-4: second create_session(stage_guide) returns ConflictError"`: spawn process A (owner=A) that succeeds creating stage_guide, spawn process B (owner=B) that tries to create stage_guide, assert B's stderr contains ConflictError AND sessions.json has exactly 1 active stage_guide
- [ ] 5.2 (GREEN) Fixture `spawn_stage_guide_with_exit_code <owner>` returns child's exit code (so caller can distinguish success vs ConflictError)
- [ ] 5.3 (GREEN) Fixture `count_active_stage_guide_sessions` (reads sessions.json, counts stage_guide kind with state=active)
- [ ] 5.4 (VERIFY GREEN) Run bats — case passes

### Task 6 — AC-5 自动归档重置 (events.jsonl hits 50MB, last_seen_offset resets to 0)

- [ ] 6.1 (RED) Write `@test "AC-5: after archive, active stage_guide last_seen_offset == 0"`: spawn process that creates stage_guide with last_seen_offset=50, spawn process that writes enough events to trigger archive (set `RDDF_EVENTS_LOG_MAX_SIZE_MB=1` env to make 50MB cap tiny), trigger archive via direct call, assert last_seen_offset == 0
- [ ] 6.2 (GREEN) Fixture `trigger_archive_via_api` calls Python that imports events_log.archive_events with sessions_file
- [ ] 6.3 (GREEN) Fixture env-var injection via child Python invocation (`RDDF_EVENTS_LOG_MAX_SIZE_MB=1 python3 -c "..."`)
- [ ] 6.4 (VERIFY GREEN) Run bats — case passes

### Task 7 — AC-6 guide_entry 持久化 (subshell exit triggers guide_close, abnormal exit preserves active)

- [ ] 7.1 (RED) Write `@test "AC-6a: guide_entry in subshell + kill -1 → stage_guide marked completed"`: bash subshell runs `bash guide_entry.sh &` + sends kill -1 to subshell + waits, asserts sessions.json stage_guide state=completed
- [ ] 7.2 (RED) Write `@test "AC-6b: guide_entry in subshell + kill -9 → stage_guide remains active"`: similar but kill -9 (no chance for EXIT trap), asserts stage_guide state=active
- [ ] 7.3 (GREEN) Fixture `run_guide_entry_subshell <owner>` (sources guide_entry.sh in subshell, traps EXIT/INT/TERM)
- [ ] 7.4 (VERIFY GREEN) Run both bats cases pass

### Task 8 — Documentation + regression gate (AC-7, AC-8, AC-9)

- [ ] 8.1 Update `/workspace/project/rdd-workflow-e2e/README.md` §Test suite breakdown table: add row for `test_stage_guide_cross_process_e2e.bats` (6 cases) + bump total "36 → 42"
- [ ] 8.2 Add category description: "Cross-process: real subprocess spawn + fcntl.flock contention + offset timing"
- [ ] 8.3 Add KNOWN_FAILURES.txt entry if macOS flock tests skipped (run on Linux, append only if observed)
- [ ] 8.4 Run `bash tests/scripts/report_regression.sh` in rdd-workflow-e2e — 0 new failures expected
- [ ] 8.5 Run `./test.sh --quick` in /workspace/project/rdd-workflow — confirm 0 new failures in this repo

### Task 9 — Final integration + commit

- [ ] 9.1 Run full `bats tests/` in rdd-workflow-e2e — 42/42 pass (or 36 baseline + 6 new = 42 expected)
- [ ] 9.2 Commit on `feat/stage-guide-cross-process-coverage` branch:
  - `tests/_lib/test_stage_guide_cross_process_fixture.bash`
  - `tests/integration/test_stage_guide_cross_process_e2e.bats`
  - `README.md` (updated test suite table)
  - KNOWN_FAILURES.txt (only if needed)
- [ ] 9.3 Open PR against chisuhua/rdd-workflow-e2e master

---

## Acceptance Mapping

| Plan Task | Proposal AC |
|-----------|-------------|
| Task 2 | AC-1 (fcntl 并发) |
| Task 3 | AC-2 (offset 时序) |
| Task 4 | AC-3 (crash 恢复) |
| Task 5 | AC-4 (H7 单例) |
| Task 6 | AC-5 (归档重置) |
| Task 7 | AC-6 (guide_entry 持久化) |
| Task 8 | AC-7 (README sync) |
| Task 8 | AC-8 (e2e regression gate) |
| Task 8 | AC-9 (主仓 regression gate) |

## Risks & Mitigations

- **flaky tests**: AC-1/AC-2 have inherent timing variance. Add 3x retry wrapper (`run_with_retry 3 bats`) for these.
- **macOS flock differences**: Linux flock fcntl differs from BSD style. Document skip in KNOWN_FAILURES if observed.
- **CI container limits**: subprocess.Popen + fcntl works in Docker; no special config needed.
- **Cleanup**: each test must `rm -rf $BATS_TEST_TMPDIR` in teardown to avoid lock file pollution.

## Definition of Done

- [ ] All 6 AC cases green on Linux
- [ ] README test suite table updated
- [ ] PR opened against rdd-workflow-e2e master
- [ ] No new failures in either repo's regression gate
- [ ] Total test count: 36 + 6 = 42 in rdd-workflow-e2e
