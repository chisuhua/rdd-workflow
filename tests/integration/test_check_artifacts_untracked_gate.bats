load ../test_helper

setup() {
    TEST_REPO="$BATS_TMPDIR/test-ship-plan-untracked"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO"
    cd "$TEST_REPO"
    git init -q
    git config user.email "t@t"
    git config user.name "t"
    git checkout -q -b main
    mkdir -p "openspec/changes/test-change/specs/foo"
    echo "schema: spec-driven" > openspec/changes/test-change/.openspec.yaml
    git add openspec/changes/test-change/.openspec.yaml
    git commit -q -m "init"
    source "$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh"
}

@test "check_artifacts_committed: clean tree passes" {
    cd "$TEST_REPO"
    PROJECT_ROOT="$TEST_REPO" run check_artifacts_committed "$TEST_REPO" "test-change"
    [ "$status" -eq 0 ]
}

@test "check_artifacts_committed: untracked files are ALLOWED (exit 0)" {
    cd "$TEST_REPO"
    echo "## ADDED Requirements" > openspec/changes/test-change/specs/foo/spec.md
    PROJECT_ROOT="$TEST_REPO" run check_artifacts_committed "$TEST_REPO" "test-change"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "untracked" ]]
    [[ "$output" =~ "不阻塞" ]]
}

@test "check_artifacts_committed: tracked modifications are BLOCKED (exit 1)" {
    cd "$TEST_REPO"
    echo "MODIFIED" >> openspec/changes/test-change/.openspec.yaml
    PROJECT_ROOT="$TEST_REPO" run check_artifacts_committed "$TEST_REPO" "test-change"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "未提交修改" ]]
    [[ "$output" =~ ".openspec.yaml" ]]
}

@test "check_artifacts_committed: --strict-untracked blocks untracked (exit 2)" {
    cd "$TEST_REPO"
    echo "## ADDED Requirements" > openspec/changes/test-change/specs/foo/spec.md
    PROJECT_ROOT="$TEST_REPO" run check_artifacts_committed "$TEST_REPO" "test-change" "yes"
    [ "$status" -eq 2 ]
    [[ "$output" =~ "strict-untracked" ]]
}

@test "check_artifacts_committed: STRICT_UNTRACKED env var works" {
    cd "$TEST_REPO"
    echo "## ADDED Requirements" > openspec/changes/test-change/specs/foo/spec.md
    PROJECT_ROOT="$TEST_REPO" STRICT_UNTRACKED=yes run check_artifacts_committed "$TEST_REPO" "test-change"
    [ "$status" -eq 2 ]
}

@test "check_artifacts_committed: deleted tracked artifact is BLOCKED as modification" {
    cd "$TEST_REPO"
    rm openspec/changes/test-change/.openspec.yaml
    PROJECT_ROOT="$TEST_REPO" run check_artifacts_committed "$TEST_REPO" "test-change"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "未提交修改" ]]
}

@test "check_artifacts_committed: nonexistent change dir fails" {
    cd "$TEST_REPO"
    PROJECT_ROOT="$TEST_REPO" run check_artifacts_committed "$TEST_REPO" "no-such-change"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "Artifacts 尚未提交" ]]
}