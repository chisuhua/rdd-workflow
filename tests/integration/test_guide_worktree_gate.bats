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

# ---------------------------------------------------------------------------
# Task 2: cleanup-analysis section links to the stage-command gate
# ---------------------------------------------------------------------------

@test "guide_worktree_gate: cleanup-analysis section mentions stage gate linkage" {
    # The cleanup analysis section should reference the stage-command gate
    # and reuse WT_ISSUES_JSON data.
    local f="$PROJECT_ROOT/skills/guide/SKILL.md"
    # Extract the "### 工作树清理分析" section body (until next ### )
    local section
    section=$(awk '/^### 工作树清理分析/{flag=1;next} /^### /{flag=0} flag' "$f")
    [ -n "$section" ]
    # Must mention the gate linkage
    echo "$section" | grep -qF '阶段命令门控'
    # Must mention WT_ISSUES_JSON
    echo "$section" | grep -qF 'WT_ISSUES_JSON'
}

# ---------------------------------------------------------------------------
# Task 3: E2E - gate applies to all 3 stage commands + smoke regression
# ---------------------------------------------------------------------------

@test "guide_worktree_gate: SKILL.md has content for all 3 stage commands with gate" {
    # Verify gate applies to all 3 stages by checking each command is present
    # in the same file that documents the gate step.
    local f="$PROJECT_ROOT/skills/guide/SKILL.md"
    # Gate section must exist first
    grep -qF '阶段命令门控' "$f"
    # All 3 stage commands must appear in the file
    local total=0
    for cmd in guide-arch guide-plan guide-ship; do
        if grep -qF "$cmd" "$f"; then
            total=$((total + 1))
        fi
    done
    [ "$total" -eq 3 ]
}

@test "guide_worktree_gate: gate section precedes 执行选择 dispatch" {
    # The gate section must appear BEFORE the 执行选择 section so the
    # AI reads the gate instruction before dispatching stage commands.
    local f="$PROJECT_ROOT/skills/guide/SKILL.md"
    local gate_line dispatch_line
    gate_line=$(grep -nF '### 阶段命令门控' "$f" | head -1 | cut -d: -f1)
    dispatch_line=$(grep -nF '### 执行选择' "$f" | head -1 | cut -d: -f1)
    [ -n "$gate_line" ]
    [ -n "$dispatch_line" ]
    [ "$gate_line" -lt "$dispatch_line" ]
}

@test "guide_worktree_gate: smoke regression - SKILL.md still parseable" {
    # Ensure SKILL.md is still valid markdown structure with frontmatter.
    local f="$PROJECT_ROOT/skills/guide/SKILL.md"
    run head -1 "$f"
    [ "$status" -eq 0 ]
    [[ "$output" == *"---"* ]]
}

@test "guide_worktree_gate: smoke regression - guide_skill tests still pass" {
    # Ensure our doc edits did not break the existing guide skill metadata
    # test suite (frontmatter / structure locks).
    run bats tests/integration/test_guide_skill.bats
    [ "$status" -eq 0 ]
}
