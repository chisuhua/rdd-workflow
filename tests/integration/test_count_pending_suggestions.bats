#!/usr/bin/env bats
# tests/integration/test_count_pending_suggestions.bats
# P3-3b regression: 'count pending proposals' Python heredoc was inlined
# in 3 files (propose.md:891-903, status.md:413-425, guide-plan.md:317-366).
# Extracted to _lib/state.sh::count_pending_suggestions.
#
# These tests lock:
#   1. state.sh defines count_pending_suggestions
#   2. propose.md, status.md, guide-plan.md no longer inline the algorithm
#   3. Runtime: returns 0 for missing file, 0 for empty list, N for valid list

load ../test_helper

@test "skills/_lib/state.sh defines count_pending_suggestions" {
  [ -f "$REPO_ROOT/skills/_lib/state.sh" ]
  grep -q '^count_pending_suggestions()' "$REPO_ROOT/skills/_lib/state.sh"
}

@test "propose.md no longer inlines count pending proposals algorithm" {
  [ -f "$REPO_ROOT/skills/propose.md" ]
  ! grep -qE "sum\(1 for e in entries.*e\.get\('status'\) == '待创建'\)" "$REPO_ROOT/skills/propose.md"
}

@test "status.md no longer inlines count pending proposals algorithm" {
  [ -f "$REPO_ROOT/skills/status.md" ]
  ! grep -qE "sum\(1 for e in entries.*e\.get\(.status.\) == .待创建" "$REPO_ROOT/skills/status.md"
}

@test "guide-plan.md no longer inlines count pending proposals algorithm" {
  [ -f "$REPO_ROOT/skills/guide-plan.md" ]
  ! grep -qE "sum\(1 for e in entries.*e\.get\(.status.\) == .待创建" "$REPO_ROOT/skills/guide-plan.md"
}

@test "count_pending_suggestions returns 0 when proposal-suggestions.md missing" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  source "$REPO_ROOT/skills/_lib/state.sh"
  result=$(count_pending_suggestions "$TEST_REPO")
  [ "$result" = "0" ]
  rm -rf "$TEST_REPO"
}

@test "count_pending_suggestions returns 0 when entries list is empty" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  echo "[]" > proposal-suggestions.md
  source "$REPO_ROOT/skills/_lib/state.sh"
  result=$(count_pending_suggestions "$TEST_REPO")
  [ "$result" = "0" ]
  rm -rf "$TEST_REPO"
}

@test "count_pending_suggestions returns N when entries have 待创建 status" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  cat > proposal-suggestions.md <<'EOF'
[
  {"name": "a", "status": "待创建"},
  {"name": "b", "status": "created"},
  {"name": "c", "status": "待创建"},
  {"name": "d", "status": "待创建"}
]
EOF
  source "$REPO_ROOT/skills/_lib/state.sh"
  result=$(count_pending_suggestions "$TEST_REPO")
  [ "$result" = "3" ]
  rm -rf "$TEST_REPO"
}

@test "count_pending_suggestions ignores malformed entries (defensive)" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  # Mix valid entries with malformed ones
  cat > proposal-suggestions.md <<'EOF'
[
  {"name": "a", "status": "待创建"},
  "not-a-dict",
  {"name": "b"},
  {"name": "c", "status": "待创建"}
]
EOF
  source "$REPO_ROOT/skills/_lib/state.sh"
  result=$(count_pending_suggestions "$TEST_REPO")
  [ "$result" = "2" ]
  rm -rf "$TEST_REPO"
}