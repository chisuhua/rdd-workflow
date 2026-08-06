load ../test_helper

# Regression test for archive-iteration-sync: lightweight archive path
# must call mark_iteration_archived to sync iteration.json.
# Bug: archive_change_for_mode() lightweight branch was missing the call,
# causing 5/8 changes to lack archived_at timestamp after archive.

@test "archive-iteration-sync: lightweight path source contains mark_iteration_archived call" {
    # The lightweight archive path in ship_archive.sh must call
    # mark_iteration_archived after successful archive, just like
    # the worktree path does via archive_change().
    #
    # This test verifies the call exists in the lightweight branch.
    PROJECT_ROOT="$REPO_ROOT"
    SHIP_ARCHIVE="$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"

    # Extract the lightweight branch (else clause) and check for the call
    # The lightweight branch starts at "else" after the worktree if-block
    run bash -c "
        awk '/^  else/,/^  fi/' '$SHIP_ARCHIVE' | grep -c 'mark_iteration_archived'
    "
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "archive-iteration-sync: worktree path calls mark_iteration_archived via archive_change" {
    # The worktree path calls archive_change which internally calls
    # mark_iteration_archived. Verify this chain exists.
    PROJECT_ROOT="$REPO_ROOT"
    ARCHIVE_SH="$PROJECT_ROOT/_lib/archive.sh"

    run grep -c "mark_iteration_archived" "$ARCHIVE_SH"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "archive-iteration-sync: mark_archived sets archived_at in iteration module" {
    # Verify the Python mark_archived function properly sets archived_at
    PROJECT_ROOT="$REPO_ROOT"
    cd "$PROJECT_ROOT"

    run python3 -c "
import sys, tempfile, os, json
sys.path.insert(0, '$PROJECT_ROOT')
from skills._lib.iteration import create_empty, add_or_update_change, mark_archived

with tempfile.TemporaryDirectory() as tmp:
    d = create_empty('test')
    d = add_or_update_change(d, name='test-change', status='in_worktree')
    d = mark_archived(d, 'test-change')
    c = [x for x in d['changes'] if x['name'] == 'test-change'][0]
    assert c['status'] == 'archived', f'status={c[\"status\"]}'
    assert 'archived_at' in c, 'archived_at missing'
    assert c['archived_at'] is not None, 'archived_at is None'
    print('OK: mark_archived sets archived_at correctly')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK"* ]]
}
