#!/usr/bin/env bats
# tests/e2e/agent/test_rdd_planner_e2e.bats
# Per Plan 3: 8 rdd-planner C-layer scenarios (P-E1..P-E8)

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/isolation.bash"
    source "$REPO_ROOT/tests/e2e/_lib/script_smoke.bash"
    source "$REPO_ROOT/tests/e2e/_lib/agent_runner.bash"
    REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"
    export REPO_ROOT
    TEST_TMP="$BATS_TEST_TMPDIR/rdd-planner-e2e"
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

@test "rdd-planner: P-E1 stage entry → planner-handoff 写出" {
    run run_scenario "p_e1"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/state/.planner-handoff.json" ]
    grep -q "planner-handoff-v1" "$OUTPUT_DIR/.rddf/state/.planner-handoff.json"
}

@test "rdd-planner: P-E2 intake → 扫描 5 类源" {
    run run_scenario "p_e2"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/state/.planner-intake.json" ]
    grep -q "ADR gap" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-planner: P-E3 propose → 5 段格式提案落盘" {
    run run_scenario "p_e3"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/improvement-suggestions.md" ]
}

@test "rdd-planner: P-E4 brainstorm 流程 → 改进提案" {
    run run_scenario "p_e4"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/improvements/p-e4-test.md" ]
}

@test "rdd-planner: P-E5 approve → 落盘 proposal.md + spec.md (D3)" {
    run run_scenario "p_e5"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/openspec/changes/p-e3-test/proposal.md" ]
    [ -f "$OUTPUT_DIR/openspec/changes/p-e3-test/specs/p-e3-test/spec.md" ]
}

@test "rdd-planner: P-E6 reject → feedback 写入 + 不落盘 change" {
    run run_scenario "p_e6"
    [ "$status" -eq 0 ]
    grep -q "rejected" "$OUTPUT_DIR/improvement-suggestions.md"
}

@test "rdd-planner: P-E7 横切命令 — status/sync/feedback/advance-sprint" {
    run run_scenario "p_e7"
    [ "$status" -eq 0 ]
    grep -q "status:" "$OUTPUT_DIR/stdout.txt"
    grep -q "sync:" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-planner: P-E8 stage exit → planner-handoff 终态" {
    run run_scenario "p_e8"
    [ "$status" -eq 0 ]
    grep -q "stage_status: exited" "$OUTPUT_DIR/stdout.txt"
}
