#!/usr/bin/env bats

# tests/test_helper.bash is auto-loaded by bats from the parent tests/
# directory; do not `load test_helper` (would re-resolve from this dir).

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    export RDDF_PROJECT_ROOT="$REPO_ROOT"
}

@test "rddf contract-check: CLI 注册 (--help 列表包含 contract-check)" {
    cd "$REPO_ROOT"
    run python3 -m skills._lib.cli --help
    [[ "$output" == *"contract-check"* ]]
}

@test "rddf contract-check: 委托一致性 (--hub / --local / --cache-file 参数透传)" {
    cd "$REPO_ROOT"
    run python3 -m skills._lib.cli contract-check --help
    [[ "$output" == *"--hub"* ]]
    [[ "$output" == *"--local"* ]]
    [[ "$output" == *"--cache-file"* ]]
}

@test "rddf contract-check: 退出码传播 (non-breaking → exit 0)" {
    cd "$REPO_ROOT"
    FIXTURE_HUB="$REPO_ROOT/tests/fixtures/openapi/auth-v2-hub.yaml"
    FIXTURE_LOCAL_OK="$REPO_ROOT/tests/fixtures/openapi/auth-v2-local-ok.py"
    [[ -f "$FIXTURE_HUB" ]] || skip "fixture hub not present"
    [[ -f "$FIXTURE_LOCAL_OK" ]] || skip "fixture local-ok not present"
    run python3 -m skills._lib.cli contract-check \
        --hub "$FIXTURE_HUB" --local "$FIXTURE_LOCAL_OK"
    [ "$status" -eq 0 ]
}

@test "rddf contract-check: 退出码传播 (breaking → exit 1)" {
    cd "$REPO_ROOT"
    FIXTURE_HUB="$REPO_ROOT/tests/fixtures/openapi/auth-v2-hub.yaml"
    FIXTURE_LOCAL_BROKEN="$REPO_ROOT/tests/fixtures/openapi/auth-v2-local-broken.py"
    [[ -f "$FIXTURE_HUB" ]] || skip "fixture hub not present"
    [[ -f "$FIXTURE_LOCAL_BROKEN" ]] || skip "fixture local-broken not present"
    run python3 -m skills._lib.cli contract-check \
        --hub "$FIXTURE_HUB" --local "$FIXTURE_LOCAL_BROKEN"
    [ "$status" -eq 1 ]
}