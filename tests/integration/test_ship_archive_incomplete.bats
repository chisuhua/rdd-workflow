load ../test_helper

# This file previously referenced undefined helpers (check_incomplete_tasks
# and append_incomplete_to_suggestions) that never existed in archive.sh.
# It now tests the real archive_gate_check semantics across both modes.

@test "archive: gate blocks change with no completed tasks" {
    TMP="$BATS_TMPDIR/test-arch"
    mkdir -p "$TMP/openspec/changes/incomplete"
    printf -- '- [ ] a\n- [ ] b\n' > "$TMP/openspec/changes/incomplete/tasks.md"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'incomplete'"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "未实现" ]]
}

@test "archive: gate passes when all tasks complete" {
    TMP="$BATS_TMPDIR/test-arch2"
    mkdir -p "$TMP/openspec/changes/complete"
    printf -- '- [x] a\n- [x] b\n' > "$TMP/openspec/changes/complete/tasks.md"
    run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'complete'"
    [ "$status" -eq 0 ]
}

@test "archive: FORCE_ARCHIVE_INCOMPLETE bypasses gate" {
    TMP="$BATS_TMPDIR/test-arch3"
    mkdir -p "$TMP/openspec/changes/force"
    printf -- '- [ ] a\n- [ ] b\n' > "$TMP/openspec/changes/force/tasks.md"
    FORCE_ARCHIVE_INCOMPLETE=yes \
        run bash -c "source '$PROJECT_ROOT/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'force'"
    [ "$status" -eq 0 ]
}