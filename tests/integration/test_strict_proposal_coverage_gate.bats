#!/usr/bin/env bats
# tests/integration/test_strict_proposal_coverage_gate.bats
# Integration tests for STRICT_PROPOSAL_COVERAGE gate behavior.

setup() {
    load ../test_helper
    WT_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    GATE_SCRIPT="$WT_ROOT/skills/guide-design/scripts/check_theme_coverage_gate.sh"
    TEST_PROJECT_ROOT="$(mktemp -d)"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/state"
}

teardown() {
    rm -rf "$TEST_PROJECT_ROOT"
}

setup_roadmap_with_themes() {
    local theme1="$1"
    local theme2="$2"
    local suffix="$3"
    cat > "$TEST_PROJECT_ROOT/roadmap.md" <<EOF
# Test Roadmap

### Phase 1: arch (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | ${theme1}${suffix}；${theme2} |
EOF
}

@test "STRICT_PROPOSAL_COVERAGE=yes blocks when uncovered themes exist" {
    setup_roadmap_with_themes "RBAC" "事件总线"
    unset STRICT_PROPOSAL_COVERAGE
    unset SKIP_PROPOSAL_COVERAGE
    export STRICT_PROPOSAL_COVERAGE=yes

    run bash "$GATE_SCRIPT" "$TEST_PROJECT_ROOT"

    unset STRICT_PROPOSAL_COVERAGE
    [ "$status" -ne 0 ]
    [[ "$output" == *"事件总线"* ]]
    [[ "$output" == *"STRICT_PROPOSAL_COVERAGE"* ]]
}

@test "STRICT_PROPOSAL_COVERAGE=yes passes when all themes covered" {
    setup_roadmap_with_themes "RBAC" "事件总线"
    cat > "$TEST_PROJECT_ROOT/.rddf/improvements/p1.md" <<EOF
# Test
**主题**: RBAC
EOF
    cat > "$TEST_PROJECT_ROOT/.rddf/improvements/p2.md" <<EOF
# Test
**主题**: 事件总线
EOF
    unset SKIP_PROPOSAL_COVERAGE
    export STRICT_PROPOSAL_COVERAGE=yes

    run bash "$GATE_SCRIPT" "$TEST_PROJECT_ROOT"

    unset STRICT_PROPOSAL_COVERAGE
    [ "$status" -eq 0 ]
    [[ "$output" == *"总主题: 2"* ]]
}

@test "default (no env var) is warning only — exit 0 with uncovered themes" {
    setup_roadmap_with_themes "RBAC" "事件总线"
    unset STRICT_PROPOSAL_COVERAGE
    unset SKIP_PROPOSAL_COVERAGE

    run bash "$GATE_SCRIPT" "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
    [[ "$output" == *"warning only"* ]]
    [[ "$output" == *"事件总线"* ]]
}

@test "SKIP_PROPOSAL_COVERAGE=yes bypasses strict gate" {
    setup_roadmap_with_themes "RBAC" "事件总线"
    unset STRICT_PROPOSAL_COVERAGE
    export STRICT_PROPOSAL_COVERAGE=yes
    export SKIP_PROPOSAL_COVERAGE=yes

    run bash "$GATE_SCRIPT" "$TEST_PROJECT_ROOT"

    unset STRICT_PROPOSAL_COVERAGE
    unset SKIP_PROPOSAL_COVERAGE
    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP_PROPOSAL_COVERAGE"* ]]
}

@test "~skipped~ themes excluded from denominator" {
    setup_roadmap_with_themes "RBAC" "事件总线" " ~skipped~"
    unset STRICT_PROPOSAL_COVERAGE
    unset SKIP_PROPOSAL_COVERAGE

    run bash "$GATE_SCRIPT" "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
    [[ "$output" == *"已跳过"* ]]
    [[ "$output" == *"总主题: 1"* ]]
}

@test "no themes → exit 0, skip gate" {
    cat > "$TEST_PROJECT_ROOT/roadmap.md" <<EOF
# Test Roadmap
### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 |
|--------|------|------|--------|
| arch-design | 架构 | 核心 | P0 |
EOF
    unset STRICT_PROPOSAL_COVERAGE
    unset SKIP_PROPOSAL_COVERAGE

    run bash "$GATE_SCRIPT" "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
    [[ "$output" == *"无 roadmap 主题约束"* ]]
}

@test "missing roadmap.md → exit 2 with error" {
    unset STRICT_PROPOSAL_COVERAGE
    unset SKIP_PROPOSAL_COVERAGE

    run bash "$GATE_SCRIPT" "$TEST_PROJECT_ROOT"

    [ "$status" -eq 2 ]
    [[ "$output" == *"roadmap.md not found"* ]]
}

@test "missing --project-root arg → exit 2" {
    unset STRICT_PROPOSAL_COVERAGE
    unset SKIP_PROPOSAL_COVERAGE

    run bash "$GATE_SCRIPT"

    [ "$status" -eq 2 ]
    [[ "$output" == *"Usage"* ]]
}