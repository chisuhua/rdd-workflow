#!/usr/bin/env bats
# test_guide_ship_phase1_project_yaml.bats — guide-ship Phase 1 Step 1.5
# reads .rddf/project.yaml to detect git.openspec_tracked override
#
# Per complete-project-yaml-config-gaps M3 Task 3.1 + spec.md
# 'guide-ship-phase-1-detect-lightweight' requirement: when project.yaml
# sets git.openspec_tracked: false, guide-ship Phase 1 must force
# lightweight mode BEFORE worktree creation.
load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
}

# Per AGENTS.md: bats test naming format is "模块: 场景描述"

@test "guide-ship: SKILL.md Phase 1 contains Step 1.5" {
    grep -q "Step 1.5" "$REPO_ROOT/skills/guide-ship/SKILL.md"
}

@test "guide-ship: Step 1.5 reads project.yaml git.openspec_tracked" {
    # Step 1.5 must invoke project_config.sh or similar to read project.yaml
    # The grep is permissive: matches any reference to openspec_tracked
    # detection in the SKILL.md body.
    awk '/Step 1\.5/,/^## /' "$REPO_ROOT/skills/guide-ship/SKILL.md" | grep -q "openspec_tracked"
}

@test "guide-ship: Step 1.5 exports RDDF_EXECUTION_MODE=lightweight on openspec_tracked=false" {
    awk '/Step 1\.5/,/^## /' "$REPO_ROOT/skills/guide-ship/SKILL.md" | grep -q "RDDF_EXECUTION_MODE.*lightweight"
}

@test "guide-ship: Step 1.5 prints lightweight hint before worktree creation" {
    awk '/Step 1\.5/,/^## /' "$REPO_ROOT/skills/guide-ship/SKILL.md" | grep -q "强制轻量模式"
}
