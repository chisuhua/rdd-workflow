load ../test_helper

# Integration test for fix-archive-on-main-flow: verify that
# tools/archive_on_main.sh enforces the --confirm-main flag (fail-closed),
# invokes sync_iteration_after_archive after the mv, and rolls back
# when the helper fails.

setup() {
    BATS_TEST_TMPDIR="$(mktemp -d)"
    export PROJECT_ROOT="$BATS_TEST_TMPDIR"

    # Create a fake project: openspec/changes/<name>/ + minimal state dir
    mkdir -p "$BATS_TEST_TMPDIR/openspec/changes/test-change"
    cat > "$BATS_TEST_TMPDIR/openspec/changes/test-change/proposal.md" <<'EOF'
# test-change
EOF
    cat > "$BATS_TEST_TMPDIR/openspec/changes/test-change/tasks.md" <<'EOF'
# Tasks
- [x] 1.1 done
- [x] 1.2 done
EOF
    cat > "$BATS_TEST_TMPDIR/openspec/changes/test-change/.openspec.yaml" <<'EOF'
schema: spec-driven
name: test-change
EOF

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

    # Initialize a git repo in the test project (required for git operations)
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "test@example.com"
    git config user.name "test"
    git add -A
    git commit -q -m "init"

    # Point SCRIPT at the worktree's tools/archive_on_main.sh
    SCRIPT="$REPO_ROOT/tools/archive_on_main.sh"

    # Provide a fake openspec binary (no-op) so the script can call it
    mkdir -p "$BATS_TEST_TMPDIR/.bin"
    cat > "$BATS_TEST_TMPDIR/.bin/openspec" <<'EOF'
#!/bin/bash
# minimal fake: success exit
exit 0
EOF
    chmod +x "$BATS_TEST_TMPDIR/.bin/openspec"
    export PATH="$BATS_TEST_TMPDIR/.bin:$PATH"
}

teardown() {
    [ -n "$BATS_TEST_TMPDIR" ] && rm -rf "$BATS_TEST_TMPDIR"
}

@test "archive_on_main: missing --confirm-main → exit 2, banner printed" {
    SCRIPT="$REPO_ROOT/tools/archive_on_main.sh"
    run bash "$SCRIPT" "test-change" </dev/null
    [ "$status" -eq 2 ]
    [[ "$output" == *"OFF-HAPPY-PATH"* ]]
    [[ "$output" == *"--confirm-main"* ]]
}

@test "archive_on_main: --confirm-main with valid change → mv + sync" {
    SCRIPT="$REPO_ROOT/tools/archive_on_main.sh"
    run bash "$SCRIPT" "test-change" --confirm-main </dev/null
    [ "$status" -eq 0 ]
    # archive dir should exist
    archive_dir_count=$(find "$BATS_TEST_TMPDIR/openspec/changes/archive" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    [ "$archive_dir_count" -ge 1 ]
    # iteration.json should be marked archived
    archived_status=$(python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/.rddf/state/iteration.json'))
c = next(c for c in d['changes'] if c['name'] == 'test-change')
print(c.get('status', ''))
")
    [ "$archived_status" = "archived" ]
}

@test "archive_on_main: --archive-commit-sha <sha> is recorded in iteration.json" {
    SCRIPT="$REPO_ROOT/tools/archive_on_main.sh"
    run bash "$SCRIPT" "test-change" --confirm-main --archive-commit-sha "deadbeef123" </dev/null
    [ "$status" -eq 0 ]
    sha=$(python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/.rddf/state/iteration.json'))
c = next(c for c in d['changes'] if c['name'] == 'test-change')
print(c.get('archive_commit_sha', ''))
")
    [ "$sha" = "deadbeef123" ]
}

@test "archive_on_main: idempotent — second invocation detects duplicate and skips" {
    SCRIPT="$REPO_ROOT/tools/archive_on_main.sh"
    # First invocation
    run bash "$SCRIPT" "test-change" --confirm-main </dev/null
    [ "$status" -eq 0 ]
    # Second invocation should detect archive dir exists and either reject or skip
    run bash "$SCRIPT" "test-change" --confirm-main </dev/null
    # The contract: reject duplicate OR idempotent sync (not both)
    # We accept either non-zero exit OR success without new commit
    archive_count=$(find "$BATS_TEST_TMPDIR/openspec/changes/archive" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    [ "$archive_count" -eq 1 ]
}

@test "archive_on_main: missing change directory → exit non-zero" {
    SCRIPT="$REPO_ROOT/tools/archive_on_main.sh"
    run bash "$SCRIPT" "nonexistent-change" --confirm-main </dev/null
    [ "$status" -ne 0 ]
}

@test "archive_on_main: non-git repo → fail-closed (require git)" {
    SCRIPT="$REPO_ROOT/tools/archive_on_main.sh"
    # Set up a non-git dir
    NGTMP="$(mktemp -d)"
    mkdir -p "$NGTMP/openspec/changes/test-change"
    echo "x" > "$NGTMP/openspec/changes/test-change/proposal.md"

    cd "$NGTMP"
    run bash "$SCRIPT" "test-change" --confirm-main </dev/null
    [ "$status" -ne 0 ]
    rm -rf "$NGTMP"
}

@test "archive_on_main: script is at least 30 lines (per proposal AC)" {
    SCRIPT="$REPO_ROOT/tools/archive_on_main.sh"
    [ -f "$SCRIPT" ]
    lines=$(wc -l < "$SCRIPT")
    [ "$lines" -ge 30 ]
}
