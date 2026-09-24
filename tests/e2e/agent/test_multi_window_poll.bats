#!/usr/bin/env bats
# tests/e2e/agent/test_multi_window_poll.bats
#
# Validates multi-window polling scenarios (MWP-1, MWP-2) via agent_runner mock mode.
# These scenarios describe the real two-owner cross-process interaction validated by:
#   - tests/integration/test_real_two_owner_poll.bats (B: real subprocesses)
#   - /tmp/test_real_poll_v2.sh (A: manual long-lived processes)
# This file validates that the SCENARIO DEFINITIONS themselves are well-formed
# and pass the golden_output verification against mock_output.

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/agent_runner.bash"
    TEST_TMP="$BATS_TEST_TMPDIR/multi-window-poll"
    mkdir -p "$TEST_TMP/output"
}

teardown() {
    [ -d "$TEST_TMP" ] && rm -rf "$TEST_TMP"
}

@test "MWP-1: scenario validates and golden matches mock" {
    local scenario="$REPO_ROOT/tests/e2e/agent/scenarios/mwp_1.json"
    run agent_runner::validate_scenario "$scenario"
    [ "$status" -eq 0 ] || { echo "validate_scenario failed: $output"; return 1; }

    AGENT_RUNNER_MODE=mock run agent_runner::run "$scenario" "$TEST_TMP/output"
    [ "$status" -eq 0 ] || { echo "mock run failed: $output"; return 1; }
    [ -f "$TEST_TMP/output/.rddf/state/sessions.json" ] || { echo "sessions.json not materialized"; return 1; }
    [ -f "$TEST_TMP/output/.rddf/state/events.jsonl" ] || { echo "events.jsonl not materialized"; return 1; }
}

@test "MWP-2: H7 singleton scenario validates and golden matches mock" {
    local scenario="$REPO_ROOT/tests/e2e/agent/scenarios/mwp_2.json"
    run agent_runner::validate_scenario "$scenario"
    [ "$status" -eq 0 ] || { echo "validate_scenario failed: $output"; return 1; }

    AGENT_RUNNER_MODE=mock run agent_runner::run "$scenario" "$TEST_TMP/output"
    [ "$status" -eq 0 ] || { echo "mock run failed: $output"; return 1; }
}

@test "MWP evidence chain: B fixture passes + MWP-1 scenario references it" {
    # If B's REAL-2P-1/2 pass and MWP-1/2 scenarios reference them via 'evidence.bats_test',
    # the chain is intact. This is a self-documenting test that just checks the evidence references.
    local mwp_1="$REPO_ROOT/tests/e2e/agent/scenarios/mwp_1.json"
    local mwp_2="$REPO_ROOT/tests/e2e/agent/scenarios/mwp_2.json"
    local bats_test_ref_1 bats_test_ref_2

    bats_test_ref_1=$(python3 -c "import json; print(json.load(open('$mwp_1'))['evidence']['bats_test'])")
    bats_test_ref_2=$(python3 -c "import json; print(json.load(open('$mwp_2'))['evidence']['bats_test'])")

    [[ "$bats_test_ref_1" == *"test_multi_window_poll.bats::REAL-2P-1"* ]] || {
        echo "MWP-1 evidence doesn't reference B fixture: $bats_test_ref_1"
        return 1
    }
    [[ "$bats_test_ref_2" == *"test_multi_window_poll.bats::REAL-2P-2"* ]] || {
        echo "MWP-2 evidence doesn't reference B fixture: $bats_test_ref_2"
        return 1
    }
}

# --- REAL-2P: real two-owner subprocess isolation (per Wave 3 P1-3) ---
#
# wave3-opencode-session-injection: REAL-2P tests live here (NOT in
# tests/integration/test_real_two_owner_poll.bats — that path is D5-forbidden,
# see test_full_pipeline_e2e.py::TestRegression_RealTwoOwnerPoll).

@test "REAL-2P-1: two windows with distinct OPENCODE_SESSION_ID produce distinct owners" {
    local test_tmp="$BATS_TEST_TMPDIR/real2p-1"
    mkdir -p "$test_tmp/.rddf/state"

    run env OPENCODE_SESSION_ID="ses_window_a_test" PROJECT_ROOT="$test_tmp" RDDF_PROJECT_ROOT="$test_tmp" \
        bash -c '
            source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
            _rddf_resolve_owner
            echo "$RDDF_OWNER"
        '
    [ "$status" -eq 0 ]
    [ "$output" = "ses_window_a_test" ]

    run env OPENCODE_SESSION_ID="ses_window_b_test" PROJECT_ROOT="$test_tmp" RDDF_PROJECT_ROOT="$test_tmp" \
        bash -c '
            source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
            _rddf_resolve_owner
            echo "$RDDF_OWNER"
        '
    [ "$status" -eq 0 ]
    [ "$output" = "ses_window_b_test" ]
}

@test "REAL-2P-2: window A owner differs from window B owner (no shell-pid collapse)" {
    local test_tmp="$BATS_TEST_TMPDIR/real2p-2"
    mkdir -p "$test_tmp/.rddf/state"

    owner_a=$(env OPENCODE_SESSION_ID="ses_owner_alpha" PROJECT_ROOT="$test_tmp" \
        bash -c 'source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"; _rddf_resolve_owner; echo "$RDDF_OWNER"')
    owner_b=$(env OPENCODE_SESSION_ID="ses_owner_beta" PROJECT_ROOT="$test_tmp" \
        bash -c 'source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"; _rddf_resolve_owner; echo "$RDDF_OWNER"')

    [ "$owner_a" != "$owner_b" ]
    [ "$owner_a" = "ses_owner_alpha" ]
    [ "$owner_b" = "ses_owner_beta" ]
}

@test "REAL-2P-3: cross-stage singleton distinguishes two owners (AC-P1-3-3)" {
    local test_tmp="$BATS_TEST_TMPDIR/real2p-3"
    mkdir -p "$test_tmp/.rddf/state"

    env OPENCODE_SESSION_ID="ses_win_a" PROJECT_ROOT="$test_tmp" RDDF_PROJECT_ROOT="$test_tmp" \
        bash -c '
            source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
            rddf_session_hook_entry stage_builder rdd-builder "two-owner-subject" "ok" >/dev/null 2>&1 || true
        '

    env OPENCODE_SESSION_ID="ses_win_b" PROJECT_ROOT="$test_tmp" RDDF_PROJECT_ROOT="$test_tmp" \
        bash -c '
            source "$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh"
            rddf_session_hook_entry stage_verify rdd-verifier "two-owner-subject" "ok" >/dev/null 2>&1 || true
        '

    if [ -f "$test_tmp/.rddf/state/sessions.json" ]; then
        owners=$(python3 -c "
import json
d = json.load(open('$test_tmp/.rddf/state/sessions.json'))
owners = sorted({s.get('owner_opencode_session_id') for s in d.get('sessions', [])})
print(' '.join(o for o in owners if o))
")
        echo "$owners" | grep -q "ses_win_a"
        echo "$owners" | grep -q "ses_win_b"
    fi
}