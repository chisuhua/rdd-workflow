#!/usr/bin/env bats
# G6: stale workflow-state.md detection was optional doc. Now promoted
#     into scan_state() so the runtime auto-surfaces the warning.

load ../test_helper

@test "scan-state.sh defines check_stale_workflow_state function" {
  grep -qF "check_stale_workflow_state()" skills/_lib/scan-state.sh
}

@test "scan-state.sh invokes check_stale_workflow_state from scan_state" {
  awk '
    /^scan_state[[:space:]]*\(\)/ { in_fn=1 }
    in_fn && /check_stale_workflow_state/ { found=1 }
    in_fn && /^}/ { exit }
    END { exit (found ? 0 : 1) }
  ' skills/_lib/scan-state.sh
}

@test "guide.md no longer carries the stale-state warning as duplicated doc" {
  if grep -q "Stale workflow-state" skills/guide/SKILL.md; then
    echo "FAIL: stale message still in guide.md"
    return 1
  fi
}
