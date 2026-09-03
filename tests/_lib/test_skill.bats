#!/usr/bin/env bats
# tests/_lib/test_skill.bats
#
# Unit tests for the skill.bash helper. Locks down the parser API
# before the 9 skill-specific integration tests start to depend on it.
#
# Resolution: load_lib skill picks tests/_lib/skill.bash first
# (per tests/test_helper.bash:22-37).
#
# Run: bats tests/_lib/test_skill.bats

load ../test_helper
load_lib skill

# All assertions use real skill files in the worktree's skills/ dir.

@test "skill_field returns top-level name for guide.md" {
  run skill_field skills/guide/SKILL.md name
  [ "$status" -eq 0 ]
  [ "$output" = "guide" ]
}

@test "skill_field returns alias for INSTALL.md" {
  run skill_field skills/INSTALL.md alias
  [ "$status" -eq 0 ]
  [ "$output" = "install" ]
}

@test "skill_meta_field returns semver version for rdd-arch.md" {
  run skill_meta_field skills/rdd-arch/SKILL.md version
  [ "$status" -eq 0 ]
  [[ "$output" =~ ^[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]
}

@test "skill_meta_field returns user-invocable=true for guide.md" {
  run skill_meta_field skills/guide/SKILL.md user-invocable
  [ "$status" -eq 0 ]
  [ "$output" = "true" ]
}

@test "skill_commands returns at least 5 commands for roadmap.md" {
  run skill_commands skills/roadmap/SKILL.md
  [ "$status" -eq 0 ]
  # 5 commands after v2.0.3 phase-gate-report removal: init/status/edit/validate/advance
  [ "${#lines[@]}" -ge 5 ]
}

@test "skill_commands returns sub-skill list for INSTALL.md" {
  # v3.0: INSTALL.md now includes a "包含的子技能" table listing all
  # 12 sub-skills (guide, guide-arch, ..., rdd-workflow-writing-plans).
  # skill_commands extracts the backtick-quoted command identifiers.
  run skill_commands skills/INSTALL.md
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -ge 12 ]
}

@test "skill_has_section returns 0 for status.md '模式 A'" {
  run skill_has_section skills/status/SKILL.md "模式 A"
  [ "$status" -eq 0 ]
}

@test "skill_field exits non-zero for nonexistent file" {
  run skill_field /nonexistent/path/skill.md name
  [ "$status" -ne 0 ]
}
