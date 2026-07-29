load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/improvements"
    cat > "$TEST_DIR/improvements/test-deferred.md" << 'EOF'
# test-deferred
**优先级**: P2 | **来源**: test
**阶段**: default | **分类**: general
**类型**: fix
**状态**: 已推迟
EOF
    cat > "$TEST_DIR/improvements/test-pending.md" << 'EOF'
# test-pending
**优先级**: P1 | **来源**: test
**阶段**: default | **分类**: general
**类型**: feature
EOF
}

@test "proposal_defer: list_improvements outputs 4 segments with status" {
    run bash -c "source '$REPO_ROOT/skills/_lib/state.sh' && list_improvements '$TEST_DIR'"
    [ "$status" -eq 0 ]
    # Should contain test-pending with default '待讨论'
    echo "$output" | grep -q '|待讨论'
    # Should contain test-deferred with '已推迟'
    echo "$output" | grep -q '|已推迟'
}

teardown() {
    rm -rf "$TEST_DIR"
}
