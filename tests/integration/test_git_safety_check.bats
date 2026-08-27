load ../test_helper

setup() {
    TEST_REPO="$BATS_TMPDIR/test-git-safety-check"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO"
    cd "$TEST_REPO"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git checkout -q -b main
    echo "init" > foo.txt
    git add foo.txt
    git commit -q -m "init"
    SCRIPT="$PROJECT_ROOT/skills/guide-ship/scripts/git_safety_check.sh"
}

teardown() {
    rm -rf "$TEST_REPO"
}

@test "git_safety_check: clean tree passes" {
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "工作树干净" ]]
}

@test "git_safety_check: untracked files are OK (exit 0)" {
    touch newfile.txt
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "untracked" ]]
    [[ "$output" =~ "合法 ship 阶段新增" ]]
}

@test "git_safety_check: tracked modification warns (exit 0)" {
    echo "modified" >> foo.txt
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "工作树不干净" ]]
    [[ "$output" =~ "WARNING" ]]
}

@test "git_safety_check: tracked modification BLOCKS with STRICT_COMMIT_SCOPE=yes" {
    echo "modified" >> foo.txt
    PROJECT_ROOT="$TEST_REPO" STRICT_COMMIT_SCOPE=yes run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "STRICT_COMMIT_SCOPE" ]]
    [[ "$output" =~ "blocking" ]]
}

@test "git_safety_check: --strict CLI flag enables STRICT mode" {
    echo "modified" >> foo.txt
    PROJECT_ROOT="$TEST_REPO" run bash "$SCRIPT" --strict
    [ "$status" -eq 1 ]
}

@test "git_safety_check: missing PROJECT_ROOT is graceful" {
    PROJECT_ROOT="/nonexistent/path" run bash "$SCRIPT"
    [ "$status" -ne 0 ]
}