#!/usr/bin/env bats
# tests/integration/test_count_pending_suggestions.bats
# P3-3b regression: 'count pending proposals' Python heredoc was inlined
# in 3 files (propose.md:891-903, status.md:413-425, rdd-planner.md:317-366).
# Extracted to _lib/state.sh::count_pending_suggestions.
#
# These tests lock:
#   1. state.sh defines count_pending_suggestions
#   2. propose.md, status.md, rdd-planner.md no longer inline the algorithm
#   3. Runtime: returns 0 for missing file, 0 for empty list, N for valid list

load ../test_helper

@test "_lib/state.sh defines count_pending_suggestions" {
  [ -f "$REPO_ROOT/_lib/state.sh" ]
  grep -q '^count_pending_suggestions()' "$REPO_ROOT/_lib/state.sh"
}

@test "propose.md no longer inlines count pending proposals algorithm" {
  [ -f "$REPO_ROOT/skills/propose/SKILL.md" ]
  ! grep -qE "sum\(1 for e in entries.*e\.get\('status'\) == '待创建'\)" "$REPO_ROOT/skills/propose/SKILL.md"
}

@test "status.md no longer inlines count pending proposals algorithm" {
  [ -f "$REPO_ROOT/skills/status/SKILL.md" ]
  ! grep -qE "sum\(1 for e in entries.*e\.get\(.status.\) == .待创建" "$REPO_ROOT/skills/status/SKILL.md"
}

@test "rdd-planner.md no longer inlines count pending proposals algorithm" {
  [ -f "$REPO_ROOT/skills/rdd-planner/SKILL.md" ]
  ! grep -qE "sum\(1 for e in entries.*e\.get\(.status.\) == .待创建" "$REPO_ROOT/skills/rdd-planner/SKILL.md"
}

@test "count_pending_suggestions returns 0 when proposal-suggestions.md missing" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  source "$REPO_ROOT/_lib/state.sh"
  result=$(count_pending_suggestions "$TEST_REPO")
  [ "$result" = "0" ]
  rm -rf "$TEST_REPO"
}

@test "count_pending_suggestions returns 0 when entries list is empty" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  echo "[]" > proposal-suggestions.md
  source "$REPO_ROOT/_lib/state.sh"
  result=$(count_pending_suggestions "$TEST_REPO")
  [ "$result" = "0" ]
  rm -rf "$TEST_REPO"
}

@test "count_pending_suggestions returns N when N .md files in .rddf/improvements/" {
  # v2.0+ API: helper scans `.rddf/improvements/*.md` (not the v3-era
  # proposal-suggestions.md JSON). Create N improvement files; no approval file
  # means all count as pending.
  TEST_REPO=$(mktemp -d)
  mkdir -p "$TEST_REPO/.rddf/improvements"
  for n in a b c d; do
    printf '# %s\n' "$n" > "$TEST_REPO/.rddf/improvements/$n.md"
  done
  source "$REPO_ROOT/_lib/state.sh"
  result=$(count_pending_suggestions "$TEST_REPO")
  [ "$result" = "4" ]
  rm -rf "$TEST_REPO"
}

@test "count_pending_suggestions tolerates non-md files in improvements/" {
  # Helper filters to *.md only; other files are ignored (defensive against
  # editors leaving .swp / .bak around).
  TEST_REPO=$(mktemp -d)
  mkdir -p "$TEST_REPO/.rddf/improvements"
  for n in a b; do
    printf '# %s\n' "$n" > "$TEST_REPO/.rddf/improvements/$n.md"
  done
  printf 'leftover\n' > "$TEST_REPO/.rddf/improvements/.a.md.swp"
  printf 'backup\n' > "$TEST_REPO/.rddf/improvements/b.md.bak"
  source "$REPO_ROOT/_lib/state.sh"
  result=$(count_pending_suggestions "$TEST_REPO")
  [ "$result" = "2" ]
  rm -rf "$TEST_REPO"
}