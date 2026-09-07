#!/usr/bin/env bats
# test_ac_verifier_archive_gate.bats — archive_gate_check AC verification gate
#
# v2.0 semantics (ADR-0045): no ac-verifier subprocess fallback. The gate
# consumes the SHA-bound verdict cache only; missing/stale cache fails
# closed unless the audited bypass (SKIP_RDD_VERIFIER=yes +
# RDDF_VERIFIER_BYPASS_REASON) is set.
#
# Complementary bypass scenarios live in
# tests/integration/test_archive_gate_no_ac_fallback.bats (Task 10).

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TEST_TMP="$(mktemp -d)"
  cd "$TEST_TMP"
  git init -q
  git config user.email "t@t"
  git config user.name "T"
  mkdir -p "$TEST_TMP/openspec/changes/test-change" "$TEST_TMP/.rddf/state"
  # Symlink skills/ so verifier helpers are discoverable
  ln -s "$REPO_ROOT/skills" "$TEST_TMP/skills"
  echo "- [x] task" > "$TEST_TMP/openspec/changes/test-change/tasks.md"
  cat > "$TEST_TMP/openspec/changes/test-change/proposal.md" <<'PROPOSAL'
## Acceptance Criteria
- AC-1: implement login
- AC-2: implement logout
PROPOSAL
  git add . && git commit -q -m init
}

teardown() {
  rm -rf "$TEST_TMP"
}

# === archive_gate_check AC gate (cache-only, per ADR-0045) ===

@test "archive_gate_check fails closed when no verdict cache exists" {
  source "$REPO_ROOT/_lib/archive.sh"
  run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"no valid verdict cache"* ]]
}

@test "archive_gate_check passes when fresh cache has all-pass verdict" {
  SHA=$(git rev-parse HEAD)
  cat > "$TEST_TMP/.rddf/state/.ac-verdict-test-change.json" <<EOF
{"version":2,"change":"test-change","codebase_commit":"$SHA","verdict":[
  {"ac_id":"AC-1","status":"pass","confidence":0.95,"evidence":[],"reasoning":"ok"}
],"ran_at":"2026-09-07T00:00:00Z","ran_by":"rdd-verifier"}
EOF
  source "$REPO_ROOT/_lib/archive.sh"
  run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Reusing verifier verdict cache"* ]]
}

@test "archive_gate_check blocks on cached AC fail with STRICT_AC_GATE=yes" {
  SHA=$(git rev-parse HEAD)
  cat > "$TEST_TMP/.rddf/state/.ac-verdict-test-change.json" <<EOF
{"version":2,"change":"test-change","codebase_commit":"$SHA","verdict":[
  {"ac_id":"AC-1","status":"fail","confidence":0.9,"evidence":[],"reasoning":"missing implementation"}
],"ran_at":"2026-09-07T00:00:00Z","ran_by":"rdd-verifier"}
EOF
  source "$REPO_ROOT/_lib/archive.sh"
  STRICT_AC_GATE=yes run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"AC verification failed under STRICT_AC_GATE"* ]]
}

@test "archive_gate_check skips AC verification with SKIP_AC_VERIFICATION=yes" {
  source "$REPO_ROOT/_lib/archive.sh"
  SKIP_AC_VERIFICATION=yes run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
}

@test "archive_gate_check skips AC verification when no proposal.md" {
  rm "$TEST_TMP/openspec/changes/test-change/proposal.md"
  source "$REPO_ROOT/_lib/archive.sh"
  run archive_gate_check test-change "$TEST_TMP"
  [ "$status" -eq 0 ]
}
