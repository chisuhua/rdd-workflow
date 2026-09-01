#!/usr/bin/env bats
# Integration: design-done gate accepts status with suffix (regression test for this bug)

load ../test_helper

@test "design-done: gate accepts 已批准 (suffix) without failing" {
    TMP=$(mktemp -d)
    cat > "$TMP/suggestions.md" <<'EOF'
| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
| P1-change | P0 | test | 2026-09-01 | 已批准 (2026-09-01, 关联 phase-4) |
EOF
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    source "$REPO_ROOT/skills/guide-design/scripts/design_done_check.sh"
    check_design_done_gate "$TMP/suggestions.md"
    rm -rf "$TMP"
}

@test "design-done: gate accepts 延迟 (suffix) for legacy deferred proposals" {
    TMP=$(mktemp -d)
    cat > "$TMP/suggestions.md" <<'EOF'
| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
| legacy | P2 | test | 2026-08-26 | 延迟 (2026-08-28, 维持 v3.2 deferred 决策)  |
EOF
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    source "$REPO_ROOT/skills/guide-design/scripts/design_done_check.sh"
    check_design_done_gate "$TMP/suggestions.md"
    rm -rf "$TMP"
}
