#!/usr/bin/env bats
# tests/integration/test_plan_commit_policy.bats
#
# Verify that rdd-workflow-writing-plans and execute skill files default
# to deferring commit to the archive phase, not per-task commit.

load ../test_helper

setup() {
  wp="$REPO_ROOT/skills/rdd-workflow-writing-plans/SKILL.md"
  ex="$REPO_ROOT/skills/execute/SKILL.md"
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

@test "plan_commit_policy: execute skill step 5 defers commit" {
  # The execute skill instructions must contain the defer wording.
  grep -qE 'Step 5.*Defer commit|execute 阶段不.*commit|archive 阶段.*提交' "$ex"
  # The five lines following "Step 5" must not contain a commit command.
  run grep -A 5 "Step 5" "$ex"
  [[ "$output" != *"git commit"* ]]
}
