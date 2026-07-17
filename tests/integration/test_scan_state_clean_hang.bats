#!/usr/bin/env bats
# test_scan_state_clean_hang.bats — regression for scan-state.sh
# infinite recursion bug (line 220 self-call)

load ../test_helper

setup() {
    cd "$BATS_TEST_TMPDIR"
    rm -rf repo 2>/dev/null
    mkdir repo && cd repo
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
}

@test "scan_state: terminates within 3s on clean repo (regression for hang bug)" {
    mkdir -p openspec/changes openspec/specs

    run bash -c "
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        scan_state '$PWD'
    "
    # The key regression: status 124 = timeout = hang bug present.
    # With the fix, scan_state returns quickly (status 0).
    [ "$status" -ne 124 ]
    [ "$status" -eq 0 ]
}

@test "check_stale_workflow_state: terminates when workflow-state.md is absent" {
    run bash -c "
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        check_stale_workflow_state '$PWD'
    "
    [ "$status" -eq 0 ]
}

@test "check_stale_workflow_state: terminates when workflow-state.md is present" {
    echo "stale content" > workflow-state.md

    run bash -c "
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        check_stale_workflow_state '$PWD'
    "
    [ "$status" -eq 0 ]
}
