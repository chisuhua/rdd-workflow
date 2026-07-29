# tests/integration/test_execution_mode_decision.bats
# 全链路集成测试：deps 分析 → plan-handoff → ship 读取

setup() {
    load "$BATS_TEST_DIRNAME/../test_helper"
    # Ensure we're in the project root
    cd "$BATS_TEST_DIRNAME/../.."
}

@test "deps: analyze_execution_mode returns correct mode for small change" {
    PROJECT_ROOT=$(mktemp -d)
    mkdir -p "$PROJECT_ROOT/openspec/changes/test-small"
    echo "- Modify: src/main.py" > "$PROJECT_ROOT/openspec/changes/test-small/design.md"
    echo "- [ ] task 1" > "$PROJECT_ROOT/openspec/changes/test-small/tasks.md"
    echo "simple fix" > "$PROJECT_ROOT/openspec/changes/test-small/proposal.md"

    result=$(cd "$PROJECT_ROOT" && python3 -c "
from skills.deps.scripts.deps_output import analyze_execution_mode
r = analyze_execution_mode('test-small', '$PROJECT_ROOT')
print(r['mode'])
")
    [ "$result" = "lightweight" ]
}

@test "deps: build_analysis includes execution_mode_recommendations" {
    PROJECT_ROOT=$(mktemp -d)
    mkdir -p "$PROJECT_ROOT/openspec/changes/c1"
    echo "- Modify: src/main.py" > "$PROJECT_ROOT/openspec/changes/c1/design.md"
    echo "- [ ] task 1" > "$PROJECT_ROOT/openspec/changes/c1/tasks.md"
    echo "fix" > "$PROJECT_ROOT/openspec/changes/c1/proposal.md"

    result=$(cd "$PROJECT_ROOT" && python3 -c "
from skills.deps.scripts.deps_output import build_analysis
import json
r = build_analysis([{'name': 'c1'}], project_root='$PROJECT_ROOT')
print(json.dumps(r.get('execution_mode_recommendations', {})))
" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('c1',{}).get('mode',''))")
    [ "$result" = "lightweight" ]
}

@test "plan: write_plan_handoff includes execution_mode_decisions" {
    PROJECT_ROOT=$(mktemp -d)
    mkdir -p "$PROJECT_ROOT/.rddf/state"
    mkdir -p "$PROJECT_ROOT/openspec/changes/c1"
    echo "- Modify: src/main.py" > "$PROJECT_ROOT/openspec/changes/c1/design.md"
    echo "- [ ] task 1" > "$PROJECT_ROOT/openspec/changes/c1/tasks.md"
    echo "fix" > "$PROJECT_ROOT/openspec/changes/c1/proposal.md"

    # Write deps-analysis.json first
    python3 -c "
from skills.deps.scripts.deps_output import build_analysis, write_analysis
r = build_analysis([{'name': 'c1'}], project_root='$PROJECT_ROOT')
write_analysis('$PROJECT_ROOT', r)
"

    # Write handoff
    python3 -c "
from skills.guide_plan.scripts.plan_done_gate import write_plan_handoff
result = write_plan_handoff(project_root='$PROJECT_ROOT', change_count=1, current_change='c1')
decisions = result.get('execution_mode_decisions', {})
assert 'c1' in decisions, f'c1 not in decisions: {decisions}'
assert decisions['c1']['mode'] == 'lightweight', f'expected lightweight, got {decisions[\"c1\"][\"mode\"]}'
print('OK')
"
}

@test "ship: detect_execution_mode reads handoff decision" {
    PROJECT_ROOT=$(mktemp -d)
    mkdir -p "$PROJECT_ROOT/.rddf/state"

    cat > "$PROJECT_ROOT/.rddf/state/.plan-handoff.json" << 'JSON'
{
    "version": 2,
    "active_changes": ["test-123"],
    "execution_mode_decisions": {
        "test-123": {"mode": "lightweight", "reason": "small change, no conflicts", "confidence": "high"}
    }
}
JSON

    result=$(cd "$PROJECT_ROOT" && bash -c '
source skills/guide-ship/scripts/ship_plan.sh 2>/dev/null
detect_execution_mode "'$PROJECT_ROOT'" "test-123" 2>/dev/null
')
    [ "$result" = "lightweight" ]
}