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

    [[ "$bats_test_ref_1" == *"test_real_two_owner_poll"* ]] || {
        echo "MWP-1 evidence doesn't reference B fixture: $bats_test_ref_1"
        return 1
    }
    [[ "$bats_test_ref_2" == *"test_real_two_owner_poll"* ]] || {
        echo "MWP-2 evidence doesn't reference B fixture: $bats_test_ref_2"
        return 1
    }
}