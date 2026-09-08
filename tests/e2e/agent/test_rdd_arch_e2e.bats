#!/usr/bin/env bats
# tests/e2e/agent/test_rdd_arch_e2e.bats
# Per Plan 3: 8 rdd-arch C-layer scenarios (A-E1..A-E8)

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/isolation.bash"
    source "$REPO_ROOT/tests/e2e/_lib/script_smoke.bash"
    source "$REPO_ROOT/tests/e2e/_lib/agent_runner.bash"
    REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"
    export REPO_ROOT
    TEST_TMP="$BATS_TEST_TMPDIR/rdd-arch-e2e"
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

@test "rdd-arch: A-E1 setup → arch discovery contract" {
    run run_scenario "a_e1"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/state/.arch-handoff.json" ]
    grep -q '"adr_dir":' "$OUTPUT_DIR/.rddf/state/.arch-handoff.json"
}

@test "rdd-arch: A-E2 ADR 创建 → 4 段格式落地" {
    run run_scenario "a_e2"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/docs/adr/ADR-0001-rdd-quick.md" ]
    grep -q "## Decision" "$OUTPUT_DIR/docs/adr/ADR-0001-rdd-quick.md"
}

@test "rdd-arch: A-E3 差距分析 → arch-quality-gate 通过" {
    run run_scenario "a_e3"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/state/.arch-quality-report.json" ]
}

@test "rdd-arch: A-E4 roadmap 定义 → phase 分配" {
    run run_scenario "a_e4"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/roadmap.md" ]
    grep -q "## Phase" "$OUTPUT_DIR/roadmap.md"
}

@test "rdd-arch: A-E5 arch-done gate pass" {
    run run_scenario "a_e5"
    [ "$status" -eq 0 ]
    grep -q "arch_done_status" "$OUTPUT_DIR/.rddf/state/.arch-handoff.json"
}

@test "rdd-arch: A-E6 arch-done gate fail — 0 ADR 阻断" {
    run run_scenario "a_e6"
    [ "$status" -eq 0 ]
    grep -q "至少需要 1 个 ADR" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-arch: A-E7 arch-handoff stale 检测" {
    run run_scenario "a_e7"
    [ "$status" -eq 0 ]
    grep -q "stale" "$OUTPUT_DIR/.rddf/state/.arch-handoff.json"
}

@test "rdd-arch: A-E8 隔离契约 — 不污染下游 planner state" {
    run run_scenario "a_e8"
    [ "$status" -eq 0 ]
    grep -q "zero_pollution: true" "$OUTPUT_DIR/stdout.txt"
}
