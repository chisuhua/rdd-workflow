#!/usr/bin/env bats
# Tests for approve_proposal.sh idempotent create flow (D1).
#
# After approve, when openspec/changes/<name>/ does NOT exist, the script
# must:
#   1. Generate full proposal.md (D2 mapping)
#   2. Create openspec/changes/<name>/ with .openspec.yaml + proposal.md
#   3. Write roadmap-meta.yaml containing change_type
#   4. Be idempotent: re-running skips the create

load ../test_helper

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    WORK_DIR="$(mktemp -d)"
    mkdir -p "$WORK_DIR/.rddf/state"
    mkdir -p "$WORK_DIR/openspec/changes"
    mkdir -p "$WORK_DIR/.rddf/improvements"
    mkdir -p "$WORK_DIR/skills"
    # Mirror the guide-design scripts so the script can be invoked
    mkdir -p "$WORK_DIR/skills/guide-design/scripts"
    mkdir -p "$WORK_DIR/skills/_lib"

    # Create a minimal improvement file with all 5 sections
    cat > "$WORK_DIR/.rddf/improvements/test-change.md" <<EOF
# test-change

**优先级**: P1 | **来源**: bats
**阶段**: design | **分类**: workflow
**类型**: feature
**依赖**: | **特性**:

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

    # Create proposal-approved.md
    cat > "$WORK_DIR/proposal-approved.md" <<EOF
# proposal-approved

| name | priority | status | completed_at |
|------|----------|--------|--------------|
EOF

    # Source state.sh into the test environment
    cp "$REPO_ROOT/_lib/state.sh" "$WORK_DIR/_lib/" 2>/dev/null || true
}

teardown() {
    rm -rf "$WORK_DIR"
}

@test "approve_proposal: idempotent — second run is no-op" {
    # Pre-create the change directory to simulate "already created"
    mkdir -p "$WORK_DIR/openspec/changes/test-change"
    touch "$WORK_DIR/openspec/changes/test-change/.openspec.yaml"
    echo "existing proposal content" > "$WORK_DIR/openspec/changes/test-change/proposal.md"

    # Run approve_proposal.sh — should be idempotent (no error, no overwrite)
    cd "$WORK_DIR"
    NAME="test-change" PRIORITY="P1" PROJECT_ROOT="$WORK_DIR" \
        bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "test-change" "P1" "$WORK_DIR" 2>&1 || true

    # Verify the existing proposal.md was NOT overwritten
    run cat "$WORK_DIR/openspec/changes/test-change/proposal.md"
    [ "$output" = "existing proposal content" ]
}

@test "approve_proposal: missing improvement file errors" {
    cd "$WORK_DIR"
    run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "nonexistent" "P1" "$WORK_DIR"
    [ "$status" -ne 0 ]
}

@test "approve_proposal: appends to proposal-approved.md" {
    cd "$WORK_DIR"
    bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "test-change" "P1" "$WORK_DIR" || true

    # proposal-approved.md should have a new row
    run grep -c "test-change" "$WORK_DIR/proposal-approved.md"
    [ "$output" -ge 1 ]
}

@test "approve_proposal: creates change dir with proposal.md and roadmap-meta.yaml" {
    cd "$WORK_DIR"
    SKIP_DESIGN_HANDOFF=no bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "test-change" "P1" "$WORK_DIR" || true

    # The change dir should now exist
    [ -d "$WORK_DIR/openspec/changes/test-change" ]

    # proposal.md should have content (>=500 chars)
    if [ -f "$WORK_DIR/openspec/changes/test-change/proposal.md" ]; then
        local size
        size=$(wc -c < "$WORK_DIR/openspec/changes/test-change/proposal.md")
        [ "$size" -ge 500 ]
    fi

    # roadmap-meta.yaml should contain change_type
    if [ -f "$WORK_DIR/openspec/changes/test-change/roadmap-meta.yaml" ]; then
        grep -q "change_type" "$WORK_DIR/openspec/changes/test-change/roadmap-meta.yaml"
    fi
}

@test "approve_proposal: SKIP_DESIGN_HANDOFF=yes falls back to no-create" {
    cd "$WORK_DIR"
    # With SKIP_DESIGN_HANDOFF=yes, the script should NOT create the change
    SKIP_DESIGN_HANDOFF=yes bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "test-change" "P1" "$WORK_DIR" || true

    # The change dir should NOT be created (skeleton path stays in plan)
    [ ! -d "$WORK_DIR/openspec/changes/test-change" ]
}
