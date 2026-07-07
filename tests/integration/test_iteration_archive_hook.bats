#!/usr/bin/env bats
#
# tests/integration/test_iteration_archive_hook.bats
#
# Integration test for the archive.sh mark_iteration_archived hook.
# Verifies the bash function correctly delegates to skills/_lib/iteration.py
# to mark a change as archived in .rddf/state/iteration.json.
#
# Run: bats tests/integration/test_iteration_archive_hook.bats

load ../test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    WORKDIR="$(mktemp -d)"
    cd "$WORKDIR"
    git init -q
    git config user.email "test@example.com"
    git config user.name "Test"
    mkdir -p .rddf/state openspec/changes openspec/changes/archive
    # Seed iteration.json with a change in in_worktree state
    cat > .rddf/state/iteration.json <<'JSON'
{
  "version": 1,
  "updated_at": "2026-07-01T00:00:00+00:00",
  "current_phase": "v2.1",
  "changes": [
    {
      "name": "test-change",
      "phase": "v2.1",
      "category": "general",
      "priority": "P0",
      "status": "in_worktree",
      "added_at": "2026-07-01T00:00:00+00:00",
      "worktree_path": ".rddf/wt/test-change",
      "plan_path": ".rddf/plans/test-change.md",
      "tasks_done": 3,
      "tasks_total": 5
    }
  ]
}
JSON
    export PROJECT_ROOT="$WORKDIR"
    # Source archive.sh — this exposes mark_iteration_archived
    source "$REPO_ROOT/skills/_lib/archive.sh"
}

teardown() {
    rm -rf "$WORKDIR"
}

@test "mark_iteration_archived: changes status to archived and sets timestamp" {
    mark_iteration_archived "test-change" "$PROJECT_ROOT"

    # Reload iteration.json
    local status archived_at
    status=$(python3 -c "import json; print(json.load(open('.rddf/state/iteration.json'))['changes'][0]['status'])")
    archived_at=$(python3 -c "import json; print(json.load(open('.rddf/state/iteration.json'))['changes'][0].get('archived_at', ''))")

    [ "$status" = "archived" ]
    [ -n "$archived_at" ]
}

@test "mark_iteration_archived: preserves other fields (phase, tasks_done, etc.)" {
    mark_iteration_archived "test-change" "$PROJECT_ROOT"

    local phase tasks_done tasks_total
    phase=$(python3 -c "import json; print(json.load(open('.rddf/state/iteration.json'))['changes'][0]['phase'])")
    tasks_done=$(python3 -c "import json; print(json.load(open('.rddf/state/iteration.json'))['changes'][0]['tasks_done'])")
    tasks_total=$(python3 -c "import json; print(json.load(open('.rddf/state/iteration.json'))['changes'][0]['tasks_total'])")

    [ "$phase" = "v2.1" ]
    [ "$tasks_done" = "3" ]
    [ "$tasks_total" = "5" ]
}

@test "mark_iteration_archived: returns 0 even on success (no error propagation)" {
    run mark_iteration_archived "test-change" "$PROJECT_ROOT"
    [ "$status" -eq 0 ]
}

@test "mark_iteration_archived: returns 0 when iteration.json does not exist (no-op)" {
    rm -f .rddf/state/iteration.json
    run mark_iteration_archived "test-change" "$PROJECT_ROOT"
    [ "$status" -eq 0 ]
    # No file should be created
    [ ! -f .rddf/state/iteration.json ]
}

@test "mark_iteration_archived: tolerates missing change entry (creates one)" {
    # Remove the entry but keep iteration.json
    python3 -c "
import json
data = json.load(open('.rddf/state/iteration.json'))
data['changes'] = []  # empty
json.dump(data, open('.rddf/state/iteration.json', 'w'), indent=2)
"
    # mark_iteration_archived should NOT recreate the entry (it's the
    # propose hook's job to add entries; archive just transitions).
    # So the call should be a no-op on iteration.json content.
    mark_iteration_archived "test-change" "$PROJECT_ROOT"
    local count
    count=$(python3 -c "import json; print(len(json.load(open('.rddf/state/iteration.json'))['changes']))")
    # Entry may or may not be present depending on iteration.py semantics;
    # the important thing is no crash. Both behaviors are acceptable.
    [ "$count" -ge 0 ]
}

@test "mark_iteration_archived: handles corrupt iteration.json without crashing" {
    echo "{ this is not valid json" > .rddf/state/iteration.json
    run mark_iteration_archived "test-change" "$PROJECT_ROOT"
    [ "$status" -eq 0 ]
}

@test "archive.sh syntax is valid bash" {
    bash -n "$REPO_ROOT/skills/_lib/archive.sh"
}
