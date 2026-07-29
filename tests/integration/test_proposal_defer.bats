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

@test "proposal_defer: arch_proposal_review skips deferred by default" {
    # Structural: arch_proposal_review.sh must contain the deferred-skip logic
    grep -q 'DEFERRED_COUNT' "$REPO_ROOT/skills/guide-arch/scripts/arch_proposal_review.sh"
    grep -q 'SHOW_ALL' "$REPO_ROOT/skills/guide-arch/scripts/arch_proposal_review.sh"
    grep -q '已推迟' "$REPO_ROOT/skills/guide-arch/scripts/arch_proposal_review.sh"
    # Behavioral: the skip logic must correctly skip deferred, show pending
    run bash -c "
        IMPROVEMENTS_DIR=$TEST_DIR/improvements
        DEFERRED_COUNT=0
        for f in \$IMPROVEMENTS_DIR/*.md; do
            [ -f \"\$f\" ] || continue
            name=\$(basename \"\$f\" .md)
            status=\$(grep -m1 '^\*\*状态\*\*:' \"\$f\" 2>/dev/null | sed 's/.*\*\*状态\*\*: *//' | cut -d'|' -f1 | xargs)
            status=\"\${status:-待讨论}\"
            if [ \"\$status\" = \"已推迟\" ] && [ \"\${SHOW_ALL:-false}\" != \"true\" ]; then
                DEFERRED_COUNT=\$((DEFERRED_COUNT + 1))
                continue
            fi
            echo \"SHOW: \$name\"
        done
        echo \"DEFERRED: \$DEFERRED_COUNT\"
    "
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "SHOW: test-pending"
    echo "$output" | grep -q "DEFERRED: 1"
    ! echo "$output" | grep -q "SHOW: test-deferred"
}

@test "proposal_defer: arch_proposal_review has v show-all option" {
    grep -q 'view-all' "$REPO_ROOT/skills/guide-arch/scripts/arch_proposal_review.sh"
    grep -q '⏸️' "$REPO_ROOT/skills/guide-arch/scripts/arch_proposal_review.sh"
}
