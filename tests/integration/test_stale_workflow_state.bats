#!/usr/bin/env bats
# G6: stale workflow-state.md detection was optional doc. Now promoted
#     into scan_state() so the runtime auto-surfaces the warning.

load ../test_helper

@test "scan-state.sh defines check_stale_workflow_state function" {
  grep -qF "check_stale_workflow_state()" skills/guide/scripts/scan-state.sh
}

@test "scan-state.sh invokes check_stale_workflow_state from scan_state" {
  # `scan_state()` is the public entry point; it delegates the ladder to
  # `_scan_state_impl()` so that the "non-authoritative" marker (used when
  # python3 is unavailable) can be appended to the REASON on EVERY return
  # path. The stale-state check therefore lives in the delegated function.
  awk '
    /^(scan_state|_scan_state_impl)[[:space:]]*\(\)/ { in_fn=1 }
    in_fn && /check_stale_workflow_state/ { found=1 }
    in_fn && /^}/ { in_fn=0 }
    END { exit (found ? 0 : 1) }
  ' skills/guide/scripts/scan-state.sh
}

@test "scan-state.sh scan_state delegates to the implementation" {
  # Guard the delegation itself: without it the marker could never be
  # applied to the early return paths.
  grep -qE '^scan_state[[:space:]]*\(\)[[:space:]]*\{' skills/guide/scripts/scan-state.sh
  grep -q '_scan_state_impl' skills/guide/scripts/scan-state.sh
}

@test "guide.md no longer carries the stale-state warning as duplicated doc" {
  if grep -q "Stale workflow-state" skills/guide/SKILL.md; then
    echo "FAIL: stale message still in guide.md"
    return 1
  fi
}
