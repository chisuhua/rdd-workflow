#!/usr/bin/env bats

load ../test_helper

# P2-10: guide-ship.md Phase 5 menu must distinguish two semantic endings:
#   - "本次 session 结束" — exit ship-done, resume in a later session
#   - "项目完成" — the entire project is archived; no more changes will be made
# The historical menu only had 2 options per branch and conflated these
# distinct semantics, making it impossible to communicate "we're done with
# this batch" vs "we're done with this project forever". Lock both labels.

@test "guide-ship.md Phase 5 distinguishes session-end vs project-complete" {
  # v2.0.8: Phase 5 loop-check menu extracted to scripts/ship_done.sh;
  # the 4-option menu with distinct session-end vs project-complete labels
  # now lives in check_remaining_work().
  [ -f "skills/guide-ship/scripts/ship_done.sh" ]
  grep -q "本次 session 结束" skills/guide-ship/scripts/ship_done.sh
  grep -q "项目完成" skills/guide-ship/scripts/ship_done.sh
}

@test "guide-ship.md Phase 5 menu has 4 numbered options" {
  # v2.0.8: menu lives in scripts/ship_done.sh, printed by check_remaining_work()
  [ -f "skills/guide-ship/scripts/ship_done.sh" ]
  # Should have 1, 2, 3, 4 numbered options (each appears twice - both variants)
  count=$(grep -cE '"[1-4]\.' skills/guide-ship/scripts/ship_done.sh)
  [ "$count" -ge 4 ]
}
