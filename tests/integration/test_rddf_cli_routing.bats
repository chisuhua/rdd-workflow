#!/usr/bin/env bats

# fix-cli-routing-cross-repo-commands: lock CLI routing for the 3 cross-repo
# subcommands documented as MUST-level in ADR-0030/README but previously
# missing from _lib/cli/__init__.py::_ROUTES (returned "unknown command").

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
}

@test "rddf sync-hub: CLI 注册 (--help 返回帮助, 不再是 unknown command)" {
    cd "$REPO_ROOT"
    run python3 -m skills._lib.cli sync-hub --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--contract"* ]]
    [[ "$output" != *"unknown command"* ]]
}

@test "rddf watch-hub: CLI 注册 (--help 返回帮助, 不再是 unknown command)" {
    cd "$REPO_ROOT"
    run python3 -m skills._lib.cli watch-hub --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--once"* ]]
    [[ "$output" != *"unknown command"* ]]
}

@test "rddf deps cross-repo: 子路由分发 (--help 返回 cross-repo 帮助)" {
    cd "$REPO_ROOT"
    run python3 -m skills._lib.cli deps cross-repo --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--spokes"* ]]
    [[ "$output" != *"unknown command"* ]]
}
