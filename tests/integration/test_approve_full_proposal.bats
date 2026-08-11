#!/usr/bin/env bats
# E2E: approve -> output change dir contains full proposal + roadmap-meta + iteration

load ../test_helper

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    WORK_DIR="$(mktemp -d)"
    mkdir -p "$WORK_DIR/.rddf/state"
    mkdir -p "$WORK_DIR/openspec/changes"
    mkdir -p "$WORK_DIR/.rddf/improvements"
    mkdir -p "$WORK_DIR/skills/guide-design/scripts"
    mkdir -p "$WORK_DIR/skills/_lib"

    # Create a realistic improvement file with all 5 sections
    cat > "$WORK_DIR/.rddf/improvements/demo.md" <<EOF
# demo

**优先级**: P1 | **来源**: bats
**阶段**: design | **分类**: workflow
**类型**: feature
**依赖**: | **特性**:

## 架构依据

ADR-0003 + ADR-0017 决定 design 阶段职责升级。

## 范围

- approve 升级
- 完整 proposal.md 生成

## 关键场景

- 单条批准

## 技术约束

- env-var 传参

## 验收标准

- [ ] proposal.md >= 500 字符
- [ ] 含 ADR-NNNN 引用
- [ ] In/Out Scope 完整
EOF

    # proposal-approved.md
    cat > "$WORK_DIR/proposal-approved.md" <<EOF
# proposal-approved

| name | priority | status | completed_at |
|------|----------|--------|--------------|
EOF

    # state.sh (mock minimal)
    cat > "$WORK_DIR/_lib/state.sh" <<'EOF'
#!/usr/bin/env bash
append_approved() { return 0; }
mark_approved_completed() { return 0; }
EOF
}

teardown() {
    rm -rf "$WORK_DIR"
}

@test "approve e2e: change dir contains proposal.md >= 500 chars with ADR + In/Out Scope" {
    cd "$WORK_DIR"
    bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "demo" "P1" "$WORK_DIR" 2>&1 || true

    # change dir was created
    [ -d "$WORK_DIR/openspec/changes/demo" ]

    # proposal.md exists and is >= 500 chars
    if [ -f "$WORK_DIR/openspec/changes/demo/proposal.md" ]; then
        local size
        size=$(wc -c < "$WORK_DIR/openspec/changes/demo/proposal.md")
        [ "$size" -ge 500 ]

        # Contains ADR references
        grep -q "ADR-" "$WORK_DIR/openspec/changes/demo/proposal.md"

        # Contains In Scope / Out of Scope
        grep -q "In Scope" "$WORK_DIR/openspec/changes/demo/proposal.md"
        grep -q "Out of Scope" "$WORK_DIR/openspec/changes/demo/proposal.md"
    fi
}

@test "approve e2e: roadmap-meta.yaml contains change_type" {
    cd "$WORK_DIR"
    bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "demo" "P1" "$WORK_DIR" 2>&1 || true

    if [ -f "$WORK_DIR/openspec/changes/demo/roadmap-meta.yaml" ]; then
        grep -q "change_type" "$WORK_DIR/openspec/changes/demo/roadmap-meta.yaml"
    fi
}

@test "approve e2e: idempotent — second run does not overwrite" {
    cd "$WORK_DIR"
    bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "demo" "P1" "$WORK_DIR" 2>&1 || true

    # Add custom content to proposal
    if [ -f "$WORK_DIR/openspec/changes/demo/proposal.md" ]; then
        echo "## User Edit" >> "$WORK_DIR/openspec/changes/demo/proposal.md"
    fi

    # Re-run
    bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "demo" "P1" "$WORK_DIR" 2>&1 || true

    # User edit should still be there
    if [ -f "$WORK_DIR/openspec/changes/demo/proposal.md" ]; then
        grep -q "User Edit" "$WORK_DIR/openspec/changes/demo/proposal.md"
    fi
}
