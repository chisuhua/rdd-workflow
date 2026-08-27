load ../test_helper

setup() {
    TEST_REPO="$BATS_TMPDIR/test-change-split-detect"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO/.rddf/improvements"
    cd "$TEST_REPO"
    SCRIPT="$PROJECT_ROOT/skills/guide-design/scripts/change_split_detect.sh"
}

teardown() {
    rm -rf "$TEST_REPO"
}

write_proposal() {
    local name="$1"
    local body="$2"
    cat > ".rddf/improvements/$name.md" <<EOF
# $name

$body
EOF
}

@test "change_split_detect: no shared files when proposals are disjoint" {
    write_proposal "p1" "## 范围

- 修改 \`docs/adr/ADR-0001.md\`
"
    write_proposal "p2" "## 范围

- 修改 \`tests/unit/test_foo.py\`
"
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "无共享文件冲突" ]]
}

@test "change_split_detect: detects shared file (warn mode)" {
    write_proposal "p1" "## 范围

- 修改 \`AGENTS.md\` line 72
"
    write_proposal "p2" "## 范围

- 修改 \`AGENTS.md\` line 84
"
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "共享文件" ]]
    [[ "$output" =~ "AGENTS.md" ]]
    [[ "$output" =~ "p1" ]]
    [[ "$output" =~ "p2" ]]
}

@test "change_split_detect: JSON mode structured output" {
    write_proposal "p1" "## 范围

- 修改 \`AGENTS.md\`
"
    write_proposal "p2" "## 范围

- 修改 \`AGENTS.md\`
"
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT" --json
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"conflicts":' ]]
    [[ "$output" =~ '"file":"AGENTS.md"' ]]
    [[ "$output" =~ '"proposals":["p1","p2"]' ]]
}

@test "change_split_detect: missing improvements dir is graceful" {
    rm -rf "$TEST_REPO/.rddf"
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "improvements dir not found" ]]
}

@test "change_split_detect: empty improvements dir reports no conflicts" {
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "无共享文件冲突" ]]
}

@test "change_split_detect: ignores backticked content outside 范围 section" {
    # 范围 节之外不应被识别 (e.g., ## 验收 或 ## 架构依据)
    write_proposal "p1" "## 范围

- 修改 \`AGENTS.md\`

## 验收

- \`tests/test_foo.py\` 应该不被识别为范围文件
"
    write_proposal "p2" "## 范围

- 修改 \`tests/test_bar.py\`
"
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "无共享文件冲突" ]]
}