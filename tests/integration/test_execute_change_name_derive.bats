#!/usr/bin/env bats
# tests/integration/test_execute_change_name_derive.bats
#
# Lock ensure_change_name semantics:
#   1. worktree branch openspec/<name> → derived
#   2. lightweight branch openspec/<name> → derived
#   3. explicit CHANGE_NAME wins
#   4. non-openspec branch fails with repair guidance
#   5. derived name makes .rddf/plans/<name>.md visible

load ../test_helper

HELPER="$REPO_ROOT/skills/execute/scripts/change_name.sh"

make_repo_with_branch() {
  local branch_name="$1"
  local tmpdir
  tmpdir=$(mktemp -d -t rdd-derive-XXXXXX)
  git -C "$tmpdir" init -q >/dev/null 2>&1
  git -C "$tmpdir" config user.email "test@example.com"
  git -C "$tmpdir" config user.name "Test"
  : > "$tmpdir/README.md"
  git -C "$tmpdir" add README.md >/dev/null 2>&1
  git -C "$tmpdir" commit -q -m "init" >/dev/null 2>&1
  git -C "$tmpdir" checkout -q -b "$branch_name"
  mkdir -p "$tmpdir/.rddf/plans"
  printf '# plan for %s\n' "${branch_name#openspec/}" > "$tmpdir/.rddf/plans/${branch_name#openspec/}.md"
  printf '%s' "$tmpdir"
}

@test "ensure_change_name: derives from worktree openspec/<name> branch" {
  tmpdir=$(make_repo_with_branch openspec/worktree-case)
  run bash -c "cd '$tmpdir' && source '$HELPER' && ensure_change_name && echo \"CHANGE_NAME=[\${CHANGE_NAME}]\" && test -f .rddf/plans/\$CHANGE_NAME.md && echo plan-visible"
  [ "$status" -eq 0 ]
  [[ "$output" == *"CHANGE_NAME=[worktree-case]"* ]]
  [[ "$output" == *"plan-visible"* ]]
}

@test "ensure_change_name: derives from lightweight openspec/<name> branch" {
  tmpdir=$(make_repo_with_branch openspec/lightweight-case)
  run bash -c "cd '$tmpdir' && source '$HELPER' && ensure_change_name && echo \"CHANGE_NAME=[\${CHANGE_NAME}]\" && test -f .rddf/plans/\$CHANGE_NAME.md && echo plan-visible"
  [ "$status" -eq 0 ]
  [[ "$output" == *"CHANGE_NAME=[lightweight-case]"* ]]
  [[ "$output" == *"plan-visible"* ]]
}

@test "ensure_change_name: explicit CHANGE_NAME wins" {
  tmpdir=$(make_repo_with_branch openspec/branch-case)
  run bash -c "
    cd '$tmpdir'
    export CHANGE_NAME=manual-case
    source '$HELPER'
    ensure_change_name
    printf 'CHANGE_NAME=[%s]\\n' \"\$CHANGE_NAME\"
  "
  [ "$status" -eq 0 ]
  [[ "$output" == *"CHANGE_NAME=[manual-case]"* ]]
}

@test "ensure_change_name: non-openspec branch fails with repair guidance" {
  tmpdir=$(make_repo_with_branch master)
  run bash -c "cd '$tmpdir' && source '$HELPER' && ensure_change_name"
  [ "$status" -ne 0 ]
  [[ "$output" == *"无法推导 change 名称"* ]]
  [[ "$output" == *"请设置 CHANGE_NAME"* ]]
}