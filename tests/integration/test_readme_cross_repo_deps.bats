#!/usr/bin/env bats

# tests/integration/test_readme_cross_repo_deps.bats
# Verifies README §跨项目协同 章节含 '跨仓库依赖示例' 子节 + 必备内容

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    README="$REPO_ROOT/README.md"
}

@test "README 含 '跨仓库依赖示例' 子节" {
    run grep -c "#### 跨仓库依赖示例" "$README"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "README 跨仓库依赖示例含 rddf deps cross-repo 命令" {
    run grep -A 60 "#### 跨仓库依赖示例" "$README"
    [[ "$output" == *"rddf deps cross-repo"* ]]
    [[ "$output" == *"--spokes"* ]]
}

@test "README 跨仓库依赖示例含 Mermaid 图" {
    run grep -A 80 "#### 跨仓库依赖示例" "$README"
    [[ "$output" == *"mermaid"* ]]
    [[ "$output" == *"graph TD"* ]]
}

@test "README 跨仓库依赖示例含 STRICT_DEPS_GATE 启用方法" {
    run grep -A 80 "#### 跨仓库依赖示例" "$README"
    [[ "$output" == *"STRICT_DEPS_GATE"* ]]
    [[ "$output" == *"SKIP_DEPS_GATE"* ]]
}

@test "README 跨仓库依赖示例含推荐顺序表格" {
    run grep -A 80 "#### 跨仓库依赖示例" "$README"
    [[ "$output" == *"parallel_group"* ]]
    [[ "$output" == *"blocker"* ]]
}