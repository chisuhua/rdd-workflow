load ../test_helper

@test "guide-cross-validate: scan-state has filesystem cross-validation" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    SCRIPT="$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"

    run grep -c "FS_ACTIVE_COUNT" "$SCRIPT"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "guide-cross-validate: scan-state checks archive directory exclusion" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    SCRIPT="$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"

    run grep -c "archive/" "$SCRIPT"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "guide-cross-validate: stale handoff detection recommends guide-arch" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    SCRIPT="$PROJECT_ROOT/skills/guide/scripts/scan-state.sh"

    run grep -c "stale" "$SCRIPT"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}
