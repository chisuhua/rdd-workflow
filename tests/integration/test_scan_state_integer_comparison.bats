load ../test_helper

@test "scan_state_integer: scan-state.sh FS_ACTIVE_COUNT is normalized to a bare integer" {
    # The count must be a clean integer (no trailing newline / whitespace),
    # otherwise bash arithmetic comparisons break. The value is produced by
    # the `_count_active_changes` helper, which normalizes with
    # `wc -l | tr -d '[:space:]'`.
    run grep -E "wc -l.*tr -d" "$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"
    [ "$status" -eq 0 ]

    # Behavioural check: the helper returns a bare integer and excludes the
    # `archive/` directory exactly (a change named `xxx-archive` still counts).
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/openspec/changes/add-x" \
             "$TEST_DIR/openspec/changes/archive" \
             "$TEST_DIR/openspec/changes/keep-archive"
    run bash -c "
        source '$PROJECT_ROOT/skills/guide/scripts/scan-state.sh'
        _count_active_changes '$TEST_DIR'
    "
    [ "$status" -eq 0 ]
    [ "$output" = "2" ]
    rm -rf "$TEST_DIR"
}

@test "scan_state_integer: scan-state.sh DETACHED uses tr -d after wc -l" {
    run grep -E 'DETACHED=.*wc -l.*tr -d' "$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"
    [ "$status" -eq 0 ]
}

@test "scan_state_integer: empty repo scan_state runs without integer errors" {
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init -q
    git config user.email "t@t.com"
    git config user.name "T"
    touch roadmap.md
    mkdir -p openspec/changes/archive

    # Source scan_state and check no integer expression errors
    run bash -c "
        cd $TEST_DIR
        source $PROJECT_ROOT/skills/guide/scripts/scan-state.sh
        scan_state 2>&1 || true
    "
    [[ "$output" != *"integer expression expected"* ]]
    rm -rf "$TEST_DIR"
}
