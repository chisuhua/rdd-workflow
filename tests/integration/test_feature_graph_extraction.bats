#!/usr/bin/env bats
# tests/integration/test_feature_graph_extraction.bats
# Round C Task C1: feature.md graph subcommand extraction.
# Locks refactor in place:
#   1. feature_graph.sh exists with render_feature_graph exported.
#   2. feature.md inline graph block removed.
#   3. feature.md sources and calls render_feature_graph.
#   4. render_feature_graph handles missing iteration.json gracefully.

load ../test_helper

@test "feature_graph: helper file exists with render_feature_graph function" {
  [ -f "$REPO_ROOT/skills/_lib/feature_graph.sh" ]
  bash -c "source '$REPO_ROOT/skills/_lib/feature_graph.sh' && declare -f render_feature_graph" | grep -q 'render_feature_graph'
}

@test "feature_graph: feature.md inline graph block removed" {
  # The old graph heredoc printed mermaid via fv.render_mermaid — should be gone
  run grep 'fv\.render_mermaid' "$REPO_ROOT/skills/feature.md"
  [ "$status" -ne 0 ]
  # The __cycle_warning__ check from the old inline block should be gone
  run grep '__cycle_warning__' "$REPO_ROOT/skills/feature.md"
  [ "$status" -ne 0 ]
}

@test "feature_graph: feature.md sources and calls helper" {
  grep -q 'source.*_lib/feature_graph.sh' "$REPO_ROOT/skills/feature.md"
  grep -q 'render_feature_graph' "$REPO_ROOT/skills/feature.md"
}

@test "feature_graph: handles missing iteration.json gracefully" {
  local tmpdir
  tmpdir=$(mktemp -d)
  output=$(PYTHONPATH="$REPO_ROOT" PROJECT_ROOT="$tmpdir" bash -c "source '$REPO_ROOT/skills/_lib/feature_graph.sh' && render_feature_graph" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -qE 'guide-plan|iteration'
}