#!/usr/bin/env bats
# tests/integration/test_feature_status_extraction.bats
# Round C Task C1: feature.md status subcommand extraction.
# Locks refactor in place:
#   1. feature_status.sh exists with render_feature_status exported.
#   2. feature.md inline status block removed.
#   3. feature.md sources and calls render_feature_status.
#   4. render_feature_status handles missing iteration.json gracefully.

load ../test_helper

@test "feature_status: helper file exists with render_feature_status function" {
  [ -f "$REPO_ROOT/skills/_lib/feature_status.sh" ]
  bash -c "source '$REPO_ROOT/skills/_lib/feature_status.sh' && declare -f render_feature_status" | grep -q 'render_feature_status'
}

@test "feature_status: feature.md inline status block removed" {
  # The old inline python3 heredoc (python3 - "$TARGET_NAME" <<'PYEOF') is gone
  run grep 'python3 -.*PYEOF' "$REPO_ROOT/skills/feature.md"
  [ "$status" -ne 0 ]
  # The old status heredoc's "all_changes" variable name — gone
  run grep 'all_changes = ' "$REPO_ROOT/skills/feature.md"
  [ "$status" -ne 0 ]
}

@test "feature_status: feature.md sources and calls helper" {
  grep -q 'source.*_lib/feature_status.sh' "$REPO_ROOT/skills/feature.md"
  grep -q 'render_feature_status' "$REPO_ROOT/skills/feature.md"
}

@test "feature_status: handles missing iteration.json gracefully" {
  local tmpdir
  tmpdir=$(mktemp -d)
  output=$(PYTHONPATH="$REPO_ROOT" PROJECT_ROOT="$tmpdir" bash -c "source '$REPO_ROOT/skills/_lib/feature_status.sh' && render_feature_status nonexistent" 2>&1 || true)
  rm -rf "$tmpdir"
  echo "$output" | grep -qE 'guide-plan|iteration'
}