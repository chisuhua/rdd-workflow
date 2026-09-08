#!/usr/bin/env bats
# tests/e2e/agent/test_rdd_quick_e2e.bats
# Per Plan 2 Task 5: 8 rdd-quick C-layer scenarios (Q-E1..Q-E8)
# Default mode: mock (CI safe). With RDDF_AGENT_E2E=1 + agent CLI: real mode.

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/isolation.bash"
    source "$REPO_ROOT/tests/e2e/_lib/script_smoke.bash"
    source "$REPO_ROOT/tests/e2e/_lib/agent_runner.bash"
    REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"
    export REPO_ROOT
    TEST_TMP="$BATS_TEST_TMPDIR/rdd-quick-e2e"
    FAKE_ROOT="$TEST_TMP/fake-project"
    OUTPUT_DIR="$TEST_TMP/output"
    mkdir -p "$FAKE_ROOT" "$OUTPUT_DIR"
    script_smoke::setup_fake_project "$FAKE_ROOT"
    isolation::snapshot_repo_state "$TEST_TMP/isolation-baseline.txt"
}

teardown() {
    if [ -f "$TEST_TMP/isolation-baseline.txt" ]; then
        isolation::verify_zero_pollution "$TEST_TMP/isolation-baseline.txt" || true
    fi
    script_smoke::cleanup_fake_project "$FAKE_ROOT"
    [ -d "$TEST_TMP" ] && rm -rf "$TEST_TMP"
}

# Common test body: run a scenario in mock mode and verify
run_scenario_in_mock_mode() {
    local scenario_id="$1"
    local scenario="$BATS_TEST_DIRNAME/scenarios/${scenario_id}.json"

    agent_runner::validate_scenario "$scenario"

    AGENT_RUNNER_MODE=mock agent_runner::run "$scenario" "$OUTPUT_DIR"
    agent_runner::verify "$OUTPUT_DIR" "$scenario"
}

@test "rdd-quick: Q-E1 P0 简单提案 → 脚手架 plan" {
    run run_scenario_in_mock_mode "q_e1"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/plans/quick-add-helper-fn.md" ]
    [[ "$(cat "$OUTPUT_DIR/stdout.txt")" == *"Step 1: Write the failing test"* ]]
}

@test "rdd-quick: Q-E2 P1 复杂提案触发 Metis/Oracle 评审" {
    run run_scenario_in_mock_mode "q_e2"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/plans/quick-migrate-pg-v15.md" ]
    grep -q "reviewed_by: metis+oracle" "$OUTPUT_DIR/.rddf/plans/quick-migrate-pg-v15.md"
}

@test "rdd-quick: Q-E3 P1 简单提案直入 P2（跳过 review）" {
    run run_scenario_in_mock_mode "q_e3"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/plans/quick-fix-typo.md" ]
    # Verify no Metis/Oracle mention
    ! grep -q "Metis" "$OUTPUT_DIR/stdout.txt" || ! grep -q "Oracle" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-quick: Q-E4 P2 TDD 5 步就地执行" {
    run run_scenario_in_mock_mode "q_e4"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/tests/test_helper.py" ]
    [ -f "$OUTPUT_DIR/helper.py" ]
    [ -f "$OUTPUT_DIR/.rddf/state/.quick-history.jsonl" ]
    grep -q '"name": "add-helper-fn"' "$OUTPUT_DIR/.rddf/state/.quick-history.jsonl"
    grep -q '"outcome": "completed"' "$OUTPUT_DIR/.rddf/state/.quick-history.jsonl"
}

@test "rdd-quick: Q-E5 P3 全部 AC pass → completed" {
    run run_scenario_in_mock_mode "q_e5"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/state/.ac-verdict-quick-add-helper-fn.json" ]
    grep -q '"status": "pass"' "$OUTPUT_DIR/.rddf/state/.ac-verdict-quick-add-helper-fn.json"
    grep -q "1/1 pass" "$OUTPUT_DIR/.rddf/state/.quick-history.jsonl"
}

@test "rdd-quick: Q-E6 P3-P4 部分 AC fail → retry 1/3" {
    run run_scenario_in_mock_mode "q_e6"
    [ "$status" -eq 0 ]
    local lines
    lines=$(wc -l < "$OUTPUT_DIR/.rddf/state/.quick-history.jsonl")
    [ "$lines" -ge 2 ]
    # First entry: unverified, retry_count=1
    head -1 "$OUTPUT_DIR/.rddf/state/.quick-history.jsonl" | grep -q '"outcome": "unverified"'
    # Last entry: completed, retry_count=1
    tail -1 "$OUTPUT_DIR/.rddf/state/.quick-history.jsonl" | grep -q '"outcome": "completed"'
}

@test "rdd-quick: Q-E7 P4 retry 3/3 仍 fail → escalate" {
    run run_scenario_in_mock_mode "q_e7"
    [ "$status" -eq 0 ]
    grep -q "=== Escalation Summary ===" "$OUTPUT_DIR/stdout.txt"
    grep -q '"outcome": "escalated"' "$OUTPUT_DIR/.rddf/state/.quick-history.jsonl"
    grep -q '"retry_count": 3' "$OUTPUT_DIR/.rddf/state/.quick-history.jsonl"
    grep -q '"upgraded_to_change": null' "$OUTPUT_DIR/.rddf/state/.quick-history.jsonl"
}

@test "rdd-quick: Q-E8 隔离契约 — 不污染四阶段路径" {
    run run_scenario_in_mock_mode "q_e8"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/isolation_audit.json" ]
    grep -q "zero_pollution: true" "$OUTPUT_DIR/stdout.txt"
    grep -q "6/6 locked paths unchanged" "$OUTPUT_DIR/stdout.txt"
}
