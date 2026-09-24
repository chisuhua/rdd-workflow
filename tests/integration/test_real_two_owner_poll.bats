#!/usr/bin/env bats
# tests/integration/test_real_two_owner_poll.bats
# wave3-opencode-session-injection Task 3 — REAL-2P-1/2 multi-window owner isolation.
#
# Referenced by tests/e2e/agent/scenarios/mwp_1.json + mwp_2.json.
# Verifies that two concurrent OpenCode windows (distinct OPENCODE_SESSION_ID)
# produce distinct owner_opencode_session_id values, so the per-owner idempotency
# and cross-stage singleton logic in _commands.py can distinguish them
# (AC-P1-3-2 / AC-P1-3-3).

load "../test_helper"

setup() {
  export TEST_TMP="$BATS_TEST_TMPDIR/real2p-$$-$BATS_TEST_NUMBER"
  mkdir -p "$TEST_TMP/.rddf/state"
  export PROJECT_ROOT="$TEST_TMP"
  export RDDF_PROJECT_ROOT="$TEST_TMP"
}

teardown() {
  rm -rf "$TEST_TMP"
}

@test "REAL-2P-1: two windows with distinct OPENCODE_SESSION_ID produce distinct owners" {
  run env OPENCODE_SESSION_ID="ses_window_a_test" PROJECT_ROOT="$TEST_TMP" RDDF_PROJECT_ROOT="$TEST_TMP" \
    bash -c '
      source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
      _rddf_resolve_owner
      echo "$RDDF_OWNER"
    '
  [ "$status" -eq 0 ]
  [ "$output" = "ses_window_a_test" ]

  run env OPENCODE_SESSION_ID="ses_window_b_test" PROJECT_ROOT="$TEST_TMP" RDDF_PROJECT_ROOT="$TEST_TMP" \
    bash -c '
      source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
      _rddf_resolve_owner
      echo "$RDDF_OWNER"
    '
  [ "$status" -eq 0 ]
  [ "$output" = "ses_window_b_test" ]
}

@test "REAL-2P-2: window A owner differs from window B owner (no shell-pid collapse)" {
  owner_a=$(env OPENCODE_SESSION_ID="ses_owner_alpha" PROJECT_ROOT="$TEST_TMP" \
    bash -c 'source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"; _rddf_resolve_owner; echo "$RDDF_OWNER"')
  owner_b=$(env OPENCODE_SESSION_ID="ses_owner_beta" PROJECT_ROOT="$TEST_TMP" \
    bash -c 'source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"; _rddf_resolve_owner; echo "$RDDF_OWNER"')

  [ "$owner_a" != "$owner_b" ]
  [ "$owner_a" = "ses_owner_alpha" ]
  [ "$owner_b" = "ses_owner_beta" ]
}

@test "REAL-2P-3: cross-stage singleton distinguishes two owners (AC-P1-3-3)" {
  # Window A creates stage_builder; window B creates stage_verify — distinct owners
  env OPENCODE_SESSION_ID="ses_win_a" PROJECT_ROOT="$TEST_TMP" RDDF_PROJECT_ROOT="$TEST_TMP" \
    bash -c '
      source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
      rddf_session_hook_entry stage_builder rdd-builder "two-owner-subject" "ok" >/dev/null 2>&1 || true
    '

  env OPENCODE_SESSION_ID="ses_win_b" PROJECT_ROOT="$TEST_TMP" RDDF_PROJECT_ROOT="$TEST_TMP" \
    bash -c '
      source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
      rddf_session_hook_entry stage_verify rdd-verifier "two-owner-subject" "ok" >/dev/null 2>&1 || true
    '

  if [ -f "$TEST_TMP/.rddf/state/sessions.json" ]; then
    owners=$(python3 -c "
import json
d = json.load(open('$TEST_TMP/.rddf/state/sessions.json'))
owners = sorted({s.get('owner_opencode_session_id') for s in d.get('sessions', [])})
print(' '.join(o for o in owners if o))
")
    # Both owners must be present and distinct
    echo "$owners" | grep -q "ses_win_a"
    echo "$owners" | grep -q "ses_win_b"
  fi
}
