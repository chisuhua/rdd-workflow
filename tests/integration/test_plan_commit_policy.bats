#!/usr/bin/env bats
# tests/integration/test_plan_commit_policy.bats
#
# Verify that rdd-workflow-writing-plans and execute skill files default
# to deferring commit to the archive phase, not per-task commit.

load ../test_helper

setup() {
  wp="$REPO_ROOT/skills/rdd-workflow-writing-plans/SKILL.md"
}

@test "plan_commit_policy: writing-plans template step 5 defers commit" {
  # The example Step 5 heading must be "Defer commit" or equivalent.
  grep -qE 'Step 5.*Defer commit' "$wp"
  # The example Step 5 body must mention the archive-phase defer wording.
  grep -qE '留待 archive 阶段统一提交|暂不 commit|archive 阶段统一提交' "$wp"
}

@test "plan_commit_policy: writing-plans template does not instruct commit by default" {
  # Extract the embedded Task template block (from "### Task N:" to the closing `````).
  block=$(sed -n '/^### Task N:/,/^````/p' "$wp")
  # Default template must not contain a commit command.
  [[ "$block" != *"git commit"* ]]
  [[ "$block" != *"git add"* ]]
}

