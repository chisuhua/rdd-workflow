#!/usr/bin/env bats

load ../test_helper

SMART="$REPO_ROOT/skills/guide-ship/scripts/archive_change_smart.sh"

@test "archive smart: lightweight mode delegates to archive_change_for_mode" {
    [ -f "$SMART" ]
    grep -q 'archive_change_for_mode' "$SMART"
    grep -q 'detect_archive_mode' "$SMART"
}

@test "archive smart: worktree mode is detected through existing helper" {
    [ -f "$SMART" ]
    grep -qi 'detect_archive_mode.*project_root.*change_name' "$SMART"
}

@test "archive smart: validates iteration archived and task completion" {
    [ -f "$SMART" ]
    grep -q 'status.*archived' "$SMART"
    grep -q 'tasks_done.*tasks_total' "$SMART"
}

@test "archive smart: validates archive moves commit and clean tree" {
    [ -f "$SMART" ]
    grep -q 'git.*status.*porcelain' "$SMART"
    grep -q 'archive.*completed' "$REPO_ROOT/_lib/archive.sh"
}

@test "archive smart: accepts dry-run and strict flags" {
    [ -f "$SMART" ]
    grep -q -- '--dry-run' "$SMART"
    grep -q -- '--strict' "$SMART"
}

@test "archive smart: missing change directory fails with detailed error" {
    run bash "$SMART" definitely-missing-change
    [ "$status" -eq 1 ]
    [[ "$output" == *"change directory"* ]]
}
