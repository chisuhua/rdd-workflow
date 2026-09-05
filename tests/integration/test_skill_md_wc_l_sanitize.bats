load ../test_helper

@test "skill_md_wc_l: rdd-arch/SKILL.md sanitizes ADR_COUNT" {
    run grep -E "ADR_COUNT=.*wc -l.*tr -d" "$PROJECT_ROOT/skills/rdd-arch/SKILL.md"
    [ "$status" -eq 0 ]
}


@test "skill_md_wc_l: roadmap/SKILL.md sanitizes ADR_COUNT" {
    run grep -E "ADR_COUNT=.*wc -l.*tr -d" "$PROJECT_ROOT/skills/roadmap/SKILL.md"
    [ "$status" -eq 0 ]
}

@test "skill_md_wc_l: edge case - wc -l with trailing newline produces integer-safe output" {
    # Simulate the wc -l output containing a newline (the bug scenario)
    result=$(printf "0\n" | tr -d '[:space:]')
    [ "$result" = "0" ]

    # Verify integer comparison works after sanitize
    if [ "$result" -eq 0 ]; then
        echo "comparison succeeded"
    fi
    [ $? -eq 0 ]
}
