#!/usr/bin/env bats
# Integration tests for planner_stage_entry.sh / planner_stage_exit.sh
# Bug X3 fix: stage scripts no longer contain inline Python for objective
# parsing or AGENTS.md sentinel refresh; both delegate to _lib/objective_parser
# and _lib/roadmap_state.update_objectives_sentinel.

load test_helper

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
ENTRY="$REPO_ROOT/skills/rdd-planner/scripts/planner_stage_entry.sh"
EXIT_SCRIPT="$REPO_ROOT/skills/rdd-planner/scripts/planner_stage_exit.sh"

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    git init -q .
    mkdir -p .rddf/state
    mkdir -p .rddf/roadmap
    mkdir -p .rddf/roadmap/objectives
    mkdir -p openspec/changes/test-change
    echo "# AGENTS" > AGENTS.md
    cat > .rddf/state/.planner-state.json <<'EOF'
{
    "current_sprint": "sprint-2026-09",
    "proposals_ready": [],
    "proposals_approved_count": 0,
    "features_active": [],
    "recommended_route": "simple"
}
EOF
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap (stub for planner gate 1)

## Phase Skeleton
| Phase | Theme | Status |
|-------|-------|--------|
| phase-1 | stub | active |

<!-- AUTO-INDEX -->
EOF
    cat > .rddf/roadmap/objectives/objective-x.md <<'EOF'
---
id: objective-x
status: active
created: 2026-09-28
last_revised: 2026-09-28
review_by: 2026-12-27
owner: rdd-planner
priority: P1
manual_deps: []
theme: test theme
---
# Objective body
## 10. next_sprint_candidates
- [ ] c1
- [ ] c2
EOF
}

teardown() {
    rm -rf "$TEST_TMP"
}


@test "planner_stage_entry.sh no inline parse_objective import" {
    ! grep -q "from _lib.objective import parse_objective" "$ENTRY"
}

@test "planner_stage_exit.sh no inline parse_objective import" {
    ! grep -q "from _lib.objective import parse_objective" "$EXIT_SCRIPT"
}

@test "planner_stage_entry.sh delegates to _lib.objective_parser" {
    grep -q "objective_parser" "$ENTRY"
}

@test "planner_stage_exit.sh no inline AGENTS objectives sentinel" {
    ! grep -q "AGENTS_OBJECTIVES_SENTINEL_START\|AUTO: objectives start" "$EXIT_SCRIPT"
}

@test "planner_stage_exit.sh delegates to update_objectives_sentinel" {
    grep -q "update_objectives_sentinel" "$EXIT_SCRIPT"
}


@test "planner_stage_entry.sh ACTIVE_OBJECTIVES_JSON contains objective id" {
    cd "$TEST_TMP"
    local output
    output=$(env HOME="$HOME" PATH="$PATH" PYTHONPATH="$REPO_ROOT" PROJECT_ROOT="$TEST_TMP" bash -c "
        set +e
        source '$ENTRY' test-change 2>/dev/null
        echo \"\${ACTIVE_OBJECTIVES_JSON:-EMPTY}\"
    " 2>/dev/null)
    [ "$output" != "EMPTY" ]
    echo "$output" | grep -q "objective-x"
}


@test "planner_stage_exit.sh updates AGENTS.md AUTO: objectives sentinel" {
    cd "$TEST_TMP"
    cat > AGENTS.md <<'EOF'
# AGENTS

<!-- AUTO: objectives start -->
OLD STALE
<!-- AUTO: objectives end -->

<!-- footer -->
EOF

    env HOME="$HOME" PATH="$PATH" PYTHONPATH="$REPO_ROOT" PROJECT_ROOT="$TEST_TMP" bash -c "
        set +e
        source '$EXIT_SCRIPT' test-change 2>/dev/null
    " >/dev/null 2>&1 || true

    local content
    content=$(cat AGENTS.md)
    echo "$content" | grep -q "objective-x"
    ! echo "$content" | grep -q "OLD STALE"
    [ "$(echo "$content" | grep -c '<!-- AUTO: objectives start -->')" -eq 1 ]
    [ "$(echo "$content" | grep -c '<!-- AUTO: objectives end -->')" -eq 1 ]
}
