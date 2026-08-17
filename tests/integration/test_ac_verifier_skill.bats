#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
}

# === Skill Registration ===

@test "ac-verifier: SKILL.md exists with user-invocable: true" {
  [ -f "$REPO_ROOT/skills/ac-verifier/SKILL.md" ]
  run grep "user-invocable: true" "$REPO_ROOT/skills/ac-verifier/SKILL.md"
  [ "$status" -eq 0 ]
}

@test "ac-verifier: all 3 scripts exist" {
  for f in ac_verifier.sh ac_verifier.py ac_verifier_mocks.py; do
    [ -f "$REPO_ROOT/skills/ac-verifier/scripts/$f" ]
  done
}

@test "ac-verifier: bash wrapper is executable" {
  [ -x "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" ]
}

# === CLI subcommand ===

@test "rddf ac-verify --help exits 0" {
  run rddf ac-verify --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"Verify OpenSpec"* ]]
}

@test "rddf ac-verify --skip exits 2" {
  run rddf ac-verify nonexistent-change --skip
  [ "$status" -eq 2 ]
}

@test "rddf ac-verify nonexistent-change exits 2 (no proposal)" {
  AC_LLM_MOCK=yes run rddf ac-verify nonexistent-change
  [ "$status" -eq 2 ]
}

# === Bash wrapper exit code mapping ===

@test "ac_verifier.sh --help exits 0" {
  run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" --help
  [ "$status" -eq 0 ]
}

@test "ac_verifier.sh with no args exits 3" {
  run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh"
  [ "$status" -eq 3 ]
}

@test "ac_verifier.sh honors SKIP_AC_VERIFICATION=yes" {
  SKIP_AC_VERIFICATION=yes run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" my-change
  [ "$status" -eq 2 ]
}

# === Mock LLM scenarios ===

@test "mock_pass_all: writes audit log entry with exit_code=0" {
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/openspec/changes/test-change"
  printf '%s\n' "## 验收标准" "- AC one" > "$TMP/openspec/changes/test-change/proposal.md"
  echo "- [x] task" > "$TMP/openspec/changes/test-change/tasks.md"
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_pass_all \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change
  [ "$status" -eq 0 ]
  [ -f "$TMP/.rddf/state/.ac-verification.jsonl" ]
  rm -rf "$TMP"
}

@test "mock_fail_one + --strict: exit 1" {
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/openspec/changes/test-change"
  printf '%s\n' "## 验收标准" "- AC one" "- AC two" > "$TMP/openspec/changes/test-change/proposal.md"
  echo "- [x] task" > "$TMP/openspec/changes/test-change/tasks.md"
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change --strict
  [ "$status" -eq 1 ]
  rm -rf "$TMP"
}

@test "mock_fail_one without --strict: exit 0 (warning)" {
  TMP="$(mktemp -d)"
  mkdir -p "$TMP/openspec/changes/test-change"
  printf '%s\n' "## 验收标准" "- AC one" "- AC two" > "$TMP/openspec/changes/test-change/proposal.md"
  echo "- [x] task" > "$TMP/openspec/changes/test-change/tasks.md"
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change
  [ "$status" -eq 0 ]
  rm -rf "$TMP"
}