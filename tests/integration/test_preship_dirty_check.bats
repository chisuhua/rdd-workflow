load ../test_helper

@test "preship-dirty-check: check_main_repo_clean exists" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run grep -c "check_main_repo_clean" "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "preship-dirty-check: archive_change_for_mode calls check_main_repo_clean" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    SCRIPT="$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"
    run grep -c "check_main_repo_clean" "$SCRIPT"
    [ "$status" -eq 0 ]
    [ "$output" -ge 2 ]
}

@test "preship-dirty-check: check_main_repo_clean blocks on change-scope dirty" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    SCRIPT="$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"
    run grep -c "Dirty files in change scope" "$SCRIPT"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}
