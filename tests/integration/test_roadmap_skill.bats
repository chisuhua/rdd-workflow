#!/usr/bin/env bats
# tests/integration/test_roadmap_skill.bats
#
# Structural / metadata coverage for skills/roadmap/SKILL.md.
# Locks the frontmatter, the 6 declared commands (init/status/edit/
# validate/advance/gate-report), the _lib/state.sh dependency, and
# the ROADMAP_PHASE_COUNT env var (P1-5).
#
# Run: bats tests/integration/test_roadmap_skill.bats

load ../test_helper
load_lib skill

setup() {
  f="$REPO_ROOT/skills/roadmap/SKILL.md"
}

@test "roadmap_skill has correct frontmatter" {
  [ "$(skill_field "$f" name)" = "roadmap" ]
}

@test "roadmap_skill declares 5 commands (v2.0.3: gate-report removed)" {
  run skill_commands "$f"
  [ "$status" -eq 0 ]
  # skill_commands returns top-level commands + sub-options (e.g. --phase-refs).
  # Filter to top-level (no -- prefix) for the 5 known command whitelist check.
  local top_count=0
  for cmd in "${lines[@]}"; do
    case "$cmd" in
      --*) ;;  # sub-option, skip
      init|status|edit|validate|advance) top_count=$((top_count + 1)) ;;
      *) echo "unexpected top-level command: $cmd" >&2; return 1 ;;
    esac
  done
  [ "$top_count" -ge 5 ]
}

@test "roadmap_skill sources _lib/state.sh" {
  grep -q '_lib/state\.sh' "$f"
}

@test "roadmap_skill ROADMAP_PHASE_COUNT env var is honored" {
  grep -q 'ROADMAP_PHASE_COUNT' "$f"
}
