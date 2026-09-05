#!/usr/bin/env bats
# Integration tests for execute skill's worktree context rule
# (regression of test_worktree_context_rule_docs.py executed rule).
#
# Per AGENTS.md: execute skill must document worktree context requirements.

load ../test_helper

@test "execute: SKILL.md contains worktree_context rule" {
    [ -f "$REPO_ROOT/skills/execute/SKILL.md" ]
    grep -q "worktree" "$REPO_ROOT/skills/execute/SKILL.md"
}

@test "execute: SKILL.md documents COMMIT GATE before worktree creation" {
    [ -f "$REPO_ROOT/skills/execute/SKILL.md" ]
    grep -qiE "commit gate|commit.*first|before.*worktree" "$REPO_ROOT/skills/execute/SKILL.md"
}
