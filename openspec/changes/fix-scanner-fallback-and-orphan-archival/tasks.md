## 1. Add scanner fallback to `scan-state.sh`

- [ ] 1.1 Create the failing test `tests/integration/test_scanner_fallback.bats` covering the four local/global `state.sh` presence combinations.

    ```bash
    # tests/integration/test_scanner_fallback.bats
    #!/usr/bin/env bats
    # Matrix regression tests for scanner state.sh fallback (local -> global -> warning).

    load ../test_helper

    _make_state_sh() {
      local target="$1"
      mkdir -p "$(dirname "$target")"
      cat > "$target" <<'EOF'
    check_dirty_key_files() { return 0; }
    detect_approved_inconsistency() { return 0; }
    sweep_stale_suggestions() { return 0; }
    SCANNER_FALLBACK_SOURCE_PATH="${BASH_SOURCE[0]}"
    EOF
    }

    _run_scan_state() {
      local repo="$1"
      bash -c '
        source "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
        scan_state "$1"
        echo "RECOMMEND=$RECOMMEND"
        echo "REASON=$REASON"
      ' _ "$repo"
    }

    setup() {
      repo=$(mktemp -d)
      home=$(mktemp -d)
      git init -q "$repo"
      git -C "$repo" config user.email "t@t"
      git -C "$repo" config user.name "t"
      touch "$repo/init"
      git -C "$repo" add init && git -C "$repo" commit -q -m init
      export HOME="$home"
    }

    teardown() {
      rm -rf "$repo" "$home"
    }

    @test "scanner fallback: local state.sh used when both exist" {
      _make_state_sh "$repo/skills/_lib/state.sh"
      _make_state_sh "$home/.agents/skills/_lib/state.sh"
      local out; out=$(_run_scan_state "$repo")
      echo "$out" | grep -q "$repo/skills/_lib/state.sh"
      echo "$out" | grep -q "RECOMMEND=guide-arch"
    }

    @test "scanner fallback: global state.sh used when local is missing" {
      _make_state_sh "$home/.agents/skills/_lib/state.sh"
      local out; out=$(_run_scan_state "$repo")
      echo "$out" | grep -q "$home/.agents/skills/_lib/state.sh"
      echo "$out" | grep -q "RECOMMEND=guide-arch"
    }

    @test "scanner fallback: warning when both copies are missing" {
      run bash -c 'source "$REPO_ROOT/skills/guide/scripts/scan-state.sh"; scan_state "$1" 2>&1' _ "$repo"
      [ "$status" -eq 0 ]
      [[ "$output" == *"rdd-workflow not installed"* ]]
      [[ "$output" == *"INSTALL.md"* ]]
    }

    @test "scanner fallback: local and global produce identical recommendation" {
      _make_state_sh "$repo/skills/_lib/state.sh"
      local local_out; local_out=$(_run_scan_state "$repo")
      rm "$repo/skills/_lib/state.sh"
      _make_state_sh "$home/.agents/skills/_lib/state.sh"
      local global_out; global_out=$(_run_scan_state "$repo")
      [ "$(echo "$local_out" | grep -E '^(RECOMMEND|REASON)=')" = "$(echo "$global_out" | grep -E '^(RECOMMEND|REASON)=')" ]
    }
    ```

    Verification: `bats tests/integration/test_scanner_fallback.bats` (expected: FAIL, no fallback implemented yet)

- [ ] 1.2 Modify `skills/guide/scripts/scan-state.sh:67` to use the local-then-global fallback loop.

    Replace the existing line:

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

    Verification: `grep -n "rdd-workflow not installed" skills/guide/scripts/scan-state.sh` returns a line number

- [ ] 1.3 Run the scanner fallback tests and confirm all four matrix cases pass.

    Verification: `bats tests/integration/test_scanner_fallback.bats` (expected: 4 PASS)

- [ ] 1.4 Commit the scanner fallback change.

    ```bash
    git add tests/integration/test_scanner_fallback.bats skills/guide/scripts/scan-state.sh
    git commit -m "fix(scanner): local-then-global state.sh fallback with non-blocking warning"
    ```

## 2. Add the same fallback to `guide_entry.sh`

- [ ] 2.1 Modify `skills/guide/scripts/guide_entry.sh:185` with the identical loop.

    Replace the existing line:

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

    Verification: `grep -n "rdd-workflow not installed" skills/guide/scripts/guide_entry.sh` returns a line number

- [ ] 2.2 Append the guide-entry tests to `tests/integration/test_scanner_fallback.bats`.

    ```bash
    # append to tests/integration/test_scanner_fallback.bats
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

    Verification: `bats tests/integration/test_scanner_fallback.bats` (expected: 6 PASS)

- [ ] 2.3 Commit the guide_entry fallback change.

    ```bash
    git add tests/integration/test_scanner_fallback.bats skills/guide/scripts/guide_entry.sh
    git commit -m "fix(guide): same local-then-global state.sh fallback in guide_entry"
    ```

## 3. Add `orphaned` to the rddf-session terminal states

- [ ] 3.1 Create the failing test `tests/unit/test_terminal_states_orphan.bats` asserting the four terminal states.

    ```bash
    # tests/unit/test_terminal_states_orphan.bats
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

    Verification: `bats tests/unit/test_terminal_states_orphan.bats` (expected: FAIL on orphaned)

- [ ] 3.2 Add a failing behavioral test to `tests/unit/test_rddf_session.py` proving `archive_history(keep=0)` archives orphaned sessions while preserving an active session.

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

    Verification: `python3 -m pytest tests/unit/test_rddf_session.py::test_archive_history_archives_orphaned_and_keeps_active -q` (expected: FAIL before `_TERMINAL_STATES` changes)

- [ ] 3.3 Modify `skills/rddf-session/scripts/rddf_session_pkg/_types.py:42` to add `"orphaned"` to `_TERMINAL_STATES`.

    Replace:

    ```python
    _TERMINAL_STATES = frozenset(("completed", "failed", "abandoned"))
    ```

    with:

    ```python
    _TERMINAL_STATES = frozenset(("completed", "failed", "abandoned", "orphaned"))
    ```

    Verification: `grep -n 'completed.*failed.*abandoned.*orphaned' skills/rddf-session/scripts/rddf_session_pkg/_types.py` returns a line

- [ ] 3.4 Run the new terminal-state and archive-history tests plus the existing rddf-session suite.

    ```bash
    bats tests/unit/test_terminal_states_orphan.bats
    python3 -m pytest tests/unit/test_rddf_session.py -q --tb=short
    ```

    Verification: both commands exit 0, including `test_archive_history_archives_orphaned_and_keeps_active`

- [ ] 3.5 Commit the terminal-state change.

    ```bash
    git add tests/unit/test_terminal_states_orphan.bats tests/unit/test_rddf_session.py skills/rddf-session/scripts/rddf_session_pkg/_types.py
    git commit -m "fix(rddf-session): treat orphaned heartbeat-timeout sessions as terminal"
    ```

## 4. Update documentation

- [ ] 4.1 Add a bullet to `AGENTS.md` "常见陷阱" documenting the scanner fallback.

    Insert after pitfall 17 (or at the end of the numbered list):

    ```markdown
    18. **Scanner state.sh fallback**: `skills/guide/scripts/scan-state.sh` and `guide_entry.sh` first try `$PROJECT_ROOT/skills/_lib/state.sh`, then fall back to `${HOME}/.agents/skills/_lib/state.sh`. If both are missing, a non-blocking stderr warning is printed; stdout and exit code remain unchanged. Do not add symlinks or runtime path resolution.
    ```

    Verification: `grep -n "Scanner state.sh fallback" AGENTS.md` returns a line number

- [ ] 4.2 Add a `CHANGELOG.md` entry under `[Unreleased] — v2.1`.

    Insert under the `### Changed` or `### Bug Fixes` section of `[Unreleased] — v2.1`:

    ```markdown
    ### Fixed

    - **Scanner fallback**: `skills/guide/scripts/scan-state.sh` and `skills/guide/scripts/guide_entry.sh` now load `skills/_lib/state.sh` from `$PROJECT_ROOT` first, then fall back to `${HOME}/.agents/skills/_lib/state.sh`, with a non-blocking stderr warning if both are missing.
    - **Orphaned session archival**: `skills/rddf-session/scripts/rddf_session_pkg/_types.py` now includes `"orphaned"` in `_TERMINAL_STATES`, so `archive_history` archives heartbeat-timeout sessions instead of leaving them in `sessions.json`.
    ```

    Verification: `grep -n "Scanner fallback" CHANGELOG.md` and `grep -n "Orphaned session archival" CHANGELOG.md` both return line numbers

- [ ] 4.3 Commit the documentation updates.

    ```bash
    git add AGENTS.md CHANGELOG.md
    git commit -m "docs: document scanner fallback and orphaned terminal state"
    ```

## 5. Acceptance validation

- [ ] 5.1 Run the new bats tests.

    Verification: `bats tests/integration/test_scanner_fallback.bats tests/unit/test_terminal_states_orphan.bats` (expected: 10 PASS)

- [ ] 5.2 Run the existing scan-state regression suite.

    Verification: `bats tests/integration/scan_state.bats tests/integration/test_guide_scan.bats` (expected: all PASS, zero modifications)

- [ ] 5.3 Run the full Python test suite to confirm no regressions.

    Verification: `python3 -m pytest tests/ -q --tb=short` (expected: all PASS)

- [ ] 5.4 Run the npm bats suite.

    Verification: `npm test` (expected: exit 0)

- [ ] 5.5 Validate the OpenSpec change in strict mode.

    Verification: `openspec validate fix-scanner-fallback-and-orphan-archival --strict` (expected: PASS)

- [ ] 5.6 Confirm the change status is complete.

    Verification: `openspec status --change fix-scanner-fallback-and-orphan-archival --json | jq '.isComplete'` (expected: `true`)

### Validation matrix

| Criterion | Command | Expected result |
|------------|---------|-----------------|
| Scanner fallback matrix | `bats tests/integration/test_scanner_fallback.bats` | 6 PASS |
| Terminal states | `bats tests/unit/test_terminal_states_orphan.bats` | 4 PASS |
| Orphan archive behavior | `python3 -m pytest tests/unit/test_rddf_session.py::test_archive_history_archives_orphaned_and_keeps_active -q` | PASS |
| Existing scan-state regression | `bats tests/integration/scan_state.bats` | PASS |
| Existing guide scan regression | `bats tests/integration/test_guide_scan.bats` | PASS |
| rddf-session unit regression | `python3 -m pytest tests/unit/test_rddf_session.py -q` | PASS |
| Full Python suite | `python3 -m pytest tests/ -q --tb=short` | PASS |
| npm bats suite | `npm test` | exit 0 |
| OpenSpec strict validation | `openspec validate fix-scanner-fallback-and-orphan-archival --strict` | PASS |
| OpenSpec status complete | `openspec status --change fix-scanner-fallback-and-orphan-archival --json \| jq '.isComplete'` | `true` |
