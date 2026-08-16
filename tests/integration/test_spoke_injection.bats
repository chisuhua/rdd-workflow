#!/usr/bin/env bats
# tests/integration/test_spoke_injection.bats
#
# Integration tests for spoke-system-prompt-injection skill.
# Tests deploy.sh idempotency, multi-tool support, backup, and uninstall.

load ../test_helper

SKILL_DIR="${REPO_ROOT}/skills/spoke-system-prompt-injection"
DEPLOY_SCRIPT="${SKILL_DIR}/scripts/deploy.sh"

setup() {
  TEST_ROOT="${BATS_TMPDIR}/spoke-test-$$"
  mkdir -p "$TEST_ROOT"
  cd "$TEST_ROOT"
  git init -q
  git config user.email "test@example.com"
  git config user.name "Test"
  echo "test project" > README.md
  git add README.md
  git commit -q -m "init"
}

teardown() {
  rm -rf "$TEST_ROOT"
}

# ── deploy test case ────────────────────────────────────────────────

@test "spoke_injection: deploy.sh --tools cursor injects protocol into .cursorrules" {
  [ -x "$DEPLOY_SCRIPT" ] || skip "deploy.sh not found or not executable"
  RDDF_SPOKE_TARGET_DIR="$TEST_ROOT" bash "$DEPLOY_SCRIPT" --tools cursor
  assert_file_exists "$TEST_ROOT/.cursorrules"
  assert_file_contains "$TEST_ROOT/.cursorrules" "<!-- RDD-HUB-PROTOCOL-START -->"
  assert_file_contains "$TEST_ROOT/.cursorrules" "<!-- RDD-HUB-PROTOCOL-END -->"
  assert_file_contains "$TEST_ROOT/.cursorrules" "RFC Initiation"
  assert_file_contains "$TEST_ROOT/.cursorrules" "RFC Review"
  assert_file_contains "$TEST_ROOT/.cursorrules" "Sync"
  assert_file_contains "$TEST_ROOT/.cursorrules" "Auto-Approval Prohibition"
}

# ── idempotent re-run test case ────────────────────────────────────

@test "spoke_injection: running deploy.sh twice produces identical output (no duplicate)" {
  [ -x "$DEPLOY_SCRIPT" ] || skip "deploy.sh not found or not executable"
  RDDF_SPOKE_TARGET_DIR="$TEST_ROOT" bash "$DEPLOY_SCRIPT" --tools cursor
  local first_content
  first_content=$(cat "$TEST_ROOT/.cursorrules")
  RDDF_SPOKE_TARGET_DIR="$TEST_ROOT" bash "$DEPLOY_SCRIPT" --tools cursor
  local second_content
  second_content=$(cat "$TEST_ROOT/.cursorrules")
  [ "$first_content" = "$second_content" ]
  # Count protocol blocks - should be exactly 1
  local block_count
  block_count=$(grep -c "<!-- RDD-HUB-PROTOCOL-START -->" "$TEST_ROOT/.cursorrules" || true)
  [ "$block_count" -eq 1 ]
}

# ── multi-tool deployment test case ─────────────────────────────────

@test "spoke_injection: --tools all deploys to all 5 tools" {
  [ -x "$DEPLOY_SCRIPT" ] || skip "deploy.sh not found or not executable"
  RDDF_SPOKE_TARGET_DIR="$TEST_ROOT" bash "$DEPLOY_SCRIPT" --tools all
  assert_file_exists "$TEST_ROOT/.cursorrules"
  assert_file_exists "$TEST_ROOT/.clinerules"
  assert_file_exists "$TEST_ROOT/.continue/rules/cross-repo-hub.md"
  assert_file_exists "$TEST_ROOT/.github/copilot-instructions.md"
  assert_file_exists "$TEST_ROOT/CLAUDE.md"
  for file in .cursorrules .clinerules .continue/rules/cross-repo-hub.md .github/copilot-instructions.md CLAUDE.md; do
    assert_file_contains "$TEST_ROOT/$file" "<!-- RDD-HUB-PROTOCOL-START -->"
  done
}

# ── uninstall test case ─────────────────────────────────────────────

@test "spoke_injection: --uninstall removes protocol block" {
  [ -x "$DEPLOY_SCRIPT" ] || skip "deploy.sh not found or not executable"
  RDDF_SPOKE_TARGET_DIR="$TEST_ROOT" bash "$DEPLOY_SCRIPT" --tools cursor
  assert_file_contains "$TEST_ROOT/.cursorrules" "<!-- RDD-HUB-PROTOCOL-START -->"
  RDDF_SPOKE_TARGET_DIR="$TEST_ROOT" bash "$DEPLOY_SCRIPT" --uninstall --tools cursor
  [ -f "$TEST_ROOT/.cursorrules" ] || true
  local block_count
  block_count=$(grep -c "<!-- RDD-HUB-PROTOCOL-START -->" "$TEST_ROOT/.cursorrules" || true)
  [ "$block_count" -eq 0 ]
}

# ── backup creation test case ─────────────────────────────────────

@test "spoke_injection: deploy.sh creates backup before modification" {
  [ -x "$DEPLOY_SCRIPT" ] || skip "deploy.sh not found or not executable"
  echo "existing content" > "$TEST_ROOT/.cursorrules"
  RDDF_SPOKE_TARGET_DIR="$TEST_ROOT" bash "$DEPLOY_SCRIPT" --tools cursor
  local backup_count
  backup_count=$(ls -1 "$TEST_ROOT/.cursorrules".bak.* 2>/dev/null | wc -l)
  [ "$backup_count" -ge 1 ]
  local backup_file
  backup_file=$(ls -t "$TEST_ROOT/.cursorrules".bak.* 2>/dev/null | head -1)
  [ "$(cat "$backup_file")" = "existing content" ]
}
