#!/usr/bin/env bats
# tests/e2e/agent/test_rdd_verifier_e2e.bats
# Per Plan 3: 8 rdd-verifier C-layer scenarios (V-E1..V-E8)

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/isolation.bash"
    source "$REPO_ROOT/tests/e2e/_lib/script_smoke.bash"
    source "$REPO_ROOT/tests/e2e/_lib/agent_runner.bash"
    REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"
    export REPO_ROOT
    TEST_TMP="$BATS_TEST_TMPDIR/rdd-verifier-e2e"
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

run_scenario() {
    local id="$1"
    local scenario="$BATS_TEST_DIRNAME/scenarios/${id}.json"
    agent_runner::validate_scenario "$scenario"
    AGENT_RUNNER_MODE=mock agent_runner::run "$scenario" "$OUTPUT_DIR"
    agent_runner::verify "$OUTPUT_DIR" "$scenario"
}

@test "rdd-verifier: V-E1 读 plan ## Acceptance → 提取 AC" {
    run run_scenario "v_e1"
    [ "$status" -eq 0 ]
    grep -q '"ac_id": "AC-1"' "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-verifier: V-E2 读代码 → 6 字段 verdict JSON 构造" {
    run run_scenario "v_e2"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/state/.ac-verdict-test.json" ]
    grep -q '"status":' "$OUTPUT_DIR/.rddf/state/.ac-verdict-test.json"
}

@test "rdd-verifier: V-E3 pass 分类 → 升 archive 路径" {
    run run_scenario "v_e3"
    [ "$status" -eq 0 ]
    grep -q "All ACs passed" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-verifier: V-E4 fail → implementation_gap → 回 P2" {
    run run_scenario "v_e4"
    [ "$status" -eq 0 ]
    grep -q "implementation_gap" "$OUTPUT_DIR/stdout.txt"
    [ -f "$OUTPUT_DIR/.rddf/state/.ac-verdict-test-gap.json" ]
}

@test "rdd-verifier: V-E5 fail → proposal_drift → 回 P1" {
    run run_scenario "v_e5"
    [ "$status" -eq 0 ]
    grep -q "proposal_drift" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-verifier: V-E6 partial 分类 — 部分通过" {
    run run_scenario "v_e6"
    [ "$status" -eq 0 ]
    grep -q "pass=2/3" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-verifier: V-E7 3 次重试上限 → escal" {
    run run_scenario "v_e7"
    [ "$status" -eq 0 ]
    grep -q "max retries exceeded" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-verifier: V-E8 离线 / 无 LLM 凭据时 graceful skip" {
    run run_scenario "v_e8"
    [ "$status" -eq 0 ]
    grep -q "skip" "$OUTPUT_DIR/stdout.txt"
}
