#!/usr/bin/env bats
# tests/agent/test_agent_runner_real.bats
# Per Plan 2 Task 3: agent_runner.bash real mode tests (2 cases)

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/agent_runner.bash"
    TEST_TMP="$BATS_TEST_TMPDIR/agent-runner-real"
    mkdir -p "$TEST_TMP/output"
}

teardown() {
    [ -d "$TEST_TMP" ] && rm -rf "$TEST_TMP"
}

@test "agent_runner detect_mode: real when RDDF_AGENT_E2E=1 and CLI present" {
    # Stub an agent CLI for the test
    local fake_bin="$TEST_TMP/bin"
    mkdir -p "$fake_bin"
    cat > "$fake_bin/opencode" <<'STUB'
#!/usr/bin/env bash
echo "fake agent response"
STUB
    chmod +x "$fake_bin/opencode"

    PATH="$fake_bin:$PATH" RDDF_AGENT_E2E=1 run agent_runner::detect_mode
    [ "$status" -eq 0 ]
    [ "$output" = "real" ]
}

@test "agent_runner detect_mode: falls back to mock when CLI missing" {
    # Empty PATH to ensure no agent CLI
    PATH="/usr/bin:/bin" RDDF_AGENT_E2E=1 AGENT_RUNNER_MODE="" _CURRENT_SCENARIO_PATH="$TEST_TMP/nonexistent.json" \
        run agent_runner::detect_mode
    [ "$status" -eq 0 ]
    # When RDDF_AGENT_E2E=1 but no CLI, falls back to mock/validate via the AGENT_RUNNER_MODE env path
    [[ "$output" =~ ^(validate|mock)$ ]]
}
