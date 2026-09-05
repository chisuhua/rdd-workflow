#!/usr/bin/env bats
# Integration tests for _lib/wave_scheduler_hooks.sh
# Verifies bash wrapper contract: post_archive + entry_check functions.

load ../test_helper

@test "wave_scheduler: hook file exists at _lib/wave_scheduler_hooks.sh" {
    assert_file_exists "$REPO_ROOT/_lib/wave_scheduler_hooks.sh"
}

@test "wave_scheduler: wave_scheduler_post_archive function is defined" {
    source "$REPO_ROOT/_lib/wave_scheduler_hooks.sh"
    declare -F wave_scheduler_post_archive >/dev/null
}

@test "wave_scheduler: wave_scheduler_entry_check function is defined" {
    source "$REPO_ROOT/_lib/wave_scheduler_hooks.sh"
    declare -F wave_scheduler_entry_check >/dev/null
}

@test "wave_scheduler: post_archive prints suggestion when blocked change unblocked" {
    TMP_ROOT=$(mktemp -d)
    mkdir -p "$TMP_ROOT/.rddf/state"
    cat > "$TMP_ROOT/.rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-01-01T00:00:00Z",
  "current_phase": "v2.1",
  "changes": [
    {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
    {"name": "change-b", "status": "planned", "added_at": "2026-01-01T00:00:00Z", "blocker": "change-a"}
  ]
}
EOF
    export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
    source "$REPO_ROOT/_lib/wave_scheduler_hooks.sh"
    run wave_scheduler_post_archive "$TMP_ROOT" "change-a"
    [ "$status" -eq 0 ]
    [[ "$output" == *"change-b"* ]] || {
        echo "Expected output to mention change-b, got: $output"
        false
    }
    [[ "$output" == *"Wave suggestion"* ]] || {
        echo "Expected 'Wave suggestion' in output, got: $output"
        false
    }
    rm -rf "$TMP_ROOT"
}

@test "wave_scheduler: post_archive no recs prints nothing or minimal" {
    TMP_ROOT=$(mktemp -d)
    mkdir -p "$TMP_ROOT/.rddf/state"
    cat > "$TMP_ROOT/.rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-01-01T00:00:00Z",
  "current_phase": "v2.1",
  "changes": [
    {"name": "change-a", "status": "archived", "added_at": "2026-01-01T00:00:00Z"}
  ]
}
EOF
    export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
    source "$REPO_ROOT/_lib/wave_scheduler_hooks.sh"
    run wave_scheduler_post_archive "$TMP_ROOT" "change-a"
    [ "$status" -eq 0 ]
    [[ "$output" != *"Wave suggestion"* ]]
    rm -rf "$TMP_ROOT"
}

@test "wave_scheduler: post_archive missing iteration.json does not error" {
    TMP_ROOT=$(mktemp -d)
    export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
    source "$REPO_ROOT/_lib/wave_scheduler_hooks.sh"
    run wave_scheduler_post_archive "$TMP_ROOT" "change-a"
    [ "$status" -eq 0 ]
    rm -rf "$TMP_ROOT"
}

@test "wave_scheduler: entry_check prints when unblocked changes exist" {
    TMP_ROOT=$(mktemp -d)
    mkdir -p "$TMP_ROOT/.rddf/state"
    cat > "$TMP_ROOT/.rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-01-01T00:00:00Z",
  "current_phase": "v2.1",
  "changes": [
    {"name": "A", "status": "archived", "added_at": "2026-01-01T00:00:00Z"},
    {"name": "B", "status": "planned", "added_at": "2026-01-01T00:00:00Z", "blocker": "A"}
  ]
}
EOF
    export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
    source "$REPO_ROOT/_lib/wave_scheduler_hooks.sh"
    run wave_scheduler_entry_check "$TMP_ROOT" "rdd-planner"
    [ "$status" -eq 0 ]
    [[ "$output" == *"B"* ]]
    rm -rf "$TMP_ROOT"
}

@test "wave_scheduler: entry_check no recs does not error" {
    TMP_ROOT=$(mktemp -d)
    mkdir -p "$TMP_ROOT/.rddf/state"
    cat > "$TMP_ROOT/.rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-01-01T00:00:00Z",
  "current_phase": "v2.1",
  "changes": []
}
EOF
    export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
    source "$REPO_ROOT/_lib/wave_scheduler_hooks.sh"
    run wave_scheduler_entry_check "$TMP_ROOT" "rdd-planner"
    [ "$status" -eq 0 ]
    rm -rf "$TMP_ROOT"
}

