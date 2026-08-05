load ../test_helper

@test "select_worktree.sh honors RDDF_EXECUTION_ROOT" {
    TMP=$(mktemp -d)
    mkdir -p "$TMP/openspec/changes/alpha"
    cd "$TMP"
    RDDF_EXECUTION_ROOT="$TMP" \
        run bash -c "source '$PROJECT_ROOT/skills/execute/scripts/change_name.sh' 2>/dev/null; source '$PROJECT_ROOT/skills/execute/scripts/select_worktree.sh'; export RDDF_EXECUTION_ROOT='$TMP'; auto_detect_worktree_context"
    # Either it succeeds or fails with a sane error about worktree/branch — but it must NOT print
    # the 'no worktree created' guidance that would happen if RDDF_EXECUTION_ROOT were ignored.
    [[ "$output" != *"请先执行 guide-ship 技能创建 worktree"* ]]
}

@test "RDDF_EXECUTION_ROOT is exported by setup_execution_workspace" {
    grep -q 'export RDDF_EXECUTION_ROOT' "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
}

@test "execute.md references RDDF_EXECUTION_ROOT contract" {
    grep -q 'RDDF_EXECUTION_ROOT' "$PROJECT_ROOT/skills/execute/SKILL.md"
}