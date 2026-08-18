#!/usr/bin/env bats

# tests/integration/test_readme_ci_examples.bats
# Verifies README.md §跨项目协同 章节含 GitHub Actions + GitLab CI 双 snippet

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    README="$REPO_ROOT/README.md"
}

@test "README §跨项目协同 章节含 'CI 集成示例' 子节" {
    [ -f "$README" ]
    run grep -c "#### CI 集成示例" "$README"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "README §跨项目协同 章节含 GitHub Actions yaml snippet" {
    run grep -A 80 "#### CI 集成示例" "$README"
    [[ "$output" == *"GitHub Actions"* ]]
    [[ "$output" == *"name: contract-check"* ]]
    [[ "$output" == *"actions/checkout"* ]]
    [[ "$output" == *"STRICT_CONTRACT_GATE"* ]]
}

@test "README §跨项目协同 章节含 GitLab CI yaml snippet" {
    run grep -A 60 "#### CI 集成示例" "$README"
    [[ "$output" == *"GitLab CI"* ]]
    [[ "$output" == *"contract-lint:"* ]]
    [[ "$output" == *"CI_PIPELINE_SOURCE"* ]]
    [[ "$output" == *"merge_request_event"* ]]
}

@test "README CI 示例同时覆盖 STRICT 和 SKIP 两种 env var" {
    run grep -A 60 "#### CI 集成示例" "$README"
    [[ "$output" == *"STRICT_CONTRACT_GATE"* ]]
    [[ "$output" == *"SKIP_CONTRACT_GATE"* ]]
}