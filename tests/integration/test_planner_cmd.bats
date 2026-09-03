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

@test "planner: attach succeeds when project_id and phase are valid" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-2 | foo bar | active | | |
EOF
    cat > .rddf/improvements/imp1.md <<'EOF'
---
name: imp1
priority: P2
---
# imp1
EOF

    run python3 -m _lib.cli planner attach imp1 --project-id "foo bar" --phase phase-2 --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "Attached: imp1" ]]
    grep -q "project_id: foo bar" .rddf/improvements/imp1.md
    grep -q "phase: phase-2" .rddf/improvements/imp1.md
}

@test "planner: attach rejects unknown project_id" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-2 | foo bar | active | | |
EOF
    printf -- '---\nname: imp1\n---\n# imp1\n' > .rddf/improvements/imp1.md

    run python3 -m _lib.cli planner attach imp1 --project-id nope --phase phase-2 --project-root "$TEST_TMP"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "project_id not in roadmap" ]]
    ! grep -q "project_id: nope" .rddf/improvements/imp1.md
}

@test "planner: attach --overwrite replaces divergent mapping" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-2 | foo bar | active | | |
| phase-3 | bar baz | active | | |
EOF
    mkdir -p .rddf/roadmap/phases
    printf -- '---\nid: phase-3\nkind: phase\n---\n' > .rddf/roadmap/phases/phase-3.md
    printf -- '---\nname: imp1\npriority: P2\nroadmap_ref:\n  project_id: foo bar\n  phase: phase-2\n---\n# imp1\n' > .rddf/improvements/imp1.md

    run python3 -m _lib.cli planner attach imp1 --project-id "bar baz" --phase phase-3 --overwrite --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    grep -q "project_id: bar baz" .rddf/improvements/imp1.md
    grep -q "phase: phase-3" .rddf/improvements/imp1.md
    ! grep -q "project_id: foo bar" .rddf/improvements/imp1.md
}

@test "planner: attach without --overwrite rejects divergent mapping" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-2 | foo bar | active | | |
| phase-3 | bar baz | active | | |
EOF
    mkdir -p .rddf/roadmap/phases
    printf -- '---\nid: phase-3\nkind: phase\n---\n' > .rddf/roadmap/phases/phase-3.md
    printf -- '---\nname: imp1\npriority: P2\nroadmap_ref:\n  project_id: foo bar\n  phase: phase-2\n---\n# imp1\n' > .rddf/improvements/imp1.md

    run python3 -m _lib.cli planner attach imp1 --project-id "bar baz" --phase phase-3 --project-root "$TEST_TMP"

    [ "$status" -eq 1 ]
    grep -q "project_id: foo bar" .rddf/improvements/imp1.md
}

@test "planner: diff with no baseline exits 0 with notice" {
    run python3 -m _lib.cli planner diff --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "No baseline" ]]
}

@test "planner: diff exits 0 when stored matches computed" {
    mkdir -p .rddf/improvements
    printf -- '---\nname: foo\npriority: P2\nroadmap_ref:\n  project_id: p1\n  phase: phase-1\n---\n# foo\n' > .rddf/improvements/foo.md
    python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP"
    run python3 -m _lib.cli planner diff --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Stored and computed state agree" ]]
}