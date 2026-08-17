#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TMP="$(mktemp -d)"
  export TMP
  mkdir -p "$TMP/openspec/changes/test-change"
  printf '%s\n' "## 验收标准" "- AC one" "- AC two" "- AC three" > "$TMP/openspec/changes/test-change/proposal.md"
  echo "- [x] task" > "$TMP/openspec/changes/test-change/tasks.md"
}

teardown() {
  rm -rf "$TMP"
}

@test "e2e: mock_pass_all → exit 0 + audit log" {
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_pass_all \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change
  [ "$status" -eq 0 ]
  [ -f "$TMP/.rddf/state/.ac-verification.jsonl" ]
}

@test "e2e: mock_fail_one (warning mode) → exit 0 + audit log" {
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change
  [ "$status" -eq 0 ]
  log="$TMP/.rddf/state/.ac-verification.jsonl"
  [ -f "$log" ]
  grep -q '"change_name": "test-change"' "$log"
}

@test "e2e: mock_fail_one (strict mode) → exit 1 + audit log" {
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_fail_one \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change --strict
  [ "$status" -eq 1 ]
  [ -f "$TMP/.rddf/state/.ac-verification.jsonl" ]
}

@test "e2e: mock_invalid_json → exit 3 + audit log skipped" {
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_invalid_json \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change
  [ "$status" -eq 3 ]
  [ ! -f "$TMP/.rddf/state/.ac-verification.jsonl" ]
}

@test "e2e: mock_omitted_ac → AC-3 auto-filled as fail + exit 1 (strict)" {
  PROJECT_ROOT="$TMP" AC_LLM_MOCK=yes AC_LLM_MOCK_SCENARIO=mock_omitted_ac \
    run bash "$REPO_ROOT/skills/ac-verifier/scripts/ac_verifier.sh" test-change --strict
  [ "$status" -eq 1 ]
  log="$TMP/.rddf/state/.ac-verification.jsonl"
  grep -q '"AI omitted' "$log"
}