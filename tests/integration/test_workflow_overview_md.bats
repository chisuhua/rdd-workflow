#!/usr/bin/env bats
load ../test_helper

@test "docs/v2-workflow-overview.md: mentions project-setup check" {
  grep -q 'project-setup' "$REPO_ROOT/docs/v2-workflow-overview.md"
}
