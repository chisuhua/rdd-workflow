#!/usr/bin/env bats
# S3: worktree list is fetched twice — now at most 1 in bash code blocks.
# S11: case handler must accept `i` (user's custom input).

load ../test_helper

@test "status.md no longer duplicates git worktree list in Mode A Step 1" {
  # After S3 fix, the old Mode A Step 1 section (which duplicated the
  # top-of-file worktree list) should be removed. grep for the old
  # heading that preceded it: it should not appear.
  ! grep -qF "### Step 1：获取 worktree 列表" skills/status/SKILL.md
}

@test "status.md Mode A case handler includes i) branch" {
  grep -qF "i)" skills/status/SKILL.md
}
