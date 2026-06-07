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
  run skill_field skills/guide.md name
  [ "$status" -eq 0 ]
  [ "$output" = "guide" ]
}

@test "skill_field returns alias for INSTALL.md" {
  run skill_field skills/INSTALL.md alias
  [ "$status" -eq 0 ]
  [ "$output" = "install" ]
}

@test "skill_meta_field returns semver version for guide-spec.md" {
  run skill_meta_field skills/guide-spec.md version
  [ "$status" -eq 0 ]
  [[ "$output" =~ ^[0-9]+\.[0-9]+$ ]]
}

@test "skill_meta_field returns user-invocable=true for guide.md" {
  run skill_meta_field skills/guide.md user-invocable
  [ "$status" -eq 0 ]
  [ "$output" = "true" ]
}

@test "skill_commands returns at least 6 commands for roadmap.md" {
  run skill_commands skills/roadmap.md
  [ "$status" -eq 0 ]
  # 6 commands: init/status/edit/validate/advance/gate-report
  [ "${#lines[@]}" -ge 6 ]
}

@test "skill_commands returns 0 lines for INSTALL.md" {
  run skill_commands skills/INSTALL.md
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 0 ]
}

@test "skill_has_section returns 0 for status.md '模式 A'" {
  run skill_has_section skills/status.md "模式 A"
  [ "$status" -eq 0 ]
}

@test "skill_field exits non-zero for nonexistent file" {
  run skill_field /nonexistent/path/skill.md name
  [ "$status" -ne 0 ]
}
