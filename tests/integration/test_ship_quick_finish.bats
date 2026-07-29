load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init -q
    git config user.email "t@t.com"
    git config user.name "T"
    mkdir -p openspec/changes/test-change
    touch openspec/changes/test-change/proposal.md
    git add openspec/changes/test-change/
    git commit -q -m "init"
}

# Source ship_plan.sh functions
source_ship_plan() {
    source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
}

@test "ship_quick_finish: 1 trivial task triggers quick_finish" {
    cat > openspec/changes/test-change/tasks.md << 'EOF'
# Tasks
- [ ] Update proposal-suggestions.md status
EOF
    source_ship_plan
    result=$(detect_quick_finish "$TEST_DIR" "test-change")
    [ "$result" = "quick_finish" ]
}

@test "ship_quick_finish: 2 trivial tasks triggers quick_finish" {
    cat > openspec/changes/test-change/tasks.md << 'EOF'
# Tasks
- [ ] Update proposal-suggestions.md status
- [ ] Update changelog with notes
EOF
    source_ship_plan
    result=$(detect_quick_finish "$TEST_DIR" "test-change")
    [ "$result" = "quick_finish" ]
}

@test "ship_quick_finish: 3 trivial tasks returns standard" {
    cat > openspec/changes/test-change/tasks.md << 'EOF'
# Tasks
- [ ] Update proposal-suggestions.md
- [ ] Update changelog
- [ ] Update README note
EOF
    source_ship_plan
    result=$(detect_quick_finish "$TEST_DIR" "test-change")
    [ "$result" = "standard" ]
}

@test "ship_quick_finish: non-trivial task returns standard" {
    cat > openspec/changes/test-change/tasks.md << 'EOF'
# Tasks
- [ ] Implement new feature logic
EOF
    source_ship_plan
    result=$(detect_quick_finish "$TEST_DIR" "test-change")
    [ "$result" = "standard" ]
}

@test "ship_quick_finish: missing tasks.md returns no_tasks and exit 1" {
    rm -f openspec/changes/test-change/tasks.md
    source_ship_plan
    run detect_quick_finish "$TEST_DIR" "test-change"
    [ "$status" -eq 1 ]
    [ "$output" = "no_tasks" ]
}

teardown() {
    rm -rf "$TEST_DIR"
}
