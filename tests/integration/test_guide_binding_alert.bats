#!/usr/bin/env bats
#
# Integration tests for scan_session_binding() output appended to guide
# recommender (spec 2026-07-14).

load ../test_helper

setup() {
  export TEST_ROOT="$BATS_TMPDIR/test-guide-binding-$$"
  mkdir -p "$TEST_ROOT/.rddf/state"
  cd "$TEST_ROOT"
  git init -q
  git config user.email "test@example.com"
  git config user.name "Test"
  # Roadmap + plan-handoff absent → scan_state falls through to default.
  # We do NOT set up a full project; we only verify BINDING_LINES behavior.
  load_lib scan-state
}

teardown() {
  rm -rf "$TEST_ROOT"
}

@test "scan_session_binding 输出 binding 行 当有 current binding" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_ship", owner_opencode_session_id="ses_me", goal={})
PYEOF
  export OPENCODE_SESSION_ID="ses_me"
  scan_session_binding "$TEST_ROOT"
  [ "${#BINDING_LINES[@]}" -gt 0 ]
  [[ "${BINDING_LINES[0]}" == *"📍 Current: rds_"* ]]
}

@test "scan_session_binding 输出 recommended next 行 当无 binding + 有 orphaned" {
  python3 - <<PYEOF
import sys, json
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
sid = coord.create_session(kind="stage_plan", owner_opencode_session_id="ses_old", goal={})
data = json.loads(coord._sessions_file.read_text())
for s in data["sessions"]:
    if s["session_id"] == sid:
        s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
coord._atomic_write(data)
coord.check_heartbeat_timeouts()
PYEOF
  export OPENCODE_SESSION_ID="ses_me"
  scan_session_binding "$TEST_ROOT"
  [ "${#BINDING_LINES[@]}" -ge 2 ]
  [[ "${BINDING_LINES[0]}" == *"📍 No current binding"* ]]
  [[ "${BINDING_LINES[1]}" == *"💡 Recommended: rds_"* ]]
}

@test "scan_session_binding 不输出行 当 sessions.json 缺失" {
  rm -f "$TEST_ROOT/.rddf/state/sessions.json"
  export OPENCODE_SESSION_ID="ses_me"
  scan_session_binding "$TEST_ROOT"
  [ "${#BINDING_LINES[@]}" -eq 0 ]
}

@test "scan_session_binding 不修改 RECOMMEND" {
  # scan_state should still set RECOMMEND; scan_session_binding should
  # NOT clear it. Verify they coexist.
  scan_state "$TEST_ROOT"
  RECOMMEND_BEFORE="$RECOMMEND"
  scan_session_binding "$TEST_ROOT"
  [ "$RECOMMEND" = "$RECOMMEND_BEFORE" ]
}

@test "scan_session_binding 不修改 sessions.json" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_ship", owner_opencode_session_id="ses_me", goal={})
PYEOF
  before_hash=$(sha256sum "$TEST_ROOT/.rddf/state/sessions.json" | awk '{print $1}')
  export OPENCODE_SESSION_ID="ses_me"
  scan_session_binding "$TEST_ROOT"
  after_hash=$(sha256sum "$TEST_ROOT/.rddf/state/sessions.json" | awk '{print $1}')
  [ "$before_hash" = "$after_hash" ]
}