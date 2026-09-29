#!/usr/bin/env bats
# Integration contract test: planner_stage_{entry,exit}.sh must gracefully
# degrade when the `rddf` CLI is not on PATH (e.g. global install partial,
# fresh CI environment, dependency upgrade in flight).
#
# Locking this contract prevents accidental removal of the `2>/dev/null || true`
# guards that make the scripts self-sufficient for objective parsing and
# handoff emission. If rddf is missing:
#   - FEATURES should be empty (rddf roadmap list-features → silent fail)
#   - ACTIVE_OBJECTIVES_JSON should still be populated via _lib.objective_parser
#     (no rddf dependency)
#   - .planner-handoff.json should still be written
#   - scripts should exit 0

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
# Roadmap stub

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
theme: graceful-degradation test
---
EOF
}

teardown() {
    rm -rf "$TEST_TMP"
}

# Build a minimal PATH containing only bash + python3 + coreutils; no rddf.
strip_rddf_path() {
    echo "/usr/bin:/bin"
}

@test "planner_stage_entry.sh: exit 0 when rddf CLI is absent" {
    cd "$TEST_TMP"
    run env HOME="$HOME" PATH="$(strip_rddf_path)" PYTHONPATH="$REPO_ROOT" \
        PROJECT_ROOT="$TEST_TMP" bash "$ENTRY" test-change
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "command not found" ]]
    [[ ! "$output" =~ "No such file" ]]
}

@test "planner_stage_entry.sh: ACTIVE_OBJECTIVES_JSON populated when rddf absent" {
    cd "$TEST_TMP"
    run env HOME="$HOME" PATH="$(strip_rddf_path)" PYTHONPATH="$REPO_ROOT" \
        PROJECT_ROOT="$TEST_TMP" bash -c "
            set +e
            source '$ENTRY' test-change 2>/dev/null
            echo \"\${ACTIVE_OBJECTIVES_JSON:-UNSET}\"
        "
    [ "$status" -eq 0 ]
    [[ "$output" =~ "objective-x" ]]
}

@test "planner_stage_entry.sh: .planner-handoff.json written when rddf absent" {
    cd "$TEST_TMP"
    env HOME="$HOME" PATH="$(strip_rddf_path)" PYTHONPATH="$REPO_ROOT" \
        PROJECT_ROOT="$TEST_TMP" bash "$ENTRY" test-change >/dev/null 2>&1
    [ -f .rddf/state/.planner-handoff.json ]
}

@test "planner_stage_exit.sh: exit 0 when rddf CLI is absent" {
    cd "$TEST_TMP"
    run env HOME="$HOME" PATH="$(strip_rddf_path)" PYTHONPATH="$REPO_ROOT" \
        PROJECT_ROOT="$TEST_TMP" bash "$EXIT_SCRIPT" test-change
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "command not found" ]]
}

@test "planner_stage_exit.sh: AGENTS.md sentinel refreshed when rddf absent" {
    cd "$TEST_TMP"
    cat > AGENTS.md <<'EOF'
# AGENTS
EOF
    env HOME="$HOME" PATH="$(strip_rddf_path)" PYTHONPATH="$REPO_ROOT" \
        PROJECT_ROOT="$TEST_TMP" bash "$EXIT_SCRIPT" test-change >/dev/null 2>&1
    run grep -c "<!-- AUTO: objectives start -->" AGENTS.md
    [ "$output" -eq 1 ]
    run grep "objective-x" AGENTS.md
    [ "$status" -eq 0 ]
}

@test "planner_stage_exit.sh: .planner-handoff.json written when rddf absent" {
    cd "$TEST_TMP"
    env HOME="$HOME" PATH="$(strip_rddf_path)" PYTHONPATH="$REPO_ROOT" \
        PROJECT_ROOT="$TEST_TMP" bash "$EXIT_SCRIPT" test-change >/dev/null 2>&1
    [ -f .rddf/state/.planner-handoff.json ]
}
