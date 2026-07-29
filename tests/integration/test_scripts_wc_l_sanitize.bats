load ../test_helper

@test "scripts_wc_l_sanitize: arch_env_check.sh sanitizes wc -l" {
    run grep -E "wc -l.*tr -d" "$PROJECT_ROOT/skills/guide-arch/scripts/arch_env_check.sh"
    [ "$status" -eq 0 ]
}

@test "scripts_wc_l_sanitize: arch_gap_analysis.sh sanitizes wc -l" {
    run grep -E "wc -l.*tr -d" "$PROJECT_ROOT/skills/guide-arch/scripts/arch_gap_analysis.sh"
    [ "$status" -eq 0 ]
}

@test "scripts_wc_l_sanitize: plan_done_gate.sh sanitizes wc -l" {
    run grep -E "wc -l.*tr -d" "$PROJECT_ROOT/skills/guide-plan/scripts/plan_done_gate.sh"
    [ "$status" -eq 0 ]
}

@test "scripts_wc_l_sanitize: plan_intake.sh sanitizes wc -l" {
    run grep -E "wc -l.*tr -d" "$PROJECT_ROOT/skills/guide-plan/scripts/plan_intake.sh"
    [ "$status" -eq 0 ]
}

@test "scripts_wc_l_sanitize: ship_done.sh sanitizes wc -l" {
    run grep -E "wc -l.*tr -d" "$PROJECT_ROOT/skills/guide-ship/scripts/ship_done.sh"
    [ "$status" -eq 0 ]
}

@test "scripts_wc_l_sanitize: ship_plan.sh sanitizes wc -l" {
    run grep -E "wc -l.*tr -d" "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
    [ "$status" -eq 0 ]
}
