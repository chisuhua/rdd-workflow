#!/usr/bin/env bats
# tests/integration/test_rdd_arch_cli.bats
# Stage 3 Change 4: rdd-arch CLI subcommand integration.

load ../test_helper

@test "rddf arch: --help shows status / handoff / feedback subcommands" {
    run python3 -m _lib.cli arch --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "status" ]]
    [[ "$output" =~ "handoff" ]]
    [[ "$output" =~ "feedback" ]]
}

@test "rddf arch status: shows 'No planner feedback' when feedback absent" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state"
    run python3 -m _lib.cli arch status --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "rdd-arch" ]]
    [[ "$output" =~ "No planner feedback" ]] || [[ "$output" =~ "(no arch-done yet)" ]]
}

@test "rddf arch status: includes planner summary line when feedback exists" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state"
    cat > "$TEST_TMP/.rddf/state/.arch-handoff.json" <<'JSON'
{"version": 2, "adr_count": 3, "current_phase": "phase-1"}
JSON
    cat > "$TEST_TMP/.rddf/state/.planner-feedback.json" <<'JSON'
{
  "schema": "planner-feedback-v1",
  "version": 1,
  "branch": "master",
  "codebase_commit": "abc123",
  "feedbacks": [],
  "summary": {"open_critical": 2, "open_warning": 1, "open_info": 0,
              "acknowledged": 0, "resolved": 0, "dismissed": 0}
}
JSON
    run python3 -m _lib.cli arch status --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "phase-1" ]]
    [[ "$output" =~ "3 ADRs" ]]
    [[ "$output" =~ "2 critical" ]]
    [[ "$output" =~ "1 warning" ]]
}

@test "rddf arch handoff: prints current .arch-handoff.json contents" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state"
    cat > "$TEST_TMP/.rddf/state/.arch-handoff.json" <<'JSON'
{"version": 2, "adr_count": 0, "current_phase": "default"}
JSON
    run python3 -m _lib.cli arch handoff --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"version": 2' ]]
}

@test "rddf arch handoff: returns clean message when file absent" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state"
    run python3 -m _lib.cli arch handoff --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "No .arch-handoff.json" ]]
}

@test "rddf arch feedback: prints empty notice when no planner-feedback.json" {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/state"
    run python3 -m _lib.cli arch feedback --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "No planner feedback" ]]
}