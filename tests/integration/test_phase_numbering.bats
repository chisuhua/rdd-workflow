#!/usr/bin/env bats

load ../test_helper

# P2-6: guide-ship.md must use the explicit Phase 1.5 numbering for the
# "Worktree 验证 + 监控选择" section. The historical document presented
# this content as a continuation of Phase 1 (under a bold sub-heading
# "返回 Plan 前的检查"), which made it impossible to reference as a
# distinct step in workflow descriptions and tests. Lock the numbering
# so future renames stay consistent.

@test "guide-ship.md has Phase 1.5 numbering" {
  [ -f "skills/guide-ship.md" ]
  grep -qE "^## Phase 1\.5" skills/guide-ship.md
}

@test "guide-ship.md phases are numbered sequentially" {
  [ -f "skills/guide-ship.md" ]
  # Should have Phase 1, 1.5, 2, 3, 4, 5
  for n in 1 1.5 2 3 4 5; do
    if ! grep -qE "^## Phase ${n}\\b" skills/guide-ship.md; then
      echo "FAIL: missing Phase $n header"
      return 1
    fi
  done
}
