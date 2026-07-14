#!/usr/bin/env bats
# tests/integration/test_roadmap_skill.bats
#
# Structural / metadata coverage for skills/roadmap.md.
# Locks the frontmatter, the 6 declared commands (init/status/edit/
# validate/advance/gate-report), the _lib/state.sh dependency, and
# the ROADMAP_PHASE_COUNT env var (P1-5).
#
# Run: bats tests/integration/test_roadmap_skill.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/roadmap.md"
}

@test "roadmap_skill has correct frontmatter" {
  [ "$(skill_field "$f" name)" = "roadmap" ]
}

@test "roadmap_skill declares 5 commands (v2.0.3: gate-report removed)" {
  run skill_commands "$f"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -ge 5 ]
  # Each line must be one of the 5 known commands (gate-report removed in v2.0.3)
  for cmd in "${lines[@]}"; do
    case "$cmd" in
      init|status|edit|validate|advance) ;;
      *) echo "unexpected command: $cmd" >&2; return 1 ;;
    esac
  done
}

@test "roadmap_skill sources _lib/state.sh" {
  grep -q '_lib/state\.sh' "$f"
}

@test "roadmap_skill ROADMAP_PHASE_COUNT env var is honored" {
  grep -q 'ROADMAP_PHASE_COUNT' "$f"
}
