#!/usr/bin/env bats
# tests/e2e/agent/test_agent_runner_mock.bats
# Per Plan 2 Task 2: agent_runner.bash mock mode tests (3 cases)

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/agent_runner.bash"
    TEST_TMP="$BATS_TEST_TMPDIR/agent-runner-mock"
    mkdir -p "$TEST_TMP/output"
}

teardown() {
    [ -d "$TEST_TMP" ] && rm -rf "$TEST_TMP"
}

@test "agent_runner mock mode: materializes mock_output files" {
    cat > "$TEST_TMP/scenario.json" <<'JSON'
{
  "scenario_id": "T-M-1",
  "skill": "rdd-quick",
  "input": {"command": "scaffold_plan.sh", "args": ["--name", "x"]},
  "golden_output": {
    "files": [{"path": ".rddf/plans/quick-x.md", "must_exist": true}],
    "stdout_contains": ["Step 1: Write the failing test"]
  },
  "mock_output": {
    "files": {
      ".rddf/plans/quick-x.md": "# Quick Plan: x\n\nStep 1: Write the failing test\n"
    },
    "stdout": "Step 1: Write the failing test\nCreated plan: quick-x.md\n"
  },
  "isolation": {"locked_paths": [".rddf"]}
}
JSON

    AGENT_RUNNER_MODE=mock run agent_runner::run "$TEST_TMP/scenario.json" "$TEST_TMP/output"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/output/.rddf/plans/quick-x.md" ]
    [ -f "$TEST_TMP/output/stdout.txt" ]
}

@test "agent_runner mock mode: verify passes when golden matches mock" {
    cat > "$TEST_TMP/scenario.json" <<'JSON'
{
  "scenario_id": "T-M-2",
  "skill": "rdd-quick",
  "input": {"command": "echo"},
  "golden_output": {
    "files": [{"path": "result.txt", "must_exist": true}],
    "stdout_contains": ["hello world"]
  },
  "mock_output": {
    "files": {"result.txt": "ok"},
    "stdout": "hello world\n"
  },
  "isolation": {"locked_paths": []}
}
JSON

    AGENT_RUNNER_MODE=mock agent_runner::run "$TEST_TMP/scenario.json" "$TEST_TMP/output"
    run agent_runner::verify "$TEST_TMP/output" "$TEST_TMP/scenario.json"
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK verify"* ]]
}

@test "agent_runner mock mode: verify fails when golden missing" {
    cat > "$TEST_TMP/scenario.json" <<'JSON'
{
  "scenario_id": "T-M-3",
  "skill": "rdd-quick",
  "input": {"command": "echo"},
  "golden_output": {
    "files": [{"path": "missing.txt", "must_exist": true}]
  },
  "mock_output": {"files": {}, "stdout": ""},
  "isolation": {"locked_paths": []}
}
JSON

    AGENT_RUNNER_MODE=mock agent_runner::run "$TEST_TMP/scenario.json" "$TEST_TMP/output"
    run agent_runner::verify "$TEST_TMP/output" "$TEST_TMP/scenario.json"
    [ "$status" -ne 0 ]
    [[ "$output" == *"file missing"* ]]
}
