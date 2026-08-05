load ../test_helper

setup() {
    TEST_REPO="$BATS_TMPDIR/test-exec-root"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO"
    cd "$TEST_REPO"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git checkout -q -b main
    git commit --allow-empty -q -m "init"
    mkdir -p openspec/changes/alpha
    printf -- '- [ ] a\n' > openspec/changes/alpha/tasks.md
}

@test "select_worktree.sh honors RDDF_EXECUTION_ROOT pointing into repo" {
    RDDF_EXECUTION_ROOT="$TEST_REPO" \
        run bash -c "source '$PROJECT_ROOT/skills/execute/scripts/change_name.sh' 2>/dev/null; source '$PROJECT_ROOT/skills/execute/scripts/select_worktree.sh'; export RDDF_EXECUTION_ROOT='$TEST_REPO'; auto_detect_worktree_context"
    [[ "$output" != *"请先执行 guide-ship 技能创建 worktree"* ]]
}

@test "select_worktree.sh rejects RDDF_EXECUTION_ROOT outside the repo" {
    OTHER=$(mktemp -d)
    cd "$OTHER" && git init -q && git commit --allow-empty -q -m "other"
    cd "$TEST_REPO"
    RDDF_EXECUTION_ROOT="$OTHER" \
        run bash -c "source '$PROJECT_ROOT/skills/execute/scripts/change_name.sh' 2>/dev/null; source '$PROJECT_ROOT/skills/execute/scripts/select_worktree.sh'; export RDDF_EXECUTION_ROOT='$OTHER'; auto_detect_worktree_context"
    [[ "$output" == *"不在项目仓库内"* ]] || [[ "$output" == *"不在项目仓库"* ]]
}

@test "RDDF_EXECUTION_ROOT re-exported in parent shell after run_ship_phase1" {
    grep -q 'export RDDF_EXECUTION_ROOT' "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
    grep -q 'RDDF_EXECUTION_ROOT=' "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
    # Both branches of the case must be present.
    grep -q 'worktree)' "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
}

@test "execute.md references RDDF_EXECUTION_ROOT contract" {
    grep -q 'RDDF_EXECUTION_ROOT' "$PROJECT_ROOT/skills/execute/SKILL.md"
}