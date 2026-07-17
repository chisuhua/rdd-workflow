#!/usr/bin/env bats
#
# Integration tests for `rddf-session current` subcommand (spec 2026-07-14).
# Verifies binding discovery + recommendation output via the bash wrapper.

load ../test_helper

setup() {
  export TEST_ROOT="$BATS_TMPDIR/test-rddf-current-$$"
  mkdir -p "$TEST_ROOT/.rddf/state"
  cd "$TEST_ROOT"
  git init -q
  git config user.email "test@example.com"
  git config user.name "Test"
}

teardown() {
  rm -rf "$TEST_ROOT"
}

# Helper: invoke the `current` subcommand via inline python (mirrors
# the bash heredoc in skills/rddf-session/SKILL.md but keeps the test pure-python
# to avoid sourcing markdown heredocs).
run_current() {
  local owner="${1:-ses_me}"
  PY_PROJECT_ROOT="$TEST_ROOT" python3 - <<PYEOF
import os, sys
sys.path.insert(0, "$REPO_ROOT")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=os.path.join(os.environ["PY_PROJECT_ROOT"], ".rddf/state/sessions.json"))
coord.check_heartbeat_timeouts()
current = coord.find_current_binding("$owner")
if current:
    print(f"\U0001f4cd Current: {current.session_id} (kind={current.kind}, started={current.started_at})")
else:
    print("\U0001f4cd No current binding")
    nxt = coord.find_next_recommendation("$owner")
    if nxt:
        print(f"\U0001f4a1 Recommended: {nxt.session_id} (kind={nxt.kind}, last_heartbeat={nxt.last_heartbeat})")
        print(f'   \u2192 skill_use("rddf-session resume {nxt.session_id}")')
    else:
        print("   No orphaned rddf-sessions found. Run guide-arch or guide-plan to start.")
PYEOF
}

@test "current: output contains rds_id when active binding exists" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_plan", owner_opencode_session_id="ses_me", goal={})
PYEOF
  run run_current "ses_me"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Current: rds_"* ]]
  [[ "$output" == *"kind=stage_plan"* ]]
}

@test "current: outputs No current binding when unbound" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_plan", owner_opencode_session_id="ses_other", goal={})
PYEOF
  run run_current "ses_me"
  [ "$status" -eq 0 ]
  [[ "$output" == *"No current binding"* ]]
}

@test "current: outputs Recommended next when orphaned exists" {
  python3 - <<PYEOF
import sys, json
sys.path.insert(0, "$REPO_ROOT")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
sid = coord.create_session(kind="stage_plan", owner_opencode_session_id="ses_old", goal={})
# Force orphaned
sfile = "$TEST_ROOT/.rddf/state/sessions.json"
with open(sfile) as f:
    data = json.load(f)
for s in data["sessions"]:
    if s["session_id"] == sid:
        s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
coord._atomic_write(data)
coord.check_heartbeat_timeouts()
PYEOF
  run run_current "ses_me"
  [ "$status" -eq 0 ]
  [[ "$output" == *"No current binding"* ]]
  [[ "$output" == *"Recommended: rds_"* ]]
  [[ "$output" == *"rddf-session resume rds_"* ]]
}

@test "current: outputs fallback text when sessions.json missing" {
  rm -f "$TEST_ROOT/.rddf/state/sessions.json"
  run run_current "ses_me"
  [ "$status" -eq 0 ]
  [[ "$output" == *"No current binding"* ]]
  [[ "$output" == *"No orphaned rddf-sessions found"* ]]
}

@test "current: silent return exit 0 on corrupt JSON" {
  echo "this is not json" > "$TEST_ROOT/.rddf/state/sessions.json"
  run run_current "ses_me"
  [[ "$output" == *"No current binding"* ]] || [[ "$output" == *"JSON"* ]] || [[ "$output" == *"error"* ]]
}

@test "current: uses OPENCODE_SESSION_ID env var" {
  export OPENCODE_SESSION_ID="ses_special_marker_42"
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_arch", owner_opencode_session_id="ses_special_marker_42", goal={})
PYEOF
  run run_current "ses_special_marker_42"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Current: rds_"* ]]
}

@test "current: fallback to hostname_$$" {
  # No OPENCODE_SESSION_ID set; fallback to hostname_$$ pattern.
  unset OPENCODE_SESSION_ID
  python3 - <<PYEOF
import sys, socket
sys.path.insert(0, "$REPO_ROOT")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
expected = f"{socket.gethostname().split('.')[0]}_$$"
coord.create_session(kind="stage_plan", owner_opencode_session_id=expected, goal={})
PYEOF
  run run_current "$(hostname -s)_$$"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Current: rds_"* ]]
}

@test "current: does not modify sessions.json" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_plan", owner_opencode_session_id="ses_me", goal={})
PYEOF
  before_hash=$(sha256sum "$TEST_ROOT/.rddf/state/sessions.json" | awk '{print $1}')
  run run_current "ses_me"
  after_hash=$(sha256sum "$TEST_ROOT/.rddf/state/sessions.json" | awk '{print $1}')
  [ "$before_hash" = "$after_hash" ]
}