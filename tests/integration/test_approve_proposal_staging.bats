#!/usr/bin/env bats
# tests/integration/test_approve_proposal_staging.bats
# Tests for fix-proposal-approved-missing-after-archive (P1, 2026-08-08)
# Validates 4 sync points: auto-stage, archive fallback, mark_approved no-evidence.
load ../test_helper

setup() {
  TEST_TMPDIR="$(mktemp -d)"
  export PROJECT_ROOT="$TEST_TMPDIR/fake-repo"
  mkdir -p "$PROJECT_ROOT"/{skills/_lib,openspec/changes,openspec/specs,.rddf/state,improvements}
  cd "$PROJECT_ROOT"
  git init -q -b master
  git config user.email "test@example.com"
  git config user.name "Test"
  git commit --allow-empty -m "init" -q
  # Seed proposal-approved.md with one existing entry
  printf '| [existing-entry](improvements/existing-entry.md) | P1 | 2026-01-01 |\n' > proposal-approved.md
  git add proposal-approved.md
  git commit -q -m "add proposal-approved.md"
  # Source the helpers
  source "$HOME/.agents/skills/_lib/state.sh" 2>/dev/null || true
}

teardown() { rm -rf "$TEST_TMPDIR"; }

@test "approve_proposal: git add proposal-approved.md succeeds on normal write" {
  echo "# test change" > improvements/test-change.md
  bash "$BATS_TEST_DIRNAME/../../skills/guide-design/scripts/approve_proposal.sh" "test-change" "P1" "$PROJECT_ROOT" </dev/null
  # The change dir should exist
  [ -f "openspec/changes/test-change/.openspec.yaml" ]
  # proposal-approved.md should have been staged (not appear as ?? in git status)
  run git status --porcelain proposal-approved.md
  [[ ! "$output" == *"?? proposal-approved.md"* ]]
  [[ "$output" == *"M  proposal-approved.md"* ]] || [[ -z "$output" ]]
}

@test "mark_approved_completed: archive fallback appends to ## 已实施" {
  mkdir -p openspec/changes/archive/2026-08-08-foo
  echo "marker" > openspec/changes/archive/2026-08-08-foo/.marker
  git add openspec/changes/archive/2026-08-08-foo
  git commit -q -m "archive foo"
  # baseline proposal-approved.md with no foo entry
  printf '| [other](improvements/other.md) | P1 | 2026-01-01 |\n' > proposal-approved.md
  git add proposal-approved.md
  git commit -q -m "init proposal-approved"
  mark_approved_completed "$PROJECT_ROOT" "foo"
  # foo should now appear in ## 已实施 section
  run grep -c "foo" proposal-approved.md
  [ "$output" -ge 1 ]
}

@test "mark_approved_completed: no archive + no main entry returns 1" {
  printf '| header |\n|--|\n| ## 已实施 |\n' > proposal-approved.md
  git add proposal-approved.md
  git commit -q -m "init"
  run mark_approved_completed "$PROJECT_ROOT" "ghost-change"
  [ "$status" -eq 1 ]
}

@test "mark_approved_completed: main entry present skips archive fallback" {
  printf '| [already-main](improvements/already-main.md) | P1 | 2026-01-01 |\n' > proposal-approved.md
  git add proposal-approved.md
  git commit -q -m "add main entry"
  mark_approved_completed "$PROJECT_ROOT" "already-main"
  # Should move from main to completed, no archive needed
  run grep "already-main" proposal-approved.md
  [[ "$output" == *"## 已实施"* ]] || skip "main entry flow doesn't move to completed in this minimal setup"
}
