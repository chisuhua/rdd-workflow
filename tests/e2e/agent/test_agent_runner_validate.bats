#!/usr/bin/env bats
# tests/e2e/agent/test_agent_runner_validate.bats
# Per Plan 2 Task 1: agent_runner.bash validate mode tests (4 cases)

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/agent_runner.bash"
    TEST_TMP="$BATS_TEST_TMPDIR/agent-runner-validate"
    mkdir -p "$TEST_TMP"
}

teardown() {
    [ -d "$TEST_TMP" ] && rm -rf "$TEST_TMP"
}

@test "agent_runner::validate_scenario: well-formed scenario passes" {
    cat > "$TEST_TMP/good.json" <<'JSON'
{
  "scenario_id": "T-V-1",
  "skill": "rdd-quick",
  "input": {"command": "echo"},
  "golden_output": {"stdout_contains": ["hello"]},
  "isolation": {"locked_paths": [".rddf"]}
}
JSON
    run agent_runner::validate_scenario "$TEST_TMP/good.json"
    [ "$status" -eq 0 ]
}

@test "agent_runner::validate_scenario: missing required field fails" {
    cat > "$TEST_TMP/bad.json" <<'JSON'
{
  "scenario_id": "T-V-2",
  "skill": "rdd-quick"
}
JSON
    run agent_runner::validate_scenario "$TEST_TMP/bad.json"
    [ "$status" -eq 1 ]
    [[ "$output" == *"missing required fields"* ]]
}

@test "agent_runner::validate_scenario: malformed JSON fails" {
    echo "{ not valid json" > "$TEST_TMP/malformed.json"
    run agent_runner::validate_scenario "$TEST_TMP/malformed.json"
    [ "$status" -eq 2 ]
    [[ "$output" == *"malformed JSON"* ]]
}

@test "agent_runner::validate_scenario: golden_output empty fails" {
    cat > "$TEST_TMP/empty-golden.json" <<'JSON'
{
  "scenario_id": "T-V-3",
  "skill": "rdd-quick",
  "input": {"command": "echo"},
  "golden_output": {},
  "isolation": {"locked_paths": []}
}
JSON
    run agent_runner::validate_scenario "$TEST_TMP/empty-golden.json"
    [ "$status" -eq 1 ]
    [[ "$output" == *"golden_output must have"* ]]
}
