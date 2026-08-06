#!/usr/bin/env bats
# Tests for guide-plan.md queue management features (v2.0.1)
# - 队列概览 (queue overview) at Phase 2 menu top
# - Deps §5e 重组建议回显 before Phase 4 gates
# - Gate 0 改用 iteration.list_ready_for_ship

@test "queue overview: 包含 5 个队列计数" {
    grep -q "候选" "$BATS_TEST_DIRNAME/../../skills/guide-plan/SKILL.md" || return 1
    grep -q "骨架" "$BATS_TEST_DIRNAME/../../skills/guide-plan/SKILL.md" && return 0 || return 1
    # 阻塞/可 ship/deps 过期 在 Python 字符串中，通过匹配上下文验证
    grep -q "阻塞" "$BATS_TEST_DIRNAME/../../skills/guide-plan/SKILL.md" || return 1
    grep -q "可 ship" "$BATS_TEST_DIRNAME/../../skills/guide-plan/SKILL.md" || return 1
    grep -q "deps 过期" "$BATS_TEST_DIRNAME/../../skills/guide-plan/SKILL.md" || return 1
}

@test "queue overview: 调用 iteration.list_planned/list_blocked/list_ready_for_ship" {
    # v2.0.8: queue overview logic extracted to scripts/plan_queue_overview.sh
    local script="$BATS_TEST_DIRNAME/../../skills/guide-plan/scripts/plan_queue_overview.sh"
    [ -f "$script" ]
    grep -q "it.list_planned" "$script"
    grep -q "it.list_blocked" "$script"
    grep -q "it.list_ready_for_ship" "$script"
}

@test "queue overview: 候选计数读 proposal-suggestions.md 的待创建 status" {
    # v2.0.8: candidate count delegates to _lib/state.sh::count_pending_suggestions
    # which reads proposal-suggestions.md JSON and filters status == "待创建"
    local script="$BATS_TEST_DIRNAME/../../skills/guide-plan/scripts/plan_queue_overview.sh"
    local state_sh="$BATS_TEST_DIRNAME/../../_lib/state.sh"
    [ -f "$script" ]
    [ -f "$state_sh" ]
    # plan_queue_overview.sh sources state.sh and calls count_pending_suggestions
    grep -q "count_pending_suggestions" "$script"
    grep -q "proposal-suggestions.md" "$state_sh"
    grep -q "待创建" "$state_sh"
}

@test "deps §5e 回显: 提取 split/merge/reorder 建议" {
    run grep -A 25 "Deps §5e" "$BATS_TEST_DIRNAME/../../skills/guide-plan/scripts/plan_done_gate.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"split|merge|reorder"* ]]
    [[ "$output" == *"FALLBACK_MARKER"* ]]
    [[ "$output" == *"AI 语义分析未启用"* ]]
}

@test "deps §5e 回显: 默认忽略（不阻断）" {
    run grep -B 1 -A 5 "GUIDE_PLAN_DEPS_CHOICE" "$BATS_TEST_DIRNAME/../../skills/guide-plan/scripts/plan_done_gate.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"-2"* ]]
    [[ "$output" == *"SKIP_GATE_0"* ]]
}

@test "deps §5e 回显: 接受建议时设置 SKIP_GATE_0=true" {
    run grep -A 1 '1)' "$BATS_TEST_DIRNAME/../../skills/guide-plan/scripts/plan_done_gate.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP_GATE_0=true"* ]]
}

@test "gate 0: 改用 iteration.list_ready_for_ship" {
    # v2.0.8: plan_done_gate.sh moved from _lib/ to guide-plan/scripts/
    # 必须通过 PY_PROJECT_ROOT 环境变量传递 PROJECT_ROOT (v2.0.2 安全模式)
    run grep -B 2 -A 8 "from skills._lib import iteration" "$BATS_TEST_DIRNAME/../../skills/guide-plan/scripts/plan_done_gate.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"PY_PROJECT_ROOT"* ]]
    [[ "$output" == *"list_ready_for_ship"* ]]
}

@test "gate 0: 旧的内联 sum() 必须被移除" {
    # 旧实现: sum(1 for c in d.get('changes', []) if c.get('status') == 'proposed')
    run grep "sum(1 for c in d.get" "$BATS_TEST_DIRNAME/../../skills/guide-plan/scripts/plan_done_gate.sh"
    [ "$status" -ne 0 ]
}

@test "gate 0: SKIP_GATE_0 短路时直接 return 0" {
    # v2.0.8: the short-circuit block uses 'return 0' (not exit 0) so it
    # exits the function without blocking the caller. The if-condition
    # matching '"${SKIP_GATE_0:-false}" = "true"' is the short-circuit guard.
    run grep -A 5 'SKIP_GATE_0:-false.*=.*"true"' "$BATS_TEST_DIRNAME/../../skills/guide-plan/scripts/plan_done_gate.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"return 0"* ]]
}

@test "frontmatter: guide-plan.md 仍合法" {
    run python3 -c "
import yaml
with open('skills/guide-plan/SKILL.md') as f:
    content = f.read()
assert content.startswith('---')
meta = yaml.safe_load(content.split('---', 2)[1])
assert meta['name'] == 'guide-plan'
assert meta['metadata']['user-invocable'] is True
print('OK')
"
    [ "$status" -eq 0 ]
}
