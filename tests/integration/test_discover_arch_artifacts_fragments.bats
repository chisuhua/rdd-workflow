#!/usr/bin/env bats
# Test _lib/discover_roadmap_fragments.sh helper.
# ADR-0016 v2: new SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR env var + .rddf/roadmap default.

load ../test_helper

setup() {
    TMP=$(mktemp -d)
    cd "$TMP"
    git init -q .
    git config user.email "test@test.local" && git config user.name "test"
    mkdir -p docs/adr
    HELPER="${BATS_TEST_DIRNAME}/../../_lib/discover_roadmap_fragments.sh"
    export PROJECT_ROOT="$TMP"
}

teardown() {
    rm -rf "$TMP"
    unset SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR
    unset PROJECT_ROOT
}

@test "discover_roadmap_fragments_dir: env var override wins (even if missing)" {
    export SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR="/custom/fragments"
    source "$HELPER"
    # NOTE: do NOT use `run` or `$()` — both run in subshell, exports don't propagate
    discover_roadmap_fragments_dir > /tmp/discover_out_1
    [ "$?" -eq 0 ]
    [[ "$(cat /tmp/discover_out_1)" == "/custom/fragments" ]]
    [ "${DISCOVERED_ROADMAP_FRAGMENTS_DIR:-}" = "/custom/fragments" ]
    [ "${DISCOVERED_ROADMAP_FRAGMENTS_FOUND}" = "false" ]  # path doesn't exist
    [ "${DISCOVERED_ROADMAP_FRAGMENTS_TRIED}" = "1" ]
    rm -f /tmp/discover_out_1
}

@test "discover_roadmap_fragments_dir: env var override + path exists = found=true" {
    mkdir -p /tmp/custom-fragments-test
    export SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR="/tmp/custom-fragments-test"
    source "$HELPER"
    discover_roadmap_fragments_dir > /tmp/discover_out_2
    [ "$?" -eq 0 ]
    [[ "$(cat /tmp/discover_out_2)" == "/tmp/custom-fragments-test" ]]
    [ "${DISCOVERED_ROADMAP_FRAGMENTS_FOUND}" = "true" ]
    rm -rf /tmp/custom-fragments-test /tmp/discover_out_2
}

@test "discover_roadmap_fragments_dir: no env var + .rddf/roadmap exists = found=true" {
    unset SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR
    mkdir -p .rddf/roadmap/phases
    source "$HELPER"
    discover_roadmap_fragments_dir > /tmp/discover_out_3
    [ "$?" -eq 0 ]
    [[ "$(cat /tmp/discover_out_3)" == ".rddf/roadmap" ]]
    [ "${DISCOVERED_ROADMAP_FRAGMENTS_FOUND}" = "true" ]
    [ "${DISCOVERED_ROADMAP_FRAGMENTS_TRIED}" = "1" ]
    rm -f /tmp/discover_out_3
}

@test "discover_roadmap_fragments_dir: no env var + no .rddf/roadmap = default returned, found=false" {
    unset SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR
    source "$HELPER"
    discover_roadmap_fragments_dir > /tmp/discover_out_4
    [ "$?" -eq 0 ]
    [[ "$(cat /tmp/discover_out_4)" == ".rddf/roadmap" ]]
    [ "${DISCOVERED_ROADMAP_FRAGMENTS_FOUND}" = "false" ]
    rm -f /tmp/discover_out_4
}

@test "discover_roadmap_fragments_dir: rejects direct execution (sourced-only guard)" {
    run bash "$HELPER"
    [ "$status" -eq 1 ]
    [[ "$output" == *"must be sourced"* ]]
}
