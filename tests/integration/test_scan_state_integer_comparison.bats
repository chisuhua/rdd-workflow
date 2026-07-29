load ../test_helper

@test "scan_state_integer: scan-state.sh FS_ACTIVE_COUNT uses tr -d after wc -l" {
    run grep -E 'FS_ACTIVE_COUNT=.*wc -l.*tr -d' "$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"
    [ "$status" -eq 0 ]
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
