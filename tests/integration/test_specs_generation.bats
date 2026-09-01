#!/usr/bin/env bats
# E2E: approve_proposal.sh 在 design 阶段自动生成 specs/<name>/spec.md (D3)
# 覆盖 5 个场景: e2e 落盘 / idempotency / openspec validate / capabilities / acceptance

load ../test_helper

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    WORK_DIR="$(mktemp -d)"
    mkdir -p "$WORK_DIR/.rddf/state"
    mkdir -p "$WORK_DIR/openspec/changes"
    mkdir -p "$WORK_DIR/.rddf/improvements"
    mkdir -p "$WORK_DIR/skills/guide-design/scripts"
    mkdir -p "$WORK_DIR/_lib"
    mkdir -p "$WORK_DIR/skills/_lib"

    cat > "$WORK_DIR/skills/_lib/state.sh" <<'EOF'
#!/usr/bin/env bash
append_approved() { return 0; }
mark_approved_completed() { return 0; }
sweep_implemented_proposals() { return 0; }
sync_suggestions() { return 0; }
EOF

    git -C "$WORK_DIR" init -q
    git -C "$WORK_DIR" config user.email "test@test.t"
    git -C "$WORK_DIR" config user.name "test"

    cat > "$WORK_DIR/proposal-approved.md" <<'EOF'
# proposal-approved
| name | priority | status | completed_at |
|------|----------|--------|--------------|
EOF

    cp "$REPO_ROOT/skills/guide-design/scripts/generate_full_proposal.py" "$WORK_DIR/skills/guide-design/scripts/"
    cp "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" "$WORK_DIR/skills/guide-design/scripts/"

    export PROJECT_ROOT="$WORK_DIR"
}

teardown() {
    [ -n "$WORK_DIR" ] && rm -rf "$WORK_DIR"
}

write_improvement() {
    local name="$1"
    cat > "$WORK_DIR/.rddf/improvements/$name.md" <<EOF || true
# $name

**优先级**: P1 | **来源**: bats
**阶段**: v2.2 | **分类**: test
**类型**: feature

## 架构依据
bats test fixture.

## 范围
- in scope

## 关键场景

## 技术约束
- **MUST**: 自动生成 spec.md
- **MUST NOT**: 覆盖已有 specs/

## 验收标准
- [ ] 第一条 acceptance
- [ ] 第二条 acceptance

## Impact
EOF
    return 0
}

@test "specs-generate: end-to-end approve_proposal.sh creates specs/" {
    write_improvement e2e-test
    (cd "$WORK_DIR" && bash "$WORK_DIR/skills/guide-design/scripts/approve_proposal.sh" e2e-test P1 "$WORK_DIR") >/dev/null 2>&1
    [ -f "$WORK_DIR/openspec/changes/e2e-test/specs/e2e-test/spec.md" ]
    grep -q "## ADDED Requirements" "$WORK_DIR/openspec/changes/e2e-test/specs/e2e-test/spec.md"
}

@test "specs-generate: idempotent skip when specs/ exists" {
    write_improvement idem-test
    mkdir -p "$WORK_DIR/openspec/changes/idem-test/specs/idem-test"
    echo "PREEXISTING" > "$WORK_DIR/openspec/changes/idem-test/specs/idem-test/spec.md"
    (cd "$WORK_DIR" && bash "$WORK_DIR/skills/guide-design/scripts/approve_proposal.sh" idem-test P1 "$WORK_DIR") >/dev/null 2>&1
    grep -q "PREEXISTING" "$WORK_DIR/openspec/changes/idem-test/specs/idem-test/spec.md"
}

@test "specs-generate: requirements from Capabilities MUST" {
    write_improvement cap-test
    (cd "$WORK_DIR" && bash "$WORK_DIR/skills/guide-design/scripts/approve_proposal.sh" cap-test P1 "$WORK_DIR") >/dev/null 2>&1
    grep -q "### Requirement: capability-3" "$WORK_DIR/openspec/changes/cap-test/specs/cap-test/spec.md"
    grep -q "MUST" "$WORK_DIR/openspec/changes/cap-test/specs/cap-test/spec.md"
}

@test "specs-generate: scenarios from acceptance checkboxes" {
    write_improvement acc-test
    (cd "$WORK_DIR" && bash "$WORK_DIR/skills/guide-design/scripts/approve_proposal.sh" acc-test P1 "$WORK_DIR") >/dev/null 2>&1
    grep -q "### Requirement: acceptance-1" "$WORK_DIR/openspec/changes/acc-test/specs/acc-test/spec.md"
    grep -q "#### Scenario:" "$WORK_DIR/openspec/changes/acc-test/specs/acc-test/spec.md"
}

@test "specs-generate: validates against openspec validate v1.4 (no deltas found error)" {
    if ! command -v openspec >/dev/null 2>&1; then
        skip "openspec CLI not available"
    fi
    write_improvement validate-test
    (cd "$WORK_DIR" && bash "$WORK_DIR/skills/guide-design/scripts/approve_proposal.sh" validate-test P1 "$WORK_DIR") >/dev/null 2>&1
    cd "$WORK_DIR"
    run openspec validate validate-test --json
    [ "$status" -eq 0 ]
    echo "$output" | grep -qv "No deltas found"
}
