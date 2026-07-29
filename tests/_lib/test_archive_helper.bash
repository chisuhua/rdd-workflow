#!/usr/bin/env bash
# Archive test helper - shared setup for archive-related bats tests.
#
# Functions:
#   archive_test_setup <change_name> - create temp git repo with OpenSpec structure
#   archive_test_teardown           - clean up temp repo
#
# Exports:
#   TEST_REPO_DIR      - absolute path to temp repo
#   TEST_CHANGE_NAME   - change name (defaults to "test-change")
#   TEST_PROJECT_ROOT  - alias of TEST_REPO_DIR

archive_test_setup() {
    local change_name="${1:-test-change}"
    TEST_REPO_DIR="$(mktemp -d)"
    cd "$TEST_REPO_DIR" || return 1
    git init -q -b master
    git config user.email "test@test.com"
    git config user.name "Test"
    touch README.md
    git add README.md
    git commit -q -m "initial"
    mkdir -p "openspec/changes/$change_name"
    mkdir -p openspec/changes/archive
    mkdir -p openspec/specs
    mkdir -p .rddf/state
    TEST_CHANGE_NAME="$change_name"
    TEST_PROJECT_ROOT="$TEST_REPO_DIR"
    export TEST_REPO_DIR TEST_CHANGE_NAME TEST_PROJECT_ROOT
}

archive_test_teardown() {
    if [ -n "$TEST_REPO_DIR" ] && [ -d "$TEST_REPO_DIR" ]; then
        cd / || true
        rm -rf "$TEST_REPO_DIR"
    fi
    unset TEST_REPO_DIR TEST_CHANGE_NAME TEST_PROJECT_ROOT
}
