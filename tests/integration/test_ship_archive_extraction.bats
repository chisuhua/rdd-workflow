#!/usr/bin/env bats
# tests/integration/test_ship_archive_extraction.bats
# P3-2 regression: Phase 3 of guide-ship.md was a 179-line inline bash block
# for archive mode detection + feature integrity gate + worktree/lightweight
# archive orchestration. Extracted to skills/_lib/ship_archive.sh.
#
# These tests lock the refactor in place:
#   1. ship_archive.sh exists with archive_change_for_mode exported.
#   2. guide-ship.md Phase 3 calls archive_change_for_mode instead of inlining
#      the 179-line block.
#   3. Runtime: detect_archive_mode returns correct mode + feature integrity
#      gate is non-blocking by default.

load ../test_helper

# Phase 3 in current guide-ship.md spans lines 706-976.
PHASE3_RANGE="706,976p"

@test "skills/_lib/ship_archive.sh exists with expected exports" {
  [ -f "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh" ]
  grep -q "^detect_archive_mode()" "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  grep -q "^check_feature_integrity()" "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  grep -q "^archive_change_for_mode()" "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
}

@test "ship_archive.sh sources worktree.sh and archive.sh" {
  [ -f "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh" ]
  grep -q "worktree.sh" "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  grep -q "archive.sh" "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
}

@test "guide-ship.md Phase 3 sources and uses ship_archive.sh" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  grep -nE 'source .*scripts/ship_archive.sh' "$REPO_ROOT/skills/guide-ship/SKILL.md"
  grep -nE 'archive_change_for_mode|detect_archive_mode|check_feature_integrity' "$REPO_ROOT/skills/guide-ship/SKILL.md"
}

@test "guide-ship.md Phase 3 no longer inlines validate_delta_targets inline call" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  ! grep -nE 'validate_delta_targets\.py' "$REPO_ROOT/skills/guide-ship/SKILL.md"
}

@test "guide-ship.md Phase 3 archive orchestrator block is now thin (was 179)" {
  [ -f "$REPO_ROOT/skills/guide-ship/SKILL.md" ]
  # After refactor: no `git merge --no-ff` inline, no `PY_PROJECT_ROOT="$PROJECT_ROOT" python3 << 'PYEOF'` inline
  ! sed -n "$PHASE3_RANGE" "$REPO_ROOT/skills/guide-ship/SKILL.md" | grep -qE 'git merge --no-ff'
}

@test "detect_archive_mode returns worktree when worktree exists" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > README.md && git add README.md && git commit -q -m "initial"
  mkdir -p openspec/changes/c1
  git worktree add -b openspec/c1 .rddf/wt/c1 HEAD >/dev/null 2>&1
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  result=$(detect_archive_mode "$TEST_REPO" "c1")
  [ "$result" = "worktree" ]
  rm -rf "$TEST_REPO"
}

@test "detect_archive_mode returns lightweight when no worktree" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > README.md && git add README.md && git commit -q -m "initial"
  mkdir -p openspec/changes/c1
  git checkout -b openspec/c1 >/dev/null 2>&1
  source "$REPO_ROOT/skills/_lib/worktree.sh"
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  result=$(detect_archive_mode "$TEST_REPO" "c1")
  [ "$result" = "lightweight" ]
  rm -rf "$TEST_REPO"
}

@test "check_feature_integrity is non-blocking by default (FEATURE_ARCHIVE_GATE unset)" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  git init -q -b master
  git config user.email "test@test"
  git config user.name "test"
  echo "x" > README.md && git add README.md && git commit -q -m "initial"
  # No iteration.json, no feature-X changes → should exit 0 (no-op)
  source "$REPO_ROOT/skills/guide-ship/scripts/ship_archive.sh"
  run check_feature_integrity "$TEST_REPO" "any-change"
  [ "$status" -eq 0 ]
  rm -rf "$TEST_REPO"
}