#!/usr/bin/env bats
# tests/integration/test_feature_order_extraction.bats
# Round C Task C1: feature.md order subcommand extraction.
# Locks refactor in place:
#   1. feature_order.sh exists with render_feature_order exported.
#   2. feature.md inline order block removed.
#   3. feature.md sources and calls render_feature_order.
#   4. render_feature_order handles missing iteration.json gracefully.

load ../test_helper

@test "feature_order: helper file exists with render_feature_order function" {
  [ -f "$REPO_ROOT/skills/_lib/feature_order.sh" ]
  bash -c "source '$REPO_ROOT/skills/_lib/feature_order.sh' && declare -f render_feature_order" | grep -q 'render_feature_order'
}

@test "feature_order: feature.md inline order block removed" {
  # The old order heredoc printed "Recommended execution order" — gone
  run grep 'Recommended execution order' "$REPO_ROOT/skills/feature/SKILL.md"
  [ "$status" -ne 0 ]
  # The old execution_order key reference — gone
  run grep 'execution_order' "$REPO_ROOT/skills/feature/SKILL.md"
  [ "$status" -ne 0 ]
}

@test "feature_order: feature.md sources and calls helper" {
  grep -q 'source.*_lib/feature_order.sh' "$REPO_ROOT/skills/feature/SKILL.md"
  grep -q 'render_feature_order' "$REPO_ROOT/skills/feature/SKILL.md"
}

@test "feature_order: handles missing iteration.json gracefully" {
  local tmpdir
  tmpdir=$(mktemp -d)
  output=$(PYTHONPATH="$REPO_ROOT" PROJECT_ROOT="$tmpdir" bash -c "source '$REPO_ROOT/skills/_lib/feature_order.sh' && render_feature_order" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -qE 'guide-plan|iteration'
}