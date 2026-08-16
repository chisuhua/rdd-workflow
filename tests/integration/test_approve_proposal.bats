#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
  TMP_STATE="$(mktemp -d)"
  mkdir -p "$TMP_STATE/.rddf/state"
}

teardown() {
  rm -rf "$TMP_STATE"
}

@test "approve_proposal.sh without args exits non-zero" {
  run bash scripts/approve_proposal.sh
  [ "$status" -ne 0 ]
}

@test "approve_proposal.sh updates pending entry status" {
  export RDDF_PROJECT_ROOT="$TMP_STATE"
  # pre-populate pending entry
  cat > "$TMP_STATE/.rddf/state/.cross-repo-pending.json" <<EOF
{"version": 1, "entries": [{"hub_issue_url": "https://github.com/org/rdd-hub/issues/42", "gate_type": "Design-Gate", "expected_status": "approved", "created_at": "2026-08-15T16:00:00Z", "status": "pending"}]}
EOF
  run bash scripts/approve_proposal.sh test-change Design-Gate human-approver "looks good"
  [ "$status" -eq 0 ]
  result=$(python3 -c "import json; print(json.load(open('$TMP_STATE/.rddf/state/.cross-repo-pending.json'))['entries'][0]['status'])")
  [ "$result" = "approved" ]
}
