#!/usr/bin/env bats
# tests/e2e/agent/test_rdd_builder_e2e.bats
# Per Plan 3: 12 rdd-builder C-layer scenarios (B-E1..B-E12)
# Default mode: mock (CI safe). Real mode: RDDF_AGENT_E2E=1 + agent CLI.

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/isolation.bash"
    source "$REPO_ROOT/tests/e2e/_lib/script_smoke.bash"
    source "$REPO_ROOT/tests/e2e/_lib/agent_runner.bash"
    REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"
    export REPO_ROOT
    TEST_TMP="$BATS_TEST_TMPDIR/rdd-builder-e2e"
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

@test "rdd-builder: B-E1 P0 approval happy → D3 spec-delta 落盘" {
    run run_scenario "b_e1"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/openspec/changes/e2e-b1/specs/e2e-b1/spec.md" ]
}

@test "rdd-builder: B-E2 P0 reject → exit 1 + planner-feedback" {
    run run_scenario "b_e2"
    [ "$status" -eq 0 ]
    grep -q "reject" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-builder: B-E3 P1 plan gen → TDD 5 步 plan 文件" {
    run run_scenario "b_e3"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/plans/e2e-b3.md" ]
}

@test "rdd-builder: B-E4 P1.5 deps 分析 + execution_mode 决策" {
    run run_scenario "b_e4"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/state/deps-analysis.json" ]
}

@test "rdd-builder: B-E5 P1.5 风险关键词 → worktree 模式" {
    run run_scenario "b_e5"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/state/.plan-handoff.json" ]
}

@test "rdd-builder: B-E6 P2 lightweight 模式 → 主仓 commit" {
    run run_scenario "b_e6"
    [ "$status" -eq 0 ]
    grep -q "feat(e2e-b6)" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-builder: B-E7 P2 worktree 模式 → 隔离 commit" {
    run run_scenario "b_e7"
    [ "$status" -eq 0 ]
    grep -q "worktree created" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-builder: B-E8 P2.5 review 4-option dispatch" {
    run run_scenario "b_e8"
    [ "$status" -eq 0 ]
    grep -q "review action: merge" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-builder: B-E9 P3 archive happy path" {
    run run_scenario "b_e9"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/openspec/specs/e2e-b9/spec.md" ]
}

@test "rdd-builder: B-E10 P3 archive gate 阻断 — 0 commits" {
    run run_scenario "b_e10"
    [ "$status" -eq 0 ]
    grep -q "0 new commits" "$OUTPUT_DIR/stdout.txt"
}

@test "rdd-builder: B-E11 P3 → P1 verifier 失败回环" {
    run run_scenario "b_e11"
    [ "$status" -eq 0 ]
    [ -f "$OUTPUT_DIR/.rddf/state/.plan-handoff.json" ]
}

@test "rdd-builder: B-E12 隔离契约 — 不污染 rdd-quick 路径" {
    run run_scenario "b_e12"
    [ "$status" -eq 0 ]
    grep -q "zero_pollution: true" "$OUTPUT_DIR/stdout.txt"
}
