load ../test_helper

setup() {
    TEST_REPO="$BATS_TMPDIR/test-ship-plan"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO"
    cd "$TEST_REPO"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git checkout -q -b main
    mkdir -p openspec/changes/alpha .rddf/state
    echo '{}' > .rddf/state/.plan-handoff.json
    echo '{}' > .rddf/state/iteration.json
    git add -A
    git commit -q -m "init"
}

@test "SKIP_PROMETHEUS_PLANNING without QUICK_FINISH fails closed" {
    SKIP_PROMETHEUS_PLANNING=yes \
        run bash -c "PROJECT_ROOT='$TEST_REPO'; CHANGE_NAME='alpha'; source '$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh' >/dev/null 2>&1; generate_implementation_plan '$TEST_REPO' 'alpha' 'lightweight'"
    [ "$status" -ne 0 ]
}

@test "SKIP_PROMETHEUS_PLANNING with QUICK_FINISH_DETECTED writes placeholder" {
    cd "$TEST_REPO"
    SKIP_PROMETHEUS_PLANNING=yes QUICK_FINISH_DETECTED=yes \
        bash -c "PROJECT_ROOT='$TEST_REPO'; CHANGE_NAME='alpha'; source '$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh' >/dev/null 2>&1; generate_implementation_plan '$TEST_REPO' 'alpha' 'lightweight'"
    [ -f "$TEST_REPO/.rddf/plans/alpha.md" ]
}

@test "missing plan without skip flags errors clearly" {
    cd "$TEST_REPO"
    run bash -c "PROJECT_ROOT='$TEST_REPO'; CHANGE_NAME='alpha'; source '$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh' >/dev/null 2>&1; generate_implementation_plan '$TEST_REPO' 'alpha' 'lightweight'"
    [ "$status" -ne 0 ]
}