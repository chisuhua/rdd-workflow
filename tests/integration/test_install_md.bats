#!/usr/bin/env bats
load ../test_helper

@test "INSTALL.md: contains 项目设置检查 section" {
  grep -q '项目设置检查' "$REPO_ROOT/skills/INSTALL.md"
}
