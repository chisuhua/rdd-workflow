#!/usr/bin/env bats

load ../test_helper

# P2-10: guide-ship.md Phase 5 menu must distinguish two semantic endings:
#   - "本次 session 结束" — exit ship-done, resume in a later session
#   - "项目完成" — the entire project is archived; no more changes will be made
# The historical menu only had 2 options per branch and conflated these
# distinct semantics, making it impossible to communicate "we're done with
# this batch" vs "we're done with this project forever". Lock both labels.

@test "guide-ship.md Phase 5 distinguishes session-end vs project-complete" {
  [ -f "skills/guide-ship.md" ]
  grep -q "本次 session 结束" skills/guide-ship.md
  grep -q "项目完成" skills/guide-ship.md
}

@test "guide-ship.md Phase 5 menu has 4 numbered options" {
  [ -f "skills/guide-ship.md" ]
  # Should have 1, 2, 3, 4 (in Phase 5 context, not earlier phases)
  awk '/Phase 5/,EOF' skills/guide-ship.md | grep -E "^[1-4]\\." | head -5
}
