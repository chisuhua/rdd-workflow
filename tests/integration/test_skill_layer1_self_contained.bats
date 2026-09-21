#!/usr/bin/env bats
# tests/integration/test_skill_layer1_self_contained.bats
# Verify all SKILL.md files have no external docs/ references.

load ../test_helper

bats_require_minimum_version 1.5.0

@test "skill-layer1: no SKILL.md references ../docs/ or ../../docs/" {
  local violations=0
  while IFS= read -r -d '' f; do
    if grep -q '../docs/\|../../docs/' "$f" 2>/dev/null; then
      echo "VIOLATION: $f references external docs/"
      violations=$((violations + 1))
    fi
  done < <(find "$REPO_ROOT/skills" -name 'SKILL.md' -print0)
  [ "$violations" -eq 0 ]
}

@test "skill-layer1: roadmap SKILL.md has no external docs reference" {
  run grep -c '../../docs/' "$REPO_ROOT/skills/roadmap/SKILL.md" 2>/dev/null || true
  [ "$output" -eq 0 ]
}

@test "skill-layer1: rdd-hub-bootstrap SKILL.md has no external docs reference" {
  run grep -c '../../docs/' "$REPO_ROOT/skills/rdd-hub-bootstrap/SKILL.md" 2>/dev/null || true
  [ "$output" -eq 0 ]
}