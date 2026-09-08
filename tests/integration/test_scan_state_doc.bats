#!/usr/bin/env bats
# scan_state() is documented to export only RECOMMEND + REASON.
# Lock: 1) doc comment lists exactly the exported variables,
#       2) guide.md path-count comment matches scan-state.sh count.
#
# NOTE: scan-state.sh moved from _lib/ to skills/guide/scripts/ in
# Phase 2 (ADR-0021). Tests updated to reference the new path.

load ../test_helper

@test "scan-state.sh header lists EXPORTED_VARS set to {RECOMMEND REASON}" {
  grep -qE '^#[[:space:]]*EXPORTED_VARS:[[:space:]]*\{RECOMMEND[[:space:]]+REASON\}' skills/guide/scripts/scan-state.sh
}

@test "scan-state.sh priority list (1..N) is internally consistent" {
  # Count actual semantic priority paths in the comment block (lines with an
  # arrow). The v4 decision tree has 13 paths (1a, 1b, 1c, 2, 2.5, 3-10)
  # matching guide.md "13-path". The "1." line is a grouping header, not a path.
  n=$(awk '/^#[[:space:]]+[0-9]+([abc]?\.?|\.5)?[[:space:]].*→/ {print}' skills/guide/scripts/scan-state.sh | wc -l)
  echo "priority count = $n"
  [ "$n" -eq 13 ]
}

@test "guide.md path-count comment matches scan-state.sh count" {
  # guide.md uses "N-path 决策树" to describe the decision tree size.
  # scan-state.sh has 12 priority bullets but 13 actual code paths
  # (priority 9 splits into 9a approved + 9b pending + 10 default = 3 paths).
  # We verify guide.md says "13-path" to match the 13 code paths.
  guide_paths=$(grep -oE '[0-9]+-path' skills/guide/SKILL.md | grep -oE '[0-9]+' | head -1)
  [ "$guide_paths" = "13" ] || {
    echo "FAIL: guide.md claims $guide_paths-path, expected 13-path"
    return 1
  }
}
