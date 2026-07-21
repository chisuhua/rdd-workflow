load ../test_helper

@test "agent_completion: verify script exists and is executable" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run test -f "$PROJECT_ROOT/skills/guide-ship/scripts/verify-agent-completion.sh"
    [ "$status" -eq 0 ]
}

@test "agent_completion: verify script has 3 contract checks" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    SCRIPT="$PROJECT_ROOT/skills/guide-ship/scripts/verify-agent-completion.sh"
    run grep -c "check_contract_archive" "$SCRIPT"
    [ "$output" -ge 2 ]
    run grep -c "check_contract_iteration" "$SCRIPT"
    [ "$output" -ge 2 ]
    run grep -c "check_contract_worktree" "$SCRIPT"
    [ "$output" -ge 2 ]
}

@test "agent_completion: verify script has auto-fix functions" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    SCRIPT="$PROJECT_ROOT/skills/guide-ship/scripts/verify-agent-completion.sh"
    run grep -c "auto_fix_worktree" "$SCRIPT"
    [ "$output" -ge 1 ]
    run grep -c "auto_fix_iteration" "$SCRIPT"
    [ "$output" -ge 1 ]
}
