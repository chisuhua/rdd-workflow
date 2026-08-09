#!/usr/bin/env bats
# Tests for approve_proposal.sh reading **特性** field from improvements head
# and using it as fallback for parent_feature when PARENT_FEATURE env var unset.
#
# Background: `add-proposal-deps-and-features` defined `**特性**` as the design-time
# feature tag, but approve_proposal.sh never parses it — parent_feature only honored
# the PARENT_FEATURE env var. These tests lock the missing fallback.

load ../test_helper

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    WORK_DIR="$(mktemp -d)"
    mkdir -p "$WORK_DIR/.rddf/state"
    mkdir -p "$WORK_DIR/openspec/changes"
    mkdir -p "$WORK_DIR/improvements"
    mkdir -p "$WORK_DIR/skills/guide-design/scripts"
    mkdir -p "$WORK_DIR/skills/_lib"

    # git init so approve_proposal.sh's `git add` succeeds (auto-stage step)
    git -C "$WORK_DIR" init -q
    git -C "$WORK_DIR" -c user.email=test@local -c user.name=test commit --allow-empty -q -m init
    # commit proposal-approved.md too so `git add` has something to track
    git -C "$WORK_DIR" add proposal-approved.md 2>/dev/null || true

    # Minimal proposal-approved.md (skeleton satisfies append_approved)
    cat > "$WORK_DIR/proposal-approved.md" <<EOF
# proposal-approved

| name | priority | status | completed_at |
|------|----------|--------|--------------|
EOF

    # Mirror the real state.sh so append_approved resolves (read-only calls)
    cp "$REPO_ROOT/skills/_lib/state.sh" "$WORK_DIR/skills/_lib/state.sh" 2>/dev/null || true
}

teardown() {
    rm -rf "$WORK_DIR"
}

_make_improvement() {
    local feature_value="$1"
    cat > "$WORK_DIR/improvements/demo.md" <<EOF
# demo

**优先级**: P1 | **来源**: bats
**阶段**: design | **分类**: workflow
**类型**: feature
**依赖**: | **特性**: ${feature_value}

## 架构依据

ADR-0003 reference.

## 范围

- a

## 关键场景

- b

## 技术约束

- c

## 验收标准

- [ ] d
EOF
}

@test "approve_proposal: reads 特性 from improvements head into parent_feature when env unset" {
    _make_improvement "wave-core"

    cd "$WORK_DIR"
    unset PARENT_FEATURE
    bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "demo" "P1" "$WORK_DIR" 2>&1 || true

    [ -f "$WORK_DIR/openspec/changes/demo/roadmap-meta.yaml" ]
    run grep -E '^parent_feature: "wave-core"' "$WORK_DIR/openspec/changes/demo/roadmap-meta.yaml"
    [ "$status" -eq 0 ]
}

@test "approve_proposal: PARENT_FEATURE env var wins over 特性 field" {
    _make_improvement "wave-core"

    cd "$WORK_DIR"
    PARENT_FEATURE="env-wins" \
        bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "demo" "P1" "$WORK_DIR" 2>&1 || true

    [ -f "$WORK_DIR/openspec/changes/demo/roadmap-meta.yaml" ]
    run grep -E '^parent_feature: "env-wins"' "$WORK_DIR/openspec/changes/demo/roadmap-meta.yaml"
    [ "$status" -eq 0 ]
}

@test "approve_proposal: empty 特性 field leaves parent_feature empty (no crash)" {
    _make_improvement ""

    cd "$WORK_DIR"
    unset PARENT_FEATURE
    bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "demo" "P1" "$WORK_DIR" 2>&1 || true

    [ -f "$WORK_DIR/openspec/changes/demo/roadmap-meta.yaml" ]
    # parent_feature line exists with empty quoted value (matches pre-fix behavior)
    run grep -E '^parent_feature: ""' "$WORK_DIR/openspec/changes/demo/roadmap-meta.yaml"
    [ "$status" -eq 0 ]
}