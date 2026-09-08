#!/usr/bin/env bats
# tests/e2e/_lib/test_script_smoke.bats
# Self-test for script_smoke.bash (per 2026-09-08-e2e-test-plan-phase1 Task 2)
# Will be deleted in Task 14 after real coverage lives in tests/e2e/script/.

load ../../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/script_smoke.bash"
    export SMOKE_FAKE_ROOT="$BATS_TEST_TMPDIR/fake"
    export SMOKE_REPO_ROOT="$REPO_ROOT"
}

teardown() {
    [ -n "$SMOKE_FAKE_ROOT" ] && [ -d "$SMOKE_FAKE_ROOT" ] && rm -rf "$SMOKE_FAKE_ROOT"
}

@test "script_smoke::setup_fake_project creates git repo + openspec skeleton" {
    script_smoke::setup_fake_project "$SMOKE_FAKE_ROOT"
    [ -d "$SMOKE_FAKE_ROOT/.git" ]
    [ -d "$SMOKE_FAKE_ROOT/openspec/changes" ]
    [ -d "$SMOKE_FAKE_ROOT/openspec/specs" ]
    [ -d "$SMOKE_FAKE_ROOT/.rddf/state" ]
}

@test "script_smoke::invoke_phase returns 127 when phase script not found" {
    script_smoke::setup_fake_project "$SMOKE_FAKE_ROOT"
    run script_smoke::invoke_phase "nonexistent.sh" "test" "$SMOKE_FAKE_ROOT" --auto-approve
    [ "$status" -eq 127 ]
}
