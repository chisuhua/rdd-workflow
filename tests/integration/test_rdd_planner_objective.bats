#!/usr/bin/env bats
# tests/integration/test_rdd_planner_objective.bats
#
# rdd-planner objective integration (per add-objective-tracking change):
#   - planner_stage_exit.sh refreshes AGENTS.md <!-- AUTO: objectives --> sentinel
#   - list-objectives shows PoC files after planner run
#   - revise-objective appends §11 ledger row + bumps last_revised
#
# Run: bats tests/integration/test_rdd_planner_objective.bats

load ../test_helper

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    export PROJECT_ROOT
    STAGE_EXIT_SH="$PROJECT_ROOT/skills/rdd-planner/scripts/planner_stage_exit.sh"
    REVISE_SH="$PROJECT_ROOT/skills/roadmap/scripts/objective_revise.sh"
    AGENTS_MD="$PROJECT_ROOT/AGENTS.md"
}

@test "planner-objective: AGENTS.md contains AUTO: objectives sentinel" {
    [ -f "$AGENTS_MD" ]
    grep -q "<!-- AUTO: objectives start -->" "$AGENTS_MD"
    grep -q "<!-- AUTO: objectives end -->" "$AGENTS_MD"
}

@test "planner-objective: sentinel lists both PoC objectives" {
    grep -q "objective-bypass-audit-hub-governance" "$AGENTS_MD"
    grep -q "objective-onboard-new-skill" "$AGENTS_MD"
}

@test "planner-objective: revise-objective appends ledger row + bumps last_revised" {
    local TMP_DIR; TMP_DIR="$(mktemp -d)"
    mkdir -p "$TMP_DIR/.rddf/roadmap/objectives"
    cp "$PROJECT_ROOT/.rddf/roadmap/objectives/objective-onboard-new-skill.md" "$TMP_DIR/.rddf/roadmap/objectives/objective-revise-test.md"
    # Normalize id inside file to match filename (revise reads frontmatter id)
    sed -i 's/^id: objective-onboard-new-skill$/id: objective-revise-test/' "$TMP_DIR/.rddf/roadmap/objectives/objective-revise-test.md"

    run bash -c "PROJECT_ROOT='$TMP_DIR' bash '$REVISE_SH' objective-revise-test --kind sprint-review --content 'sprint 复盘验证' --decision 'continue' --reason 'bats test'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"appended ledger row"* ]]

    # Ledger row present
    grep -q "sprint 复盘验证" "$TMP_DIR/.rddf/roadmap/objectives/objective-revise-test.md"
    # last_revised bumped to today
    TODAY="$(date +%Y-%m-%d)"
    grep -q "last_revised: $TODAY" "$TMP_DIR/.rddf/roadmap/objectives/objective-revise-test.md"
    rm -rf "$TMP_DIR"
}

@test "planner-objective: list-objectives CLI integrates with PoC files" {
    run rddf roadmap list-objectives --format json
    [ "$status" -eq 0 ]
    [[ "$output" == *"objective-bypass-audit-hub-governance"* ]]
}

# v1.2 (per add-objective-aware-planner): planner stage entry/exit scripts
# write active_objectives array into .planner-handoff.json for LLM consumption.
# Tests use isolated $TMP_DIR fixture to avoid clobbering repo's planner-handoff.

@test "planner-objective: stage_entry writes active_objectives to handoff" {
    local TMP_DIR; TMP_DIR="$(mktemp -d)"
    mkdir -p "$TMP_DIR/openspec/changes/test-active" "$TMP_DIR/.rddf/state" "$TMP_DIR/.rddf/roadmap/objectives"
    # Copy PoC objective files into fixture
    cp "$PROJECT_ROOT/.rddf/roadmap/objectives/objective-onboard-new-skill.md" "$TMP_DIR/.rddf/roadmap/objectives/"
    cp "$PROJECT_ROOT/.rddf/roadmap/objectives/objective-bypass-audit-hub-governance.md" "$TMP_DIR/.rddf/roadmap/objectives/"
    # Provide a fake planner-state.json so planner-handoff.py can find state
    printf '{"recommended_route":"unknown","active_projects":[]}\n' > "$TMP_DIR/.rddf/state/.planner-state.json"

    run bash -c "cd '$TMP_DIR' && PROJECT_ROOT='$TMP_DIR' bash '$PROJECT_ROOT/skills/rdd-planner/scripts/planner_stage_entry.sh' test-active"
    [ "$status" -eq 0 ] || { echo "stderr: $output"; rm -rf "$TMP_DIR"; return 1; }
    [ -f "$TMP_DIR/.rddf/state/.planner-handoff.json" ]
    # active_objectives field present and non-empty
    grep -q '"active_objectives"' "$TMP_DIR/.rddf/state/.planner-handoff.json"
    # Contains both PoC objective ids
    grep -q 'objective-onboard-new-skill' "$TMP_DIR/.rddf/state/.planner-handoff.json"
    grep -q 'objective-bypass-audit-hub-governance' "$TMP_DIR/.rddf/state/.planner-handoff.json"
    rm -rf "$TMP_DIR"
}

@test "planner-objective: active_objectives contains next_sprint_candidates from §10" {
    local TMP_DIR; TMP_DIR="$(mktemp -d)"
    mkdir -p "$TMP_DIR/openspec/changes/test-active" "$TMP_DIR/.rddf/state" "$TMP_DIR/.rddf/roadmap/objectives"
    cp "$PROJECT_ROOT/.rddf/roadmap/objectives/objective-onboard-new-skill.md" "$TMP_DIR/.rddf/roadmap/objectives/"
    printf '{"recommended_route":"complex","active_projects":[]}\n' > "$TMP_DIR/.rddf/state/.planner-state.json"

    run bash -c "cd '$TMP_DIR' && PROJECT_ROOT='$TMP_DIR' bash '$PROJECT_ROOT/skills/rdd-planner/scripts/planner_stage_entry.sh' test-active"
    [ "$status" -eq 0 ]
    # Use Python to parse JSON because ensure_ascii=True escapes CJK as \uXXXX
    # (grep on raw bytes would miss them). Candidates should contain 3 §10 items.
    python3 -c "
import json
d = json.load(open('$TMP_DIR/.rddf/state/.planner-handoff.json'))
onboard = [o for o in d['active_objectives'] if o['id'] == 'objective-onboard-new-skill']
assert len(onboard) == 1, f'expected 1 onboard, got {len(onboard)}'
cands = onboard[0]['next_sprint_candidates']
assert len(cands) == 3, f'expected 3 candidates, got {len(cands)}: {cands}'
# Check semantic content via substring (not CJK grep)
assert any('add-skill-onboarding' in c for c in cands), f'no add-skill-onboarding in: {cands}'
assert any('pre_create_brainstorm_check' in c for c in cands), f'no HARD-GATE in: {cands}'
assert any('rdd-env-bootstrap' in c for c in cands), f'no rdd-env-bootstrap in: {cands}'
print('OK')
"
    rm -rf "$TMP_DIR"
}

@test "planner-objective: deferred objectives with N/A → empty next_sprint_candidates" {
    local TMP_DIR; TMP_DIR="$(mktemp -d)"
    mkdir -p "$TMP_DIR/openspec/changes/test-active" "$TMP_DIR/.rddf/state" "$TMP_DIR/.rddf/roadmap/objectives"
    cp "$PROJECT_ROOT/.rddf/roadmap/objectives/objective-bypass-audit-hub-governance.md" "$TMP_DIR/.rddf/roadmap/objectives/"
    printf '{"recommended_route":"complex","active_projects":[]}\n' > "$TMP_DIR/.rddf/state/.planner-state.json"

    run bash -c "cd '$TMP_DIR' && PROJECT_ROOT='$TMP_DIR' bash '$PROJECT_ROOT/skills/rdd-planner/scripts/planner_stage_entry.sh' test-active"
    [ "$status" -eq 0 ]
    # §10 is "N/A — 维持 v3.2 deferred 决策" — N/A line must be filtered out
    ! grep -q 'N/A — 维持 v3.2 deferred 决策' "$TMP_DIR/.rddf/state/.planner-handoff.json"
    # Verify bypass-audit objective is recorded with empty candidates via python
    python3 -c "
import json
d = json.load(open('$TMP_DIR/.rddf/state/.planner-handoff.json'))
bypass = [o for o in d['active_objectives'] if o['id'] == 'objective-bypass-audit-hub-governance']
assert len(bypass) == 1, f'expected 1, got {len(bypass)}'
assert bypass[0]['next_sprint_candidates'] == [], f'expected empty, got {bypass[0][\"next_sprint_candidates\"]}'
assert bypass[0]['status'] == 'deferred', f'expected deferred, got {bypass[0][\"status\"]}'
print('OK')
"
    rm -rf "$TMP_DIR"
}

@test "planner-objective: empty objectives dir → empty active_objectives array" {
    local TMP_DIR; TMP_DIR="$(mktemp -d)"
    mkdir -p "$TMP_DIR/openspec/changes/test-active" "$TMP_DIR/.rddf/state"
    # No .rddf/roadmap/objectives/ directory at all
    printf '{"recommended_route":"unknown","active_projects":[]}\n' > "$TMP_DIR/.rddf/state/.planner-state.json"

    run bash -c "cd '$TMP_DIR' && PROJECT_ROOT='$TMP_DIR' bash '$PROJECT_ROOT/skills/rdd-planner/scripts/planner_stage_entry.sh' test-active"
    [ "$status" -eq 0 ]
    python3 -c "
import json
d = json.load(open('$TMP_DIR/.rddf/state/.planner-handoff.json'))
assert d['active_objectives'] == [], f'expected [], got {d[\"active_objectives\"]}'
print('OK')
"
    rm -rf "$TMP_DIR"
}
