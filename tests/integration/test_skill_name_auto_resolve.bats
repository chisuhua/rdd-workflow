load ../test_helper

@test "resolve-skill-name: script exists" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run test -f "$PROJECT_ROOT/_lib/resolve_skill_name.sh"
    [ "$status" -eq 0 ]
}

@test "resolve-skill-name: short name resolves to full name" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    TMP_LIST=$(mktemp)
    echo "rdd-workflow/skills/rdd-workflow-writing-plans" > "$TMP_LIST"
    echo "rdd-workflow/skills/guide" >> "$TMP_LIST"

    source "$PROJECT_ROOT/_lib/resolve_skill_name.sh"
    run resolve_skill_name "rdd-workflow-writing-plans" "$TMP_LIST"
    [ "$status" -eq 0 ]
    [[ "$output" == *"rdd-workflow/skills/rdd-workflow-writing-plans"* ]]
    rm -f "$TMP_LIST"
}

@test "resolve-skill-name: no match returns error with suggestions" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    TMP_LIST=$(mktemp)
    echo "rdd-workflow/skills/guide" > "$TMP_LIST"
    echo "rdd-workflow/skills/rdd-builder" >> "$TMP_LIST"

    source "$PROJECT_ROOT/_lib/resolve_skill_name.sh"
    run resolve_skill_name "nonexistent" "$TMP_LIST"
    [ "$status" -eq 1 ]
    [[ "$output" == *"No skill matches"* ]]
    rm -f "$TMP_LIST"
}

@test "resolve-skill-name: ambiguity errors with all matches" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    TMP_LIST=$(mktemp)
    echo "org/skill-a" > "$TMP_LIST"
    echo "other/skill-a" >> "$TMP_LIST"

    source "$PROJECT_ROOT/_lib/resolve_skill_name.sh"
    run resolve_skill_name "skill-a" "$TMP_LIST"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Ambiguous"* ]]
    rm -f "$TMP_LIST"
}
