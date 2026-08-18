#!/usr/bin/env bats

# fix-orphan-hub-gates-wiring: wire check_hub_pending / check_cross_repo_approvals
# into check_design_done_gate() (skills/guide-design/SKILL.md Phase 4).
#
# The gate function is extracted verbatim from SKILL.md (same technique as
# test_design_done_gate.bats) so the tests exercise the real shipped code.

load ../test_helper

_extract_gate() {
    sed -n '/^check_design_done_gate() {/,/^}$/p' "$REPO_ROOT/skills/guide-design/SKILL.md"
}

setup() {
    BATS_TEST_TMPDIR="$(mktemp -d)"
    export PROJECT_ROOT="$BATS_TEST_TMPDIR"
    mkdir -p "$BATS_TEST_TMPDIR/.rddf/state"
    eval "$(_extract_gate)"
    # All proposals already decided → the legacy pending check passes.
    cat > "$BATS_TEST_TMPDIR/proposal-suggestions.md" <<EOF
# 提案池

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [a](.rddf/improvements/a.md) | P1 | src | 2026-08-01T00:00:00Z | 已批准 |
EOF
}

teardown() {
    [ -n "$BATS_TEST_TMPDIR" ] && rm -rf "$BATS_TEST_TMPDIR"
}

_write_pending_hub_issue() {
    cat > "$BATS_TEST_TMPDIR/.rddf/state/.cross-repo-pending.json" <<EOF
{"version": 1, "entries": [{"hub_issue_url": "https://github.com/org/rdd-hub/issues/42", "gate_type": "Design-Gate", "expected_status": "approved", "created_at": "2026-08-15T16:00:00Z", "status": "pending"}]}
EOF
}

_write_unapproved_cross_repo_change() {
    # cross-repo-federation change without an approved audit entry
    mkdir -p "$BATS_TEST_TMPDIR/openspec/changes/some-cross-repo-change"
    cat > "$BATS_TEST_TMPDIR/openspec/changes/some-cross-repo-change/roadmap-meta.yaml" <<EOF
phase: core-impl
category: cross-repo-federation
change_type: fix
priority: P1
EOF
}

@test "design-done-hub-gates: default + hub pending → exit 1" {
    _write_pending_hub_issue
    run check_design_done_gate
    [ "$status" -eq 1 ]
    [[ "$output" == *"Hub"* || "$output" == *"hub"* ]]
}

@test "design-done-hub-gates: default + cross_repo_audit 含未批准 → exit 1" {
    _write_unapproved_cross_repo_change
    run check_design_done_gate
    [ "$status" -eq 1 ]
    [[ "$output" == *"cross-repo"* || "$output" == *"批准"* ]]
}

@test "design-done-hub-gates: SKIP_HUB_CHECK=true → exit 0 (含 audit)" {
    _write_pending_hub_issue
    _write_unapproved_cross_repo_change
    export SKIP_HUB_CHECK=true
    run check_design_done_gate
    [ "$status" -eq 0 ]
}

@test "design-done-hub-gates: 空 audit + 空 pending → exit 0 默认通过" {
    run check_design_done_gate
    [ "$status" -eq 0 ]
    [[ "$output" == *"✅"* ]]
}
