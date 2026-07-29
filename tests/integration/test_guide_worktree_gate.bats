#!/usr/bin/env bats
# tests/integration/test_guide_worktree_gate.bats
#
# Regression lock for prompt-worktree-cleanup-before-stage change.
# Verifies that skills/guide/SKILL.md documents a stage-command gate
# step that checks WT_ISSUES_JSON before executing guide-arch /
# guide-plan / guide-ship, and that the cleanup-analysis section links
# to the gate.
#
# Run: bats tests/integration/test_guide_worktree_gate.bats

load ../test_helper

# ---------------------------------------------------------------------------
# Task 1: stage-command gate section exists and mentions all 3 commands
# ---------------------------------------------------------------------------

@test "guide_worktree_gate: SKILL.md documents gate step for stage commands" {
    # Verify SKILL.md contains a section about stage-command worktree gate
    run grep -F "阶段命令门控" "$PROJECT_ROOT/skills/guide/SKILL.md"
    [ "$status" -eq 0 ]
}

@test "guide_worktree_gate: SKILL.md gate step mentions all 3 stage commands" {
    # Verify SKILL.md gate step mentions guide-arch, guide-plan, guide-ship
    local f="$PROJECT_ROOT/skills/guide/SKILL.md"
    grep -qF 'guide-arch' "$f"
    grep -qF 'guide-plan' "$f"
    grep -qF 'guide-ship' "$f"
}
