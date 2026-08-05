load ../test_helper

@test "ship_archive.sh calls archive_gate_check (not check_incomplete_tasks)" {
    grep -q 'archive_gate_check' "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"
}

@test "archive.sh::archive_change invokes archive_gate_check" {
    grep -q 'archive_gate_check' "$PROJECT_ROOT/skills/_lib/archive.sh"
}

@test "archive_gate_check returns non-zero when 0 tasks complete" {
    TMP=$(mktemp -d)
    cd "$TMP"
    mkdir -p openspec/changes/foo
    printf -- '- [ ] a\n- [ ] b\n' > openspec/changes/foo/tasks.md
    source "$PROJECT_ROOT/skills/_lib/archive.sh"
    run bash -c "source '$PROJECT_ROOT/skills/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'foo'"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "未实现" ]]
    cd /
    rm -rf "$TMP"
}

@test "archive_gate_check returns 0 when at least 1 task complete" {
    TMP=$(mktemp -d)
    cd "$TMP"
    mkdir -p openspec/changes/foo
    printf -- '- [x] a\n- [ ] b\n' > openspec/changes/foo/tasks.md
    source "$PROJECT_ROOT/skills/_lib/archive.sh"
    run bash -c "source '$PROJECT_ROOT/skills/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'foo'"
    [ "$status" -eq 0 ]
    cd /
    rm -rf "$TMP"
}

@test "FORCE_ARCHIVE_INCOMPLETE=yes bypasses archive_gate_check" {
    TMP=$(mktemp -d)
    cd "$TMP"
    mkdir -p openspec/changes/foo
    printf -- '- [ ] a\n- [ ] b\n' > openspec/changes/foo/tasks.md
    source "$PROJECT_ROOT/skills/_lib/archive.sh"
    FORCE_ARCHIVE_INCOMPLETE=yes run bash -c "source '$PROJECT_ROOT/skills/_lib/archive.sh' && cd '$TMP' && archive_gate_check 'foo'"
    [ "$status" -eq 0 ]
    cd /
    rm -rf "$TMP"
}