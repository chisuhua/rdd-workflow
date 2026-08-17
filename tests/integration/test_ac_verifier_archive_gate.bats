#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TEST_TMP="$(mktemp -d)"
  cd "$TEST_TMP"
  git init -q
  mkdir -p "$TEST_TMP/openspec/changes/test-change"
  # Symlink skills/ so archive_gate_check can find ac-verifier script
  ln -s "$REPO_ROOT/skills" "$TEST_TMP/skills"
}

teardown() {
  rm -rf "$TEST_TMP"
}

# === archive_gate_check with AC verification ===

@test "archive_gate_check passes when AC verification passes (mock)" {
  echo "- [x] task" > "$TEST_TMP/openspec/changes/test-change/tasks.md"
  cat > "$TEST_TMP/openspec/changes/test-change/proposal.md" <<'PROPOSAL'
## Acceptance Criteria
- AC-1: implement login
- AC-2: implement logout
PROPOSAL
  source "$REPO_ROOT/_lib/archive.sh"
  AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_pass_all \
    run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
}

@test "archive_gate_check warns (not blocks) on AC verifier error" {
  echo "- [x] task" > "$TEST_TMP/openspec/changes/test-change/tasks.md"
  cat > "$TEST_TMP/openspec/changes/test-change/proposal.md" <<'PROPOSAL'
## Acceptance Criteria
- AC-1: implement login
- AC-2: implement logout
PROPOSAL
  source "$REPO_ROOT/_lib/archive.sh"
  AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_invalid_json \
    run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
  [[ "$output" == *"AC verification errored"* ]]
}

@test "archive_gate_check blocks on AC fail with STRICT_AC_GATE=yes" {
  echo "- [x] task" > "$TEST_TMP/openspec/changes/test-change/tasks.md"
  cat > "$TEST_TMP/openspec/changes/test-change/proposal.md" <<'PROPOSAL'
## Acceptance Criteria
- AC-1: implement login
- AC-2: implement logout
PROPOSAL
  source "$REPO_ROOT/_lib/archive.sh"
  STRICT_AC_GATE=yes AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 1 ]
}

@test "archive_gate_check skips AC verification with SKIP_AC_VERIFICATION=yes" {
  echo "- [x] task" > "$TEST_TMP/openspec/changes/test-change/tasks.md"
  cat > "$TEST_TMP/openspec/changes/test-change/proposal.md" <<'PROPOSAL'
## Acceptance Criteria
- AC-1: implement login
- AC-2: implement logout
PROPOSAL
  source "$REPO_ROOT/_lib/archive.sh"
  SKIP_AC_VERIFICATION=yes AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
}

@test "archive_gate_check skips AC verification when no proposal.md" {
  echo "- [x] task" > "$TEST_TMP/openspec/changes/test-change/tasks.md"
  source "$REPO_ROOT/_lib/archive.sh"
  AC_LLM_MOCK=yes run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
}