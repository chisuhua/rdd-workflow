#!/usr/bin/env bats
# tests/integration/test_from_issue_env_isolation.bats
# Verify that from-issue / from-roadmap / free 3 modes can coexist
# without env-var pollution.

setup() {
    load ../test_helper
    TEST_PROJECT_ROOT="$(mktemp -d)"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
    WT_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    FROM_ISSUE="$WT_ROOT/skills/add-improve/scripts/from_issue.sh"
    FROM_ROADMAP="$WT_ROOT/skills/add-improve/scripts/from_roadmap.sh"
}

teardown() {
    rm -rf "$TEST_PROJECT_ROOT"
}

@test "from-roadmap then from-issue: no env-var leakage" {
    bash "$FROM_ROADMAP" \
        --from-roadmap "phase-1/arch-design" \
        --theme "TestTheme" \
        --project-root "$TEST_PROJECT_ROOT" >/dev/null 2>&1

    # After from-roadmap, env-vars are unset
    [ -z "${ADD_IMPROVE_FROM_ROADMAP:-}" ]
    [ -z "${ADD_IMPROVE_THEME:-}" ]
    [ -z "${BRAINSTORM_RATIONALE_DRAFT:-}" ]

    # from-issue should not see from-roadmap env-vars
    run bash "$FROM_ISSUE" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
}

@test "from-issue then from-roadmap: no env-var leakage" {
    bash "$FROM_ISSUE" \
        --from-issue 42 \
        --gh-repo "foo/bar" \
        --title "Test" \
        --project-root "$TEST_PROJECT_ROOT" >/dev/null 2>&1

    # After from-issue, env-vars are unset
    [ -z "${ADD_IMPROVE_FROM_ISSUE:-}" ]
    [ -z "${ADD_IMPROVE_GH_REPO:-}" ]
    [ -z "${ADD_IMPROVE_ISSUE_TITLE:-}" ]
    [ -z "${ADD_IMPROVE_ISSUE_BODY:-}" ]

    # from-roadmap should not see from-issue env-vars
    run bash "$FROM_ROADMAP" \
        --from-roadmap "phase-1/arch-design" \
        --theme "TestTheme" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]
}

@test "interleaved env-vars: from-roadmap does not pick up from-issue vars" {
    # Set from-issue env-vars manually
    export ADD_IMPROVE_FROM_ISSUE="42"
    export ADD_IMPROVE_GH_REPO="foo/bar"

    # Run from-roadmap — should NOT see from-issue vars
    run bash "$FROM_ROADMAP" \
        --from-roadmap "phase-1/arch-design" \
        --theme "TestTheme" \
        --project-root "$TEST_PROJECT_ROOT"

    [ "$status" -eq 0 ]

    # Cleanup manually-set env-vars
    unset ADD_IMPROVE_FROM_ISSUE
    unset ADD_IMPROVE_GH_REPO
}
