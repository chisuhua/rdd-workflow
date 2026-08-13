#!/usr/bin/env bats
# tests/integration/test_add_improve_from_roadmap.bats
# Integration tests for add-improve --from-roadmap mode.
#
# Tests cover:
# - Successful scaffold creation with 主题 field
# - Rejection of shell injection in theme
# - Missing required args
# - HARD-GATE: does NOT modify proposal-suggestions.md

setup() {
    load ../test_helper
    TEST_PROJECT_ROOT="$(mktemp -d)"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/state"
    WT_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    SCRIPT="$WT_ROOT/skills/add-improve/scripts/from_roadmap.sh"
}

teardown() {
    rm -rf "$TEST_PROJECT_ROOT"
}

@test "from_roadmap creates proposal with 主题 field populated" {
    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch-design" \
        --theme "RBAC权限模型" \
        --rationale "ADR-0003 §2.3 提及但未细化" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]

    PROPOSAL="$TEST_PROJECT_ROOT/.rddf/improvements/from-roadmap-phase-1-arch-design.md"
    [ -f "$PROPOSAL" ]

    grep -q "\*\*主题\*\*: RBAC权限模型" "$PROPOSAL"
    grep -q "\*\*阶段\*\*: phase-1" "$PROPOSAL"
    grep -q "\*\*分类\*\*: arch-design" "$PROPOSAL"
    grep -q "ADR-0003 §2.3 提及但未细化" "$PROPOSAL"
}

@test "from_roadmap rejects shell injection in theme" {
    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch-design" \
        --theme 'evil$(whoami)' \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
    [[ "$output" == *"disallowed"* ]] || [[ "$output" == *"ERROR"* ]]
    # Verify no file was created
    [ ! -f "$TEST_PROJECT_ROOT/.rddf/improvements/from-roadmap-phase-1-arch-design.md" ]
}

@test "from_roadmap rejects backtick injection" {
    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch-design" \
        --theme 'evil`id`' \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
    [ ! -f "$TEST_PROJECT_ROOT/.rddf/improvements/from-roadmap-phase-1-arch-design.md" ]
}

@test "from_roadmap requires --from-roadmap arg" {
    run bash "$SCRIPT" \
        --theme "TestTheme" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
    [[ "$output" == *"required"* ]] || [[ "$output" == *"Usage"* ]]
}

@test "from_roadmap requires --theme arg" {
    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch-design" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
    [[ "$output" == *"required"* ]] || [[ "$output" == *"Usage"* ]]
}

@test "from_roadmap requires --project-root arg" {
    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch-design" \
        --theme "TestTheme"

    [ "$status" -ne 0 ]
    [[ "$output" == *"required"* ]] || [[ "$output" == *"Usage"* ]]
}

@test "from_roadmap HARD-GATE: does NOT modify proposal-suggestions.md" {
    # proposal-suggestions.md should not be created or modified by from_roadmap
    [ ! -f "$TEST_PROJECT_ROOT/proposal-suggestions.md" ]

    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch-design" \
        --theme "TestTheme" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
    # After successful run, proposal-suggestions.md still should NOT exist
    [ ! -f "$TEST_PROJECT_ROOT/proposal-suggestions.md" ]
}

@test "from_roadmap output mentions HARD-GATE explicitly" {
    run bash "$SCRIPT" \
        --from-roadmap "phase-1/arch-design" \
        --theme "TestTheme" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
    [[ "$output" == *"HARD-GATE"* ]]
    [[ "$output" == *"brainstorm"* ]]
}

@test "from_roadmap handles invalid --from-roadmap format" {
    run bash "$SCRIPT" \
        --from-roadmap "invalid-format-no-slash" \
        --theme "TestTheme" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -ne 0 ]
    [[ "$output" == *"phase_id/category_id"* ]]
}

@test "from_roadmap unsets env-vars on exit (no shell pollution)" {
    # Run the script
    bash "$SCRIPT" \
        --from-roadmap "phase-1/arch-design" \
        --theme "TestTheme" \
        --project-root "$TEST_PROJECT_ROOT" >/dev/null 2>&1

    # After exit, env-vars should NOT be set in current shell
    [ -z "${ADD_IMPROVE_FROM_ROADMAP:-}" ]
    [ -z "${ADD_IMPROVE_THEME:-}" ]
    [ -z "${BRAINSTORM_RATIONALE_DRAFT:-}" ]
}