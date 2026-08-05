load ../test_helper

setup() {
    TEST_REPO="$BATS_TMPDIR/test-quick-finish"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO"
    cd "$TEST_REPO"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git checkout -q -b main
    git commit --allow-empty -q -m "init"
    mkdir -p openspec/changes/alpha
    printf -- '- [ ] update CHANGELOG\n' > openspec/changes/alpha/tasks.md
}

@test "breaking keyword blocks Quick Finish" {
    cd "$TEST_REPO"
    printf -- '- [ ] update CHANGELOG with breaking change note\n' > openspec/changes/alpha/tasks.md
    source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
    run detect_quick_finish "$TEST_REPO" "alpha"
    [ "$status" -eq 0 ]
    [ "$output" = "standard" ]
}

@test "trivial-only tasks allow Quick Finish on clean tree" {
    cd "$TEST_REPO"
    source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
    run detect_quick_finish "$TEST_REPO" "alpha"
    [ "$status" -eq 0 ]
    [ "$output" = "quick_finish" ]
}

@test "manual_blocks blocks Quick Finish" {
    cd "$TEST_REPO"
    printf 'manual_blocks: ["other-change"]\n' > openspec/changes/alpha/roadmap-meta.yaml
    source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
    run detect_quick_finish "$TEST_REPO" "alpha"
    [ "$status" -eq 0 ]
    [ "$output" = "standard" ]
}

@test "empty manual_blocks allows Quick Finish" {
    cd "$TEST_REPO"
    printf 'manual_blocks: []\n' > openspec/changes/alpha/roadmap-meta.yaml
    source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
    run detect_quick_finish "$TEST_REPO" "alpha"
    [ "$status" -eq 0 ]
    [ "$output" = "quick_finish" ]
}