#!/usr/bin/env bats
# tests/integration/test_ship_review_extraction.bats
# P3-2 regression: Phase 2.5 of guide-ship.md was a 173-line case/esac
# bash block handling 4 review-debt sub-actions. Extracted to
# skills/_lib/ship_review.sh.
#
# These tests lock the refactor in place:
#   1. ship_review.sh exists with handle_review_action exported.
#   2. guide-ship.md Phase 2.5 calls handle_review_action "$choice" and
#      no longer inlines the 4 sub-action blocks.
#   3. Runtime: each of the 4 sub-actions produces the expected side effect.

load ../test_helper

@test "skills/_lib/ship_review.sh exists with handle_review_action" {
  [ -f "$REPO_ROOT/skills/guide-ship/scripts/ship_review.sh" ]
  grep -q "^handle_review_action()" "$REPO_ROOT/skills/guide-ship/scripts/ship_review.sh"
}

@test "guide-ship.md Phase 2.5 sources and uses ship_review.sh" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  grep -nE 'source .*scripts/ship_review.sh' "$REPO_ROOT/skills/guide-ship/SKILL.md"
  grep -nE 'handle_review_action' "$REPO_ROOT/skills/guide-ship/SKILL.md"
}

@test "guide-ship.md Phase 2.5 no longer inlines the 4 debt-action case branches" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  # Branch 1 (in-scope append): no more "追加到 tasks.md" inside bash block
  ! grep -qE '"type": "debt"' "$REPO_ROOT/skills/guide-ship/SKILL.md"
  # Branch 3 (arch drift doc)
  ! grep -qE '\-drift-analysis\.md' "$REPO_ROOT/skills/guide-review.sh" 2>/dev/null
  ! grep -qE '\-drift-analysis\.md' "$REPO_ROOT/skills/guide-ship/SKILL.md"
}

@test "guide-ship.md Phase 2.5 case/esac block is now thin (was 173)" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  # After refactor: no `case "$choice"` should appear in Phase 2.5 range
  # (lines 352-441). The dispatch logic lives in ship_review.sh now.
  ! sed -n '352,441p' "$REPO_ROOT/skills/guide-ship/SKILL.md" | grep -qE '^case "\$choice"'
  # The thin wrapper must exist (handle_review_action call).
  sed -n '352,441p' "$REPO_ROOT/skills/guide-ship/SKILL.md" | grep -qE 'handle_review_action'
}

@test "handle_review_action option 1 appends review todos to tasks.md" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  mkdir -p openspec/changes/test-change
  echo "# tasks" > openspec/changes/test-change/tasks.md
  printf "src/api.py: consider type hints\n" > /tmp/review_new_todos.txt
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_review.sh"
  handle_review_action "$TEST_REPO" "test-change" "$TEST_REPO" "1"
  grep -q "review: src/api.py" "$TEST_REPO/openspec/changes/test-change/tasks.md"
  rm -rf "$TEST_REPO"
  rm -f /tmp/review_new_todos.txt
}

@test "handle_review_action option 2 creates debt entry in proposal-suggestions.md" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  mkdir -p openspec/changes/parent-change
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_review.sh"
  handle_review_action "$TEST_REPO" "parent-change" "$TEST_REPO" "2"
  [ -f "$TEST_REPO/proposal-suggestions.md" ]
  grep -q '"type": "debt"' "$TEST_REPO/proposal-suggestions.md"
  grep -q 'cleanup-parent-change-debt' "$TEST_REPO/proposal-suggestions.md"
  rm -rf "$TEST_REPO"
}

@test "handle_review_action option 4 is a no-op (skip)" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_review.sh"
  run handle_review_action "$TEST_REPO" "x" "$TEST_REPO" "4"
  [ "$status" -eq 0 ]
  rm -rf "$TEST_REPO"
}

@test "ship_review.sh exports full_regression_gate function" {
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_review.sh"
  command -v full_regression_gate
}

@test "full_regression_gate skips when build directory is missing" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_review.sh"
  run full_regression_gate "$TEST_REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"无构建目录"* ]]
  rm -rf "$TEST_REPO"
}

@test "full_regression_gate fails with 3 options when ctest fails" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  mkdir -p "$TEST_REPO/build"
  mkdir -p "$TEST_REPO/bin"
  cat > "$TEST_REPO/bin/ctest" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  chmod +x "$TEST_REPO/bin/ctest"
  PATH="$TEST_REPO/bin:$PATH" source "$REPO_ROOT/skills/guide-ship/scripts/ship_review.sh"
  PATH="$TEST_REPO/bin:$PATH" run full_regression_gate "$TEST_REPO"
  [ "$status" -eq 1 ]
  [[ "$output" == *"全量回归失败"* ]]
  [[ "$output" == *"1. 返回 execute 修复问题"* ]]
  [[ "$output" == *"2. 创建 debt change 跟踪"* ]]
  [[ "$output" == *"3. SKIP_REGRESSION=1 强制跳过"* ]]
  rm -rf "$TEST_REPO"
}