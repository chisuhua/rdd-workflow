load ../test_helper

@test "archive-gate: blocks change with 0 completed tasks" {
    TMP="$BATS_TMPDIR/test-gate"
    mkdir -p "$TMP/openspec/changes/test-zero"
    printf -- '- [ ] Task 1\n- [ ] Task 2\n' > "$TMP/openspec/changes/test-zero/tasks.md"
    source "$PROJECT_ROOT/_lib/archive.sh"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'test-zero'"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "未实现" ]]
}

@test "archive-gate: passes change with completed tasks" {
    TMP="$BATS_TMPDIR/test-gate2"
    mkdir -p "$TMP/openspec/changes/test-done"
    printf -- '- [x] Task 1\n- [x] Task 2\n' > "$TMP/openspec/changes/test-done/tasks.md"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'test-done'"
    [ "$status" -eq 0 ]
}

@test "archive-gate: skips with FORCE_ARCHIVE_INCOMPLETE" {
    TMP="$BATS_TMPDIR/test-gate3"
    mkdir -p "$TMP/openspec/changes/test-force"
    printf -- '- [ ] Task 1\n' > "$TMP/openspec/changes/test-force/tasks.md"
    FORCE_ARCHIVE_INCOMPLETE=yes \
        run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'test-force'"
    [ "$status" -eq 0 ]
}

@test "archive-gate: blocks when tasks.md is missing (no fail-open)" {
    TMP="$BATS_TMPDIR/test-gate4"
    mkdir -p "$TMP/openspec/changes/test-missing"
    source "$PROJECT_ROOT/_lib/archive.sh"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'test-missing'"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "缺失" ]]
}

@test "archive-gate: reads tasks.md from explicit tasks_root (worktree path)" {
    # Simulate worktree path: tasks live at <wt>/openspec/changes/<name>/tasks.md
    # but the main repo openspec/changes/<name>/ doesn't exist.
    WT="$BATS_TMPDIR/wt-gate"
    MAIN="$BATS_TMPDIR/main-gate"
    mkdir -p "$WT/openspec/changes/worktree-change"
    printf -- '- [x] Done in worktree\n' > "$WT/openspec/changes/worktree-change/tasks.md"
    # main repo does NOT have openspec/changes/worktree-change
    source "$PROJECT_ROOT/_lib/archive.sh"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && archive_gate_check 'worktree-change' '$WT'"
    [ "$status" -eq 0 ]
}

@test "archive-gate: warns when change was previously archived (default WARN, exit 0)" {
    TMP="$BATS_TMPDIR/test-gate-rerun"
    mkdir -p "$TMP/openspec/changes/re-run-change"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/re-run-change/tasks.md"
    # Pre-existing archive entry (simulates prior rdd-builder P3 run)
    mkdir -p "$TMP/openspec/changes/archive/2026-09-21-re-run-change"
    touch "$TMP/openspec/changes/archive/2026-09-21-re-run-change/proposal.md"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 're-run-change'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "already archived" ]]
    [[ "$output" =~ "2026-09-21-re-run-change" ]]
}

@test "archive-gate: blocks re-archive when RDDF_REQUIRE_ARCHIVE_UNIQUE=yes" {
    TMP="$BATS_TMPDIR/test-gate-unique"
    mkdir -p "$TMP/openspec/changes/uniq-change"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/uniq-change/tasks.md"
    mkdir -p "$TMP/openspec/changes/archive/2026-09-15-uniq-change"
    touch "$TMP/openspec/changes/archive/2026-09-15-uniq-change/proposal.md"
    RDDF_REQUIRE_ARCHIVE_UNIQUE=yes \
        run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'uniq-change'"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "already archived" ]]
    [[ "$output" =~ "RDDF_REQUIRE_ARCHIVE_UNIQUE" ]]
}

@test "archive-gate: re-archive guard does not match different change names" {
    TMP="$BATS_TMPDIR/test-gate-nomatch"
    mkdir -p "$TMP/openspec/changes/fresh-change"
    printf -- '- [x] Task 1\n' > "$TMP/openspec/changes/fresh-change/tasks.md"
    # Pre-existing archive entry for a DIFFERENT change name
    mkdir -p "$TMP/openspec/changes/archive/2026-09-10-other-change"
    touch "$TMP/openspec/changes/archive/2026-09-10-other-change/proposal.md"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'fresh-change'"
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "already archived" ]]
}