#!/usr/bin/env bats
# Integration tests for `rddf planner` CLI.

load test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/improvements"
    mkdir -p "$TEST_TMP/.rddf/state"
    cd "$TEST_TMP"
    git init -q .
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "planner: status prints sprint id" {
    run python3 -m _lib.cli planner status --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "sprint-" ]]
}

@test "planner: sync dry-run does not write state" {
    cat > .rddf/improvements/foo.md <<'EOF'
---
name: foo
priority: P2
roadmap_ref:
  project_id: foo-impl
  phase: phase-2
  theme: foo theme
---
# foo
EOF

    run python3 -m _lib.cli planner sync --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "DRY-RUN" ]]
    [ ! -f .rddf/state/.planner-state.json ]
}

@test "planner: sync --apply writes state and roadmap" {
    cat > .rddf/improvements/foo.md <<'EOF'
---
name: foo
priority: P2
roadmap_ref:
  project_id: foo-impl
  phase: phase-2
  theme: foo theme
---
# foo
EOF
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap

## Phase Skeleton
| Phase | Theme |
|-------|-------|
| phase-1 | t |

<!-- AUTO-INDEX -->
EOF

    run python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [ -f .rddf/state/.planner-state.json ]
    grep -q "AUTO-SPRINT-START" .rddf/roadmap.md
    grep -q "AUTO-SPRINT-END" .rddf/roadmap.md
    grep -q "Phase Skeleton" .rddf/roadmap.md
}

@test "planner: sync preserves Phase Skeleton table" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap

## Phase Skeleton
| Phase | Theme |
|-------|-------|
| phase-1 | manual theme |

<!-- AUTO-INDEX -->
EOF

    python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP"

    grep -q "manual theme" .rddf/roadmap.md
}

@test "planner: status reads stored state" {
    mkdir -p .rddf/state
    cat > .rddf/state/.planner-state.json <<'EOF'
{
  "version": 1,
  "current_sprint": "sprint-2026-09",
  "last_sync_at": "2026-09-03T10:30:00+08:00",
  "active_projects": [],
  "unmapped_proposals": [],
  "synced_proposals": []
}
EOF

    run python3 -m _lib.cli planner status --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "stored" ]]
    [[ "$output" =~ "sprint-2026-09" ]]
}