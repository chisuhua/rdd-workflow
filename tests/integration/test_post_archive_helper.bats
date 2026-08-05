load ../test_helper

# Integration test for fix-archive-iteration-sync: verify that the bash
# wrapper mark_iteration_archived in skills/_lib/archive.sh correctly
# calls sync_iteration_after_archive (the new Python helper) and writes
# the archive_commit_sha field to iteration.json.

setup() {
    BATS_TEST_TMPDIR="$(mktemp -d)"
    export PROJECT_ROOT="$BATS_TEST_TMPDIR"

    # Create a fake main_root that looks like a project
    mkdir -p "$BATS_TEST_TMPDIR/openspec/changes/archive/2026-08-05-test-change"
    cat > "$BATS_TEST_TMPDIR/openspec/changes/archive/2026-08-05-test-change/tasks.md" <<'EOF'
# Tasks
- [x] 1.1 done
- [x] 1.2 done
- [ ] 1.3 todo
EOF

    # Create state dir with a minimal valid iteration.json (v4)
    mkdir -p "$BATS_TEST_TMPDIR/.rddf/state"
    cat > "$BATS_TEST_TMPDIR/.rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {
      "name": "test-change",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00"
    }
  ]
}
EOF

    # Source the archive.sh helper
    _LIB_DIR="$REPO_ROOT/skills/_lib"
    source "$_LIB_DIR/archive.sh"
}

teardown() {
    [ -n "$BATS_TEST_TMPDIR" ] && rm -rf "$BATS_TEST_TMPDIR"
}

@test "mark_iteration_archived: with archive_commit_sha writes the SHA to iteration.json" {
    mark_iteration_archived "test-change" "$BATS_TEST_TMPDIR" "abc123def"

    # Read the result
    result=$(python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/.rddf/state/iteration.json'))
c = d['changes'][0]
print(c.get('status', ''))
print(c.get('archived_at', 'MISSING'))
print(c.get('archive_commit_sha', 'MISSING'))
print(c.get('tasks_done', 'MISSING'))
print(c.get('plan_path', 'MISSING'))
")
    [ "$(echo "$result" | head -1)" = "archived" ]
    [ "$(echo "$result" | sed -n '2p')" != "MISSING" ]
    [ "$(echo "$result" | sed -n '3p')" = "abc123def" ]
    [ "$(echo "$result" | sed -n '4p')" = "2" ]      # tasks_done: 2 [x] in tasks.md
    [ "$(echo "$result" | sed -n '5p')" = ".rddf/plans/test-change.md" ]
}

@test "mark_iteration_archived: idempotent — second call preserves existing archived_at" {
    # First call sets archived_at
    mark_iteration_archived "test-change" "$BATS_TEST_TMPDIR" "first_sha"

    # Capture the first archived_at value
    first_ts=$(python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/.rddf/state/iteration.json'))
print(d['changes'][0].get('archived_at', ''))
")

    # Wait a tick to ensure timestamp would differ if regenerated
    sleep 0.05

    # Second call with different SHA — should NOT overwrite archived_at
    mark_iteration_archived "test-change" "$BATS_TEST_TMPDIR" "second_sha"

    second_ts=$(python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/.rddf/state/iteration.json'))
print(d['changes'][0].get('archived_at', ''))
print(d['changes'][0].get('archive_commit_sha', ''))
")

    [ "$(echo "$second_ts" | head -1)" = "$first_ts" ]            # archived_at preserved
    [ "$(echo "$second_ts" | sed -n '2p')" = "first_sha" ]          # SHA preserved
}

@test "mark_iteration_archived: missing iteration.json is a no-op (no error)" {
    rm -f "$BATS_TEST_TMPDIR/.rddf/state/iteration.json"

    # Should not error
    run mark_iteration_archived "test-change" "$BATS_TEST_TMPDIR" "abc"
    [ "$status" -eq 0 ]
}

@test "mark_iteration_archived: missing change entry returns warning, no raise" {
    # Change doesn't exist in iteration.json
    cat > "$BATS_TEST_TMPDIR/.rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {
      "name": "other-change",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00"
    }
  ]
}
EOF

    # Should print warning to stderr but exit 0
    run mark_iteration_archived "test-change" "$BATS_TEST_TMPDIR" "abc"
    [ "$status" -eq 0 ]
    [[ "$output" == *"not found"* ]] || [[ "$output" == *"test-change"* ]]
}
