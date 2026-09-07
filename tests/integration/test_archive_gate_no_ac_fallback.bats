#!/usr/bin/env bats
# test_archive_gate_no_ac_fallback.bats — ADR-0045 Task 10
#
# Locks the archive gate's no-fallback contract:
#   1. cache hit (matching SHA) → archive succeeds
#   2. stale cache → archive fails with clear message
#   3. missing cache + SKIP_RDD_VERIFIER=yes + reason → audited bypass passes
#   4. missing cache + bypass unset → fail closed
#   5. SKIP_RDD_VERIFIER=yes without reason → fail closed

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TEST_TMP="$(mktemp -d)"
  cd "$TEST_TMP"
  git init -q
  git config user.email "t@t"
  git config user.name "T"
  mkdir -p openspec/changes/test-change .rddf/state
  echo "- [x] task" > openspec/changes/test-change/tasks.md
  printf '%s\n' "## 验收标准" "- AC-1: works" > openspec/changes/test-change/proposal.md
  git add . && git commit -q -m init
  ln -s "$REPO_ROOT/skills" "$TEST_TMP/skills"
}

teardown() {
  rm -rf "$TEST_TMP"
}

_seed_cache_at_head() {
  local sha
  sha=$(git rev-parse HEAD)
  cat > .rddf/state/.ac-verdict-test-change.json <<EOF
{"schema_version":2,"change":"test-change","codebase_commit":"$sha","verdict":[
  {"ac_id":"AC-1","status":"pass","confidence":0.9,"evidence":[{"tool":"Grep","query":"x","result_summary":"y"}],"reasoning":"ok"}
],"ran_at":"2026-09-07T00:00:00Z","ran_by":"rdd-verifier","verification_state":"passed"}
EOF
}

@test "no-fallback: cache hit (matching SHA) → archive gate succeeds" {
  _seed_cache_at_head
  source "$REPO_ROOT/_lib/archive.sh"
  run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Reusing verifier verdict cache"* ]]
}

@test "no-fallback: stale cache → archive gate blocked with clear message" {
  _seed_cache_at_head
  echo "invalidate" > new.txt && git add new.txt && git commit -q -m new
  source "$REPO_ROOT/_lib/archive.sh"
  run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"no valid verdict cache"* ]]
}

@test "no-fallback: missing cache + audited bypass → archive succeeds" {
  source "$REPO_ROOT/_lib/archive.sh"
  SKIP_RDD_VERIFIER=yes RDDF_VERIFIER_BYPASS_REASON="emergency hotfix" \
    run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
  [[ "$output" == *"bypassed"* ]]
}

@test "no-fallback: missing cache + bypass unset → archive blocked" {
  source "$REPO_ROOT/_lib/archive.sh"
  run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"rddf rdd-verify"* ]]
  [[ "$output" == *"no valid verdict cache"* ]]
}

@test "no-fallback: SKIP_RDD_VERIFIER=yes without reason → fail closed" {
  source "$REPO_ROOT/_lib/archive.sh"
  SKIP_RDD_VERIFIER=yes run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"requires RDDF_VERIFIER_BYPASS_REASON"* ]]
}
