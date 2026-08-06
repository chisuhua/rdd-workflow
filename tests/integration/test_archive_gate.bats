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