# fix-scanner-fallback-and-orphan-archival Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `guide` recommender scanner load `skills/_lib/state.sh` from a global rdd-workflow install when no local copy exists, and treat rddf-session `orphaned` (heartbeat-timeout) sessions as terminal so `archive_history(keep=0)` archives them.

**Architecture:** Two surgical edits to `skills/guide/scripts/*.sh` replace the hard-coded `source "$PROJECT_ROOT/skills/_lib/state.sh"` with a 5-line `for` loop that tries local → global → emits a non-blocking stderr warning. One additive edit to `skills/rddf-session/scripts/rddf_session_pkg/_types.py` extends `_TERMINAL_STATES` from three to four elements. Two new test files (one bats integration, one bats unit) plus one new pytest case lock the contracts. Two doc updates record the new behavior.

**Tech Stack:** bash (bats-core tests), Python 3.11+ (rddf-session `_types.py` + pytest), Git worktree on branch `openspec/fix-scanner-fallback-and-orphan-archival`. No new dependencies; no new schemas.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide/scripts/scan-state.sh` | Replace line 67 hard-coded `source` with local-then-global fallback loop + non-blocking stderr warning. |
| `skills/guide/scripts/guide_entry.sh` | Replace line 185 hard-coded `source` with the same fallback loop + non-blocking stderr warning. |
| `skills/rddf-session/scripts/rddf_session_pkg/_types.py` | Add `"orphaned"` to `_TERMINAL_STATES` (line 42). |
| `AGENTS.md` | Add pitfall #18 documenting the scanner fallback behavior under "常见陷阱". |
| `CHANGELOG.md` | Add `### Fixed` bullets under `[Unreleased] — v2.1` for both fixes. |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_scanner_fallback.bats` (new) | Six `@test` cases covering the 4-cell local/global presence matrix for `scan_state` plus 2 cases for `guide_entry` fallback / warning. |
| `tests/unit/test_terminal_states_orphan.bats` (new) | Four `@test` cases asserting `_TERMINAL_STATES` membership for `completed`, `failed`, `abandoned`, `orphaned`. |
| `tests/unit/test_rddf_session.py` | Add `test_archive_history_archives_orphaned_and_keeps_active` case proving `archive_history(keep=0)` archives orphaned while preserving active. |

---

### Task 1: Add scanner fallback to `scan-state.sh`

**Files:**
- Create: `tests/integration/test_scanner_fallback.bats`
- Modify: `skills/guide/scripts/scan-state.sh:67`

Replaces tasks.md §1.1–§1.4 (4 checkboxes) with TDD 5-step structure.

- [ ] **Step 1: Write the failing test** — Create `tests/integration/test_scanner_fallback.bats` with the four-cell matrix from tasks.md §1.1 (`_make_state_sh`, `_run_scan_state`, `setup`/`teardown` with `mktemp -d` repo + HOME, four `@test` cases: local-only, global-only, both-present, neither-present). The file must:
  - Use `load ../test_helper` to pick up `$REPO_ROOT` and `setup`/`teardown` stubs.
  - Define `_make_state_sh <target>` to write a stub `state.sh` containing `check_dirty_key_files`, `detect_approved_inconsistency`, `sweep_stale_suggestions`, and `SCANNER_FALLBACK_SOURCE_PATH="${BASH_SOURCE[0]}"`.
  - Define `_run_scan_state <repo>` to `bash -c 'source "$REPO_ROOT/skills/guide/scripts/scan-state.sh"; scan_state "$1"; echo "RECOMMEND=$RECOMMEND"; echo "REASON=$REASON"' _ "$repo"`.
  - Cover: (a) both copies present → expect local source path AND `RECOMMEND=guide-arch`; (b) only global present → expect global source path AND `RECOMMEND=guide-arch`; (c) both missing → expect `status=0` and stderr contains literal `rdd-workflow not installed` AND `INSTALL.md`; (d) local vs global parity test asserts identical `RECOMMEND=`/`REASON=` lines.

- [ ] **Step 2: Run test to verify it fails** — `bats tests/integration/test_scanner_fallback.bats`. Expected: all 4 cases FAIL because `scan-state.sh:67` still hard-codes the local path, so the global fallback (case b), warning (case c), and local-priority assertion (case a) all break.

- [ ] **Step 3: Implement the local-then-global fallback loop** — Edit `skills/guide/scripts/scan-state.sh:67`. Replace the existing line:

  ```bash
    type -t check_dirty_key_files &>/dev/null || source "$PROJECT_ROOT/skills/_lib/state.sh"
  ```

  with:

  ```bash
    if ! type -t check_dirty_key_files &>/dev/null; then
      local _state_helper
      for _state_helper in "$PROJECT_ROOT/skills/_lib/state.sh" "${HOME}/.agents/skills/_lib/state.sh"; do
        [ -f "$_state_helper" ] && source "$_state_helper" && break
      done || echo "⚠️ rdd-workflow not installed: tried $PROJECT_ROOT/skills/_lib/state.sh and $HOME/.agents/skills/_lib/state.sh, both missing. Run INSTALL.md" >&2
    fi
  ```

  Verify the edit landed: `grep -n "rdd-workflow not installed" skills/guide/scripts/scan-state.sh` must return a line number.

- [ ] **Step 4: Run tests to verify they pass** — `bats tests/integration/test_scanner_fallback.bats`. Expected: 4 PASS (the case-d parity check now succeeds because both code paths emit identical `RECOMMEND=`/`REASON=` lines).

- [ ] **Step 5: Commit** — Stage the test file and source change; commit with the message from tasks.md §1.4:

  ```bash
  git add tests/integration/test_scanner_fallback.bats skills/guide/scripts/scan-state.sh
  git commit -m "fix(scanner): local-then-global state.sh fallback with non-blocking warning"
  ```

---

### Task 2: Add the same fallback to `guide_entry.sh`

**Files:**
- Modify: `skills/guide/scripts/guide_entry.sh:185`
- Modify: `tests/integration/test_scanner_fallback.bats` (append two more `@test` cases)

Replaces tasks.md §2.1–§2.3 (3 checkboxes) with TDD 5-step structure.

- [ ] **Step 1: Write the additional failing tests** — Append to `tests/integration/test_scanner_fallback.bats` the two `@test` cases from tasks.md §2.2:

  ```bash
  _run_guide_entry() {
    local repo="$1"
    local home="$2"
    bash -c '
      export HOME="$1"
      cd "$2"
      source "$3/skills/guide/scripts/guide_entry.sh"
      guide_entry --no-binding
    ' _ "$home" "$repo" "$REPO_ROOT"
  }

  @test "guide_entry fallback: global state.sh used when local is missing" {
    _make_state_sh "$home/.agents/skills/_lib/state.sh"
    run _run_guide_entry "$repo" "$home"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Workflow Entry"* ]]
    [[ "$output" != *"rdd-workflow not installed"* ]]
  }

  @test "guide_entry fallback: warning when both copies are missing" {
    run _run_guide_entry "$repo" "$home"
    [ "$status" -eq 0 ]
    [[ "$output" == *"rdd-workflow not installed"* ]]
    [[ "$output" == *"INSTALL.md"* ]]
  }
  ```

  These two new tests will FAIL at this point because `guide_entry.sh:185` still hard-codes the local path.

- [ ] **Step 2: Run tests to verify the new ones fail** — `bats tests/integration/test_scanner_fallback.bats`. Expected: 4 PASS (the original 4 from Task 1) + 2 FAIL (the new `guide_entry` cases — global fallback fails because local-only `source` errors, warning case fails because the warning string does not exist yet).

- [ ] **Step 3: Implement the same fallback loop in `guide_entry.sh`** — Edit `skills/guide/scripts/guide_entry.sh:185`. Replace the existing line:

  ```bash
    type -t detect_approved_inconsistency &>/dev/null || source "$PROJECT_ROOT/skills/_lib/state.sh"
  ```

  with:

  ```bash
    if ! type -t detect_approved_inconsistency &>/dev/null; then
      local _state_helper
      for _state_helper in "$PROJECT_ROOT/skills/_lib/state.sh" "${HOME}/.agents/skills/_lib/state.sh"; do
        [ -f "$_state_helper" ] && source "$_state_helper" && break
      done || echo "⚠️ rdd-workflow not installed: tried $PROJECT_ROOT/skills/_lib/state.sh and $HOME/.agents/skills/_lib/state.sh, both missing. Run INSTALL.md" >&2
    fi
  ```

  Verify the edit landed: `grep -n "rdd-workflow not installed" skills/guide/scripts/guide_entry.sh` must return a line number.

- [ ] **Step 4: Run tests to verify all six pass** — `bats tests/integration/test_scanner_fallback.bats`. Expected: 6 PASS (4 from Task 1 + 2 new `guide_entry` cases).

- [ ] **Step 5: Commit** — Stage both files; commit with the message from tasks.md §2.3:

  ```bash
  git add tests/integration/test_scanner_fallback.bats skills/guide/scripts/guide_entry.sh
  git commit -m "fix(guide): same local-then-global state.sh fallback in guide_entry"
  ```

---

### Task 3: Add `orphaned` to the rddf-session terminal states

**Files:**
- Create: `tests/unit/test_terminal_states_orphan.bats`
- Modify: `tests/unit/test_rddf_session.py`
- Modify: `skills/rddf-session/scripts/rddf_session_pkg/_types.py:42`

Replaces tasks.md §3.1–§3.5 (5 checkboxes) with TDD 5-step structure.

- [ ] **Step 1: Write the failing tests** — Two failing-test bodies:

  1. Create `tests/unit/test_terminal_states_orphan.bats` (from tasks.md §3.1):

     ```bash
     #!/usr/bin/env bats
     # Unit regression tests for rddf-session _TERMINAL_STATES including orphaned.

     load ../test_helper

     @test "terminal states include completed" {
       run python3 -c "from skills.rddf_session.scripts.rddf_session_pkg._types import _TERMINAL_STATES; assert 'completed' in _TERMINAL_STATES"
       [ "$status" -eq 0 ]
     }

     @test "terminal states include failed" {
       run python3 -c "from skills.rddf_session.scripts.rddf_session_pkg._types import _TERMINAL_STATES; assert 'failed' in _TERMINAL_STATES"
       [ "$status" -eq 0 ]
     }

     @test "terminal states include abandoned" {
       run python3 -c "from skills.rddf_session.scripts.rddf_session_pkg._types import _TERMINAL_STATES; assert 'abandoned' in _TERMINAL_STATES"
       [ "$status" -eq 0 ]
     }

     @test "terminal states include orphaned" {
       run python3 -c "from skills.rddf_session.scripts.rddf_session_pkg._types import _TERMINAL_STATES; assert 'orphaned' in _TERMINAL_STATES"
       [ "$status" -eq 0 ]
     }
     ```

  2. Append to `tests/unit/test_rddf_session.py` (from tasks.md §3.2) — assume the existing file already defines `coordinator` and `sessions_file` pytest fixtures:

     ```python
     def test_archive_history_archives_orphaned_and_keeps_active(coordinator, sessions_file):
         orphan_sid = coordinator.create_session(
             kind="stage_plan", owner_opencode_session_id="ses_orphan", goal={}
         )
         data = json.loads(sessions_file.read_text())
         data["sessions"][0]["state"] = "orphaned"
         sessions_file.write_text(json.dumps(data))

         active_sid = coordinator.create_session(
             kind="stage_plan", owner_opencode_session_id="ses_active", goal={}
         )
         assert coordinator.archive_history(keep=0) == 1
         assert [s["session_id"] for s in coordinator.list_sessions()] == [active_sid]

         archive_path = sessions_file.with_suffix(".archive.json")
         archived = json.loads(archive_path.read_text())["sessions"]
         assert [s["session_id"] for s in archived] == [orphan_sid]
     ```

  Both tests must exist before running — the bats file targets the `_TERMINAL_STATES` set, the pytest case exercises `archive_history(keep=0)`.

- [ ] **Step 2: Run tests to verify they fail** — Run the two new test bodies:

  ```bash
  bats tests/unit/test_terminal_states_orphan.bats
  python3 -m pytest tests/unit/test_rddf_session.py::test_archive_history_archives_orphaned_and_keeps_active -q --tb=short
  ```

  Expected: bats reports 3 PASS + 1 FAIL (the `orphaned` membership case fails); pytest reports FAIL on `test_archive_history_archives_orphaned_and_keeps_active` because `_TERMINAL_STATES` does not yet contain `"orphaned"`, so `archive_history(keep=0)` returns 0 instead of 1.

- [ ] **Step 3: Add `orphaned` to `_TERMINAL_STATES`** — Edit `skills/rddf-session/scripts/rddf_session_pkg/_types.py:42`. Replace:

  ```python
  _TERMINAL_STATES = frozenset(("completed", "failed", "abandoned"))
  ```

  with:

  ```python
  _TERMINAL_STATES = frozenset(("completed", "failed", "abandoned", "orphaned"))
  ```

  Verify the edit landed: `grep -n 'completed.*failed.*abandoned.*orphaned' skills/rddf-session/scripts/rddf_session_pkg/_types.py` must return a line.

- [ ] **Step 4: Run the new tests plus the existing rddf-session suite** — Re-run the failing tests from Step 2, plus the full `tests/unit/test_rddf_session.py` to confirm no regressions:

  ```bash
  bats tests/unit/test_terminal_states_orphan.bats
  python3 -m pytest tests/unit/test_rddf_session.py -q --tb=short
  ```

  Expected: bats reports 4 PASS; pytest reports all PASS including `test_archive_history_archives_orphaned_and_keeps_active`.

- [ ] **Step 5: Commit** — Stage the three files; commit with the message from tasks.md §3.5:

  ```bash
  git add tests/unit/test_terminal_states_orphan.bats tests/unit/test_rddf_session.py skills/rddf-session/scripts/rddf_session_pkg/_types.py
  git commit -m "fix(rddf-session): treat orphaned heartbeat-timeout sessions as terminal"
  ```

---

### Task 4: Update documentation

**Files:**
- Modify: `AGENTS.md` (add pitfall #18 under "常见陷阱")
- Modify: `CHANGELOG.md` (add `### Fixed` bullets under `[Unreleased] — v2.1`)

Replaces tasks.md §4.1–§4.3 (3 checkboxes) with TDD 5-step structure. No production code change in this task — the steps use `grep` as the verification (test) instead of `pytest`/`bats`.

- [ ] **Step 1: Write the documentation updates** — Make the two edits in source:

  1. In `AGENTS.md`, append to the numbered "常见陷阱" list (after pitfall 17 or at the end):

     ```markdown
     18. **Scanner state.sh fallback**: `skills/guide/scripts/scan-state.sh` and `guide_entry.sh` first try `$PROJECT_ROOT/skills/_lib/state.sh`, then fall back to `${HOME}/.agents/skills/_lib/state.sh`. If both are missing, a non-blocking stderr warning is printed; stdout and exit code remain unchanged. Do not add symlinks or runtime path resolution.
     ```

  2. In `CHANGELOG.md`, insert under the `### Fixed` (or `### Changed`) section of `[Unreleased] — v2.1`:

     ```markdown
     ### Fixed

     - **Scanner fallback**: `skills/guide/scripts/scan-state.sh` and `skills/guide/scripts/guide_entry.sh` now load `skills/_lib/state.sh` from `$PROJECT_ROOT` first, then fall back to `${HOME}/.agents/skills/_lib/state.sh`, with a non-blocking stderr warning if both are missing.
     - **Orphaned session archival**: `skills/rddf-session/scripts/rddf_session_pkg/_types.py` now includes `"orphaned"` in `_TERMINAL_STATES`, so `archive_history` archives heartbeat-timeout sessions instead of leaving them in `sessions.json`.
     ```

- [ ] **Step 2: Verify `AGENTS.md` contains the new pitfall** — `grep -n "Scanner state.sh fallback" AGENTS.md`. Expected: returns a line number inside the "常见陷阱" list.

- [ ] **Step 3: (Skip — no implementation; this task is docs only)** — Leave blank in the executed run; the production code change already shipped in Tasks 1–3.

- [ ] **Step 4: Verify `CHANGELOG.md` contains both `### Fixed` bullets** — Run both greps from tasks.md §4.2: `grep -n "Scanner fallback" CHANGELOG.md` and `grep -n "Orphaned session archival" CHANGELOG.md`. Expected: each returns a line number inside the `[Unreleased] — v2.1` section.

- [ ] **Step 5: Commit** — Stage both docs; commit with the message from tasks.md §4.3:

  ```bash
  git add AGENTS.md CHANGELOG.md
  git commit -m "docs: document scanner fallback and orphaned terminal state"
  ```

---

### Task 5: Acceptance validation

**Files:**
- Test: `tests/integration/test_scanner_fallback.bats`
- Test: `tests/unit/test_terminal_states_orphan.bats`
- Test: `tests/integration/scan_state.bats`
- Test: `tests/integration/test_guide_scan.bats`
- Test: `tests/unit/test_rddf_session.py` (full file, not just the new case)
- Test: `tests/` (full Python suite)
- Test: OpenSpec strict validation of this change
- Test: OpenSpec status JSON for `isComplete`

Replaces tasks.md §5.1–§5.6 (6 checkboxes). This is the validation gate — no new code, no commit; each step is a verification command from the tasks.md "Validation matrix" table.

- [ ] **Step 1: Run the new bats tests** — `bats tests/integration/test_scanner_fallback.bats tests/unit/test_terminal_states_orphan.bats`. Expected: 10 PASS (6 from `test_scanner_fallback.bats` + 4 from `test_terminal_states_orphan.bats`).

- [ ] **Step 2: Run the existing scan-state regression suite** — `bats tests/integration/scan_state.bats tests/integration/test_guide_scan.bats`. Expected: all PASS, zero modifications (these existed before this change and must still pass).

- [ ] **Step 3: Run the full Python test suite** — `python3 -m pytest tests/ -q --tb=short`. Expected: all PASS (no regressions across the rddf-session unit suite, the new archive test, and any other Python tests).

- [ ] **Step 4: Run the npm bats suite** — `npm test`. Expected: exit 0 (all bats tests under `tests/` pass via the npm wrapper).

- [ ] **Step 5: Validate the OpenSpec change in strict mode and confirm `isComplete`** — Run the two OpenSpec CLI checks:

  ```bash
  openspec validate fix-scanner-fallback-and-orphan-archival --strict
  openspec status --change fix-scanner-fallback-and-orphan-archival --json | jq '.isComplete'
  ```

  Expected: first command exits 0; second command prints `true`.