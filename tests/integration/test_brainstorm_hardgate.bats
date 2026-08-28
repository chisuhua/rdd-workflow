#!/usr/bin/env bats
# tests/integration/test_brainstorm_hardgate.bats
# Integration tests for the brainstorm HARD-GATE pre-create check
# (skills/rdd-workflow-brainstorm/scripts/pre_create_brainstorm_check.sh).

setup() {
    load ../test_helper
    # Isolated project root with a roadmap theme so the **主题**: match can be
    # exercised (fragment frontmatter "主题: ..." line).
    TEST_PROJECT_ROOT="$(mktemp -d)"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/roadmap/phases"
    printf '%s\n' "---" "id: phase-1" "kind: phase" "status: active" "主题: 定时循环与事件触发" "---" > "$TEST_PROJECT_ROOT/.rddf/roadmap/phases/phase-1.md"
    CHECK="$REPO_ROOT/skills/rdd-workflow-brainstorm/scripts/pre_create_brainstorm_check.sh"
    PROPOSAL="$TEST_PROJECT_ROOT/.rddf/improvements/test-prop.md"
    mkdir -p "$TEST_PROJECT_ROOT/.rddf/improvements"
}

teardown() {
    rm -rf "$TEST_PROJECT_ROOT"
}

# write_complete <dest>: writes a fully brainstorm-complete proposal.
write_complete() {
    local dest="$1"
    cat > "$dest" <<'EOF'
# test-prop

**优先级**: P1 | **来源**: test
**阶段**: phase-1 | **分类**: arch-design
**类型**: improvement
**主题**: 定时循环与事件触发

## 架构依据

正文。

## 范围

正文。

## Capabilities

正文。

## Impact

正文。

## 验收标准

正文。

## Why

正文。

## What Changes

正文。

## Acceptance

- [ ] one
- [ ] two
- [ ] three
EOF
}

@test "brainstorm-hardgate: complete proposal passes (exit 0)" {
    write_complete "$PROPOSAL"
    run bash "$CHECK" "$PROPOSAL" --project-root "$TEST_PROJECT_ROOT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"HARD-GATE satisfied"* ]]
}

@test "brainstorm-hardgate: missing ## Why section fails (exit 1)" {
    write_complete "$PROPOSAL"
    sed -i '/^## Why$/,/^## What Changes$/ { /^## Why$/d; }' "$PROPOSAL"
    run bash "$CHECK" "$PROPOSAL" --project-root "$TEST_PROJECT_ROOT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"missing section: ## Why"* ]]
}

@test "brainstorm-hardgate: missing ## Acceptance checkboxes fails (exit 1)" {
    write_complete "$PROPOSAL"
    # Keep only a single checkbox -> below the >= 3 threshold.
    awk '/^## Acceptance$/{n=1} n==1 && /^\- \[ \]/{c++; if(c>1) next} {print}' "$PROPOSAL" > "$PROPOSAL.tmp" && mv "$PROPOSAL.tmp" "$PROPOSAL"
    run bash "$CHECK" "$PROPOSAL" --project-root "$TEST_PROJECT_ROOT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"at least 3 checkbox items"* ]]
}

@test "brainstorm-hardgate: missing **主题**: field fails (exit 1)" {
    write_complete "$PROPOSAL"
    sed -i '/^\*\*主题\*\*:/d' "$PROPOSAL"
    run bash "$CHECK" "$PROPOSAL" --project-root "$TEST_PROJECT_ROOT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"missing field: **主题**:"* ]]
}

@test "brainstorm-hardgate: **主题**: not matching roadmap fails (exit 1)" {
    write_complete "$PROPOSAL"
    sed -i 's/^\*\*主题\*\*:.*/**主题**: 完全无关的主题/' "$PROPOSAL"
    run bash "$CHECK" "$PROPOSAL" --project-root "$TEST_PROJECT_ROOT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"does not match any roadmap theme"* ]]
}
