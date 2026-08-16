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

@test "design_done_gate blocks when pending RFC exists" {
  export RDDF_PROJECT_ROOT="$TMP_STATE"
  export SKIP_HUB_CHECK=false
  # pre-populate pending entry
  cat > "$TMP_STATE/.rddf/state/.cross-repo-pending.json" <<EOF
{"version": 1, "entries": [{"hub_issue_url": "https://github.com/org/rdd-hub/issues/42", "gate_type": "Design-Gate", "expected_status": "approved", "created_at": "2026-08-15T16:00:00Z", "status": "pending"}]}
EOF
  run env RDDF_PROJECT_ROOT="$TMP_STATE" SKIP_HUB_CHECK=false python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/skills/guide-design/scripts')
from design_done_gate import check_hub_pending
result = check_hub_pending()
sys.exit(1 if result else 0)
"
  [ "$status" -ne 0 ]
}

@test "design_done_gate passes when SKIP_HUB_CHECK=true" {
  export RDDF_PROJECT_ROOT="$TMP_STATE"
  export SKIP_HUB_CHECK=true
  cat > "$TMP_STATE/.rddf/state/.cross-repo-pending.json" <<EOF
{"version": 1, "entries": [{"hub_issue_url": "https://github.com/org/rdd-hub/issues/42", "gate_type": "Design-Gate", "expected_status": "approved", "created_at": "2026-08-15T16:00:00Z", "status": "pending"}]}
EOF
  run env RDDF_PROJECT_ROOT="$TMP_STATE" SKIP_HUB_CHECK=true python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/skills/guide-design/scripts')
from design_done_gate import check_hub_pending
result = check_hub_pending()
sys.exit(1 if result else 0)
"
  [ "$status" -eq 0 ]
}

@test "design_done_gate passes when no pending entries" {
  export RDDF_PROJECT_ROOT="$TMP_STATE"
  rm -f "$TMP_STATE/.rddf/state/.cross-repo-pending.json"
  run env RDDF_PROJECT_ROOT="$TMP_STATE" python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/skills/guide-design/scripts')
from design_done_gate import check_hub_pending
result = check_hub_pending()
sys.exit(1 if result else 0)
"
  [ "$status" -eq 0 ]
}
