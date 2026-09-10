#!/usr/bin/env bats
# tests/integration/test_rdd_planner_recommended_route.bats
# Integration tests for rdd-planner advisory signal (per ADR-0048 §Decision 2).
#
# Verifies end-to-end:
#  - rddf planner status shows "Recommended route: ..." line (per ADR-0048)
#  - rddf planner sync --apply writes recommended_route to .planner-state.json
#  - heuristic returns simple/complex/unknown based on active_projects
#  - planner-handoff.json v1.1 includes recommended_route (REQUIRED per ADR-0048)

load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    PLANNER_CMD="python3 -m _lib.cli planner"
    WORK_TMP="$(mktemp -d)"
    cd "$WORK_TMP"
    git init -q .
    mkdir -p .rddf/improvements .rddf/state .rddf/roadmap
}

teardown() {
    rm -rf "$WORK_TMP"
}

# Helper: create an improvement with given priority + theme.
write_improvement() {
    local name="$1" priority="$2" theme="$3" project_id="$4"
    cat > ".rddf/improvements/${name}.md" <<EOF
---
name: ${name}
priority: ${priority}
roadmap_ref:
  project_id: ${project_id}
  phase: phase-1
  theme: "${theme}"
---
# ${name}

## Why
test

## Acceptance
- [ ] AC-1

## Capabilities
- (none)
EOF
}

# ---------------------------------------------------------------------------
# rddf planner status output includes recommended_route (per ADR-0048)
# ---------------------------------------------------------------------------

@test "planner status: shows 'Recommended route:' line" {
    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD status --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Recommended route:" ]]
}

@test "planner status: shows unknown hint when no sync ran" {
    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD status --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Recommended route: unknown" ]]
    # When unknown, hint should suggest running sync
    [[ "$output" =~ "sync --apply" ]]
}

@test "planner status: shows simple hint when active_projects all P3" {
    write_improvement "simple-1" "P3" "doc typo" "docs"
    write_improvement "simple-2" "P3" "comment fix" "docs"

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD sync --apply --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD status --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Recommended route: simple" ]]
    # Simple hint should mention option 5 / dispatch-quick
    [[ "$output" =~ "option 5" ]] || [[ "$output" =~ "dispatch-quick" ]]
}

@test "planner status: shows complex hint when any active_project has P0/P1" {
    write_improvement "urgent-1" "P0" "security fix" "auth"
    write_improvement "minor-1" "P3" "doc typo" "docs"

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD sync --apply --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD status --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Recommended route: complex" ]]
}

@test "planner status: shows complex hint when theme has 'public interface' keyword" {
    write_improvement "api-change" "P3" "public interface redesign" "api"

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD sync --apply --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD status --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Recommended route: complex" ]]
}

@test "planner status: shows complex hint when proposal name has 'breaking-change'" {
    write_improvement "breaking-change-to-config" "P3" "some theme" "config"

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD sync --apply --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD status --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Recommended route: complex" ]]
}

@test "planner status: shows complex hint when theme references _lib/core/" {
    write_improvement "core-refactor" "P3" "refactor _lib/core/atomic_write.py" "core"

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD sync --apply --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && $PLANNER_CMD status --project-root '$WORK_TMP'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Recommended route: complex" ]]
}

# ---------------------------------------------------------------------------
# planner-handoff.json v1.1 contains recommended_route (per ADR-0048)
# ---------------------------------------------------------------------------

@test "planner-handoff schema: required includes recommended_route" {
    run python3 -c "
import json
s = json.load(open('$REPO_ROOT/_lib/schemas/planner_handoff_schema.json'))
assert 'recommended_route' in s.get('required', []), s
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "planner-state schema: required includes recommended_route" {
    run python3 -c "
import json
s = json.load(open('$REPO_ROOT/_lib/schemas/planner_state_schema.json'))
assert 'recommended_route' in s.get('required', []), s
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "planner-handoff schema: recommended_route enum is simple|complex|unknown" {
    run python3 -c "
import json
s = json.load(open('$REPO_ROOT/_lib/schemas/planner_handoff_schema.json'))
rec = s['properties']['recommended_route']
assert rec['enum'] == ['simple', 'complex', 'unknown'], rec
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

# ---------------------------------------------------------------------------
# planner_stage_exit.sh double-gate (per ADR-0048 §Decision 2)
# ---------------------------------------------------------------------------

@test "planner_stage_exit.sh: refuses when roadmap.md missing" {
    # Setup: openspec/changes/<change> exists but no roadmap.md
    mkdir -p openspec/changes/test-change
    echo "# proposal" > openspec/changes/test-change/proposal.md

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && bash '$REPO_ROOT/skills/rdd-planner/scripts/planner_stage_exit.sh' test-change"
    [ "$status" -eq 2 ]
    [[ "$output" =~ "双门控失败" ]]
}

@test "planner_stage_exit.sh: refuses when recommended_route=unknown (no sync)" {
    # Setup: roadmap.md exists + openspec/changes/test-change + no planner-state.json
    echo "# Roadmap" > roadmap.md
    mkdir -p openspec/changes/test-change
    echo "# proposal" > openspec/changes/test-change/proposal.md

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && bash '$REPO_ROOT/skills/rdd-planner/scripts/planner_stage_exit.sh' test-change"
    [ "$status" -eq 2 ]
    [[ "$output" =~ "recommended_route" ]] || [[ "$output" =~ "unknown" ]]
}

@test "planner_stage_exit.sh: passes when roadmap.md exists AND recommended_route=simple" {
    # Setup roadmap + openspec/changes + planner-state with recommended_route=simple
    echo "# Roadmap" > roadmap.md
    mkdir -p openspec/changes/test-change
    echo "# proposal" > openspec/changes/test-change/proposal.md
    mkdir -p .rddf/state
    cat > .rddf/state/.planner-state.json <<'EOF'
{
  "version": 1,
  "current_sprint": "sprint-2026-09",
  "last_sync_at": "2026-09-09T10:00:00Z",
  "last_sync_status": "ok",
  "recommended_route": "simple",
  "active_projects": [],
  "unmapped_proposals": [],
  "synced_proposals": []
}
EOF

    run env -u PROJECT_ROOT bash -c "cd '$WORK_TMP' && bash '$REPO_ROOT/skills/rdd-planner/scripts/planner_stage_exit.sh' test-change"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "planner stage exit complete" ]]
    [[ "$output" =~ "recommended_route=simple" ]]
    [ -f .rddf/state/.planner-handoff.json ]

    # Verify handoff contains recommended_route
    run python3 -c "
import json
h = json.load(open('.rddf/state/.planner-handoff.json'))
assert h['recommended_route'] == 'simple', h
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}
