#!/usr/bin/env bats
# tests/integration/test_guide_ship_line_count.bats
# P3-2 final check: guide-ship.md should be ≤ 850 lines after extraction
# (was 1361). This guards against future inline-script regression.
#
# Plan target was ≤750; actual post-extraction is 842 due to small estimation
# drift. The remaining ~50-line bash block (Phase 2 execute progress reader)
# is identified as future extraction opportunity (P3-3 candidate).

load ../test_helper

@test "guide-ship.md is ≤ 850 lines after extraction (was 1361)" {
  local line_count
  line_count=$(wc -l < "$REPO_ROOT/skills/guide-ship.md")
  [ "$line_count" -le 850 ]
}

@test "guide-ship.md line reduction ≥ 500 lines from baseline (1361)" {
  # Sanity check: extraction must reduce by at least 500 lines.
  local line_count
  line_count=$(wc -l < "$REPO_ROOT/skills/guide-ship.md")
  [ "$((1361 - line_count))" -ge 500 ]
}

@test "guide-ship.md wires all 3 extracted helpers" {
  [ -f "$REPO_ROOT/skills/guide-ship.md" ]
  grep -q 'ship_plan.sh' "$REPO_ROOT/skills/guide-ship.md"
  grep -q 'ship_review.sh' "$REPO_ROOT/skills/guide-ship.md"
  grep -q 'ship_archive.sh' "$REPO_ROOT/skills/guide-ship.md"
}

@test "all 3 _lib/ship_*.sh helpers exist" {
  [ -f "$REPO_ROOT/skills/_lib/ship_plan.sh" ]
  [ -f "$REPO_ROOT/skills/_lib/ship_review.sh" ]
  [ -f "$REPO_ROOT/skills/_lib/ship_archive.sh" ]
}