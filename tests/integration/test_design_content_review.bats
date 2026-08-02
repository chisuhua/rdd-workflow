#!/usr/bin/env bats
# E2E: design_content_review.sh warnings + STRICT blocking + SKIP bypass.

load ../test_helper

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    WORK_DIR="$(mktemp -d)"
    mkdir -p "$WORK_DIR/improvements"
}

teardown() {
    rm -rf "$WORK_DIR"
}

@test "content_review: passes on complete improvements" {
    cat > "$WORK_DIR/improvements/good.md" <<EOF
# good

**优先级**: P1 | **来源**: test
**阶段**: design | **分类**: workflow
**类型**: feature
**依赖**: | **特性**:

## 架构依据

ADR-0003.

## 范围

- a

## 关键场景

- b

## 技术约束

- c

## 验收标准

- [ ] d
EOF
    cd "$WORK_DIR"
    export IMPROVEMENTS_PATH="$WORK_DIR/improvements/good.md"
    export STRICT_DESIGN_GATE=no
    export SKIP_CONTENT_REVIEW=no
    run bash "$REPO_ROOT/skills/guide-design/scripts/design_content_review.sh"
    [ "$status" -eq 0 ]
}

@test "content_review: STRICT blocks on missing head fields" {
    cat > "$WORK_DIR/improvements/bad.md" <<EOF
# bad

## 架构依据

ADR-0003.

## 范围

- a

## 关键场景

- b

## 技术约束

- c

## 验收标准

- [ ] d
EOF
    cd "$WORK_DIR"
    export IMPROVEMENTS_PATH="$WORK_DIR/improvements/bad.md"
    export STRICT_DESIGN_GATE=yes
    export SKIP_CONTENT_REVIEW=no
    run bash "$REPO_ROOT/skills/guide-design/scripts/design_content_review.sh"
    [ "$status" -eq 1 ]
}

@test "content_review: SKIP bypasses regardless" {
    cd "$WORK_DIR"
    export IMPROVEMENTS_PATH="/nonexistent"
    export STRICT_DESIGN_GATE=yes
    export SKIP_CONTENT_REVIEW=yes
    run bash "$REPO_ROOT/skills/guide-design/scripts/design_content_review.sh"
    [ "$status" -eq 0 ]
}

@test "content_review: warning mode (no strict) exits 0 even with errors" {
    cat > "$WORK_DIR/improvements/bad.md" <<EOF
# bad
## 架构依据
no ADR
## 范围
- a
## 关键场景
- b
## 技术约束
- c
## 验收标准
- d
EOF
    cd "$WORK_DIR"
    export IMPROVEMENTS_PATH="$WORK_DIR/improvements/bad.md"
    export STRICT_DESIGN_GATE=no
    export SKIP_CONTENT_REVIEW=no
    run bash "$REPO_ROOT/skills/guide-design/scripts/design_content_review.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"WARNING"* ]] || [[ "$output" == *"missing"* ]]
}
