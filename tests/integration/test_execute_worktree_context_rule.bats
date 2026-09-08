#!/usr/bin/env bats
# Integration tests for execute skill's worktree context rule
# (regression of test_worktree_context_rule_docs.py executed rule).
#
# Per AGENTS.md: execute skill must document worktree context requirements.
#
# Note (2026-09-08): the v3 "COMMIT GATE before worktree creation" @test was
# removed — v4 execute runs inside an existing worktree (set up by rdd-builder
# P2), so the "before worktree creation" constraint no longer applies.
# Worktree commit semantics are now enforced by rdd-builder's archive.sh
# check_worktree_commits gate, not by the execute skill's docs.

load ../test_helper

@test "execute: SKILL.md contains worktree_context rule" {
    [ -f "$REPO_ROOT/skills/execute/SKILL.md" ]
    grep -q "worktree" "$REPO_ROOT/skills/execute/SKILL.md"
}
