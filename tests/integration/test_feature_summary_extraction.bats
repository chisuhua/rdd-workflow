#!/usr/bin/env bats
# tests/integration/test_feature_summary_extraction.bats
# Round C Task C1: feature.md summary subcommand extraction.
# Locks refactor in place:
#   1. feature_summary.sh exists with render_feature_summary exported.
#   2. feature.md inline case block removed.
#   3. feature.md sources and calls render_feature_summary.
#   4. render_feature_summary handles missing iteration.json gracefully.

load ../test_helper

@test "feature_summary: helper file exists with render_feature_summary function" {
  [ -f "$REPO_ROOT/skills/_lib/feature_summary.sh" ]
  bash -c "source '$REPO_ROOT/skills/_lib/feature_summary.sh' && declare -f render_feature_summary" | grep -q 'render_feature_summary'
}

@test "feature_summary: feature.md inline case block removed" {
  # The old inline Python heredoc (<<'PYEOF') is gone — dispatcher only has bash
  run grep "<<'PYEOF'" "$REPO_ROOT/skills/feature/SKILL.md"
  [ "$status" -ne 0 ]
  # The old summary heredoc's inline fv.update_iteration_feature_view call is gone
  run grep 'fv\.update_iteration_feature_view' "$REPO_ROOT/skills/feature/SKILL.md"
  [ "$status" -ne 0 ]
}

@test "feature_summary: feature.md sources and calls helper" {
  grep -q 'source.*_lib/feature_summary.sh' "$REPO_ROOT/skills/feature/SKILL.md"
  grep -q 'render_feature_summary' "$REPO_ROOT/skills/feature/SKILL.md"
}

@test "feature_summary: handles missing iteration.json gracefully" {
  local tmpdir
  tmpdir=$(mktemp -d)
  output=$(PYTHONPATH="$REPO_ROOT" PROJECT_ROOT="$tmpdir" bash -c "source '$REPO_ROOT/skills/_lib/feature_summary.sh' && render_feature_summary" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -qE 'guide-plan|iteration'
}