#!/usr/bin/env bats
load ../test_helper

@test "USAGE.md: mentions fix_command in 常见陷阱" {
  grep -q 'fix_command' "$REPO_ROOT/USAGE.md"
}
