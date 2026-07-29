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

@test "ship_quick_finish: run_ship_phase1 mentions Quick Finish when triggered" {
    cat > openspec/changes/test-change/tasks.md << 'EOF'
# Tasks
- [ ] Update proposal-suggestions.md status
EOF
    # Commit tasks.md so the COMMIT GATE passes (check_artifacts_committed
    # requires HEAD:openspec/changes/<name>/.openspec.yaml, so add that too).
    # But check_artifacts_committed checks for uncommitted dirt in change_dir,
    # so we must commit tasks.md. Also need .openspec.yaml in HEAD.
    cat > openspec/changes/test-change/.openspec.yaml << 'EOF'
change: test-change
EOF
    git add openspec/changes/test-change/
    git commit -q -m "add tasks + openspec yaml"

    # Set QUICK_FINISH_SELECTED=A so the quick-finish path returns early,
    # avoiding full worktree/plan execution that requires skill_use etc.
    run bash -c "
        export PROJECT_ROOT='$PROJECT_ROOT'
        export QUICK_FINISH_SELECTED=A
        source '$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh'
        run_ship_phase1 '$TEST_DIR' 'test-change' 2>&1 || true
    "
    [[ "$output" == *"Quick Finish"* ]] || [[ "$output" == *"quick_finish"* ]]
}

@test "ship_quick_finish: smoke regression - ship_plan.sh sources cleanly" {
    # Verify the script can be sourced without syntax errors (it defines
    # functions only; direct execution exits 1 with a guard message).
    run bash -c "source '$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh' 2>&1"
    [ "$status" -eq 0 ]
}

teardown() {
    rm -rf "$TEST_DIR"
}
