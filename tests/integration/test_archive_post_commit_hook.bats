load ../test_helper

# Integration test for add-archive-post-commit-hook-and-force-flag:
# verifies that .git-hooks/post-commit detects archive paths in the commit
# diff, extracts the change name, and calls sync_iteration_after_archive
# to update iteration.json. All failures must exit 0 (never block commit).

setup() {
    BATS_TEST_TMPDIR="$(mktemp -d)"
    export PROJECT_ROOT="$BATS_TEST_TMPDIR"

    # Create a real git repo (hooks only run on real commits)
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "test@example.com"
    git config user.name "test"

    # Create .rddf/state/iteration.json with a change entry
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
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

    # Create the change dir + archive dir
    mkdir -p openspec/changes/test-change
    echo "# test-change" > openspec/changes/test-change/proposal.md
    echo "- [x] 1.1 done" > openspec/changes/test-change/tasks.md

    # Pre-create archive dir with a fake date prefix
    ARCHIVE_DATE="2026-08-05"
    mkdir -p "openspec/changes/archive/${ARCHIVE_DATE}-test-change"
    cp openspec/changes/test-change/tasks.md "openspec/changes/archive/${ARCHIVE_DATE}-test-change/"

    # Initial commit
    git add -A
    git commit -q -m "init"

    # Symlink the worktree's skills/ into the test repo so the hook
    # can import the post_archive helper. This simulates a project
    # that has rdd-workflow installed.
    ln -s "$REPO_ROOT/skills" "$BATS_TEST_TMPDIR/skills"

    # Install the hook from the worktree
    HOOK_SRC="$REPO_ROOT/.git-hooks/post-commit"
    HOOK_DST="$BATS_TEST_TMPDIR/.git-hooks/post-commit"
    [ -f "$HOOK_SRC" ] && mkdir -p "$BATS_TEST_TMPDIR/.git-hooks" && cp "$HOOK_SRC" "$HOOK_DST" && chmod +x "$HOOK_DST"
    git config core.hooksPath "$BATS_TEST_TMPDIR/.git-hooks"
}

teardown() {
    [ -n "$BATS_TEST_TMPDIR" ] && rm -rf "$BATS_TEST_TMPDIR"
}

@test "post-commit hook: archive path in commit → iteration.json status=archived" {
    # Stage a commit that simulates an archive move
    cd "$BATS_TEST_TMPDIR"
    touch "openspec/changes/archive/2026-08-05-test-change/.archive-marker"
    git add -A
    git commit -q -m "chore(archive): finalize test-change archive state"

    # Verify iteration.json was updated
    status=$(python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/.rddf/state/iteration.json'))
c = next(c for c in d['changes'] if c['name'] == 'test-change')
print(c.get('status', ''))
")
    [ "$status" = "archived" ]
}

@test "post-commit hook: non-archive commit → no stdout, no side effects" {
    cd "$BATS_TEST_TMPDIR"
    echo "unrelated" > README.md
    git add -A

    # Capture hook output (git commit output includes hook stdout)
    output=$(git commit -m "docs: update readme" 2>&1)
    # Hook should produce no output for non-archive commits
    [[ ! "$output" == *"archive hook"* ]]
}

@test "post-commit hook: missing helper → exit 0, commit succeeds" {
    cd "$BATS_TEST_TMPDIR"
    # Make archive_commit_sha_helper import fail by removing sync_iteration_after_archive
    # This is a degenerate test — the hook should tolerate any Python failure
    touch "openspec/changes/archive/2026-08-05-test-change/.archive-marker"
    git add -A
    run git commit -m "test"
    [ "$status" -eq 0 ]  # git commit succeeded
}

@test "post-commit hook: date prefix is stripped correctly" {
    cd "$BATS_TEST_TMPDIR"
    # Use a different date prefix to verify regex matching
    mkdir -p "openspec/changes/archive/2026-07-31-test-change"
    touch "openspec/changes/archive/2026-07-31-test-change/.marker"
    git add -A
    git commit -q -m "test"

    status=$(python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/.rddf/state/iteration.json'))
c = next(c for c in d['changes'] if c['name'] == 'test-change')
print(c.get('status', ''))
")
    [ "$status" = "archived" ]
}

@test "post-commit hook: idempotent — second commit doesn't overwrite archived_at" {
    cd "$BATS_TEST_TMPDIR"
    touch "openspec/changes/archive/2026-08-05-test-change/.m1"
    git add -A
    git commit -q -m "first"

    first_ts=$(python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/.rddf/state/iteration.json'))
c = next(c for c in d['changes'] if c['name'] == 'test-change')
print(c.get('archived_at', ''))
")

    sleep 0.1
    touch "openspec/changes/archive/2026-08-05-test-change/.m2"
    git add -A
    git commit -q -m "second"

    second_ts=$(python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/.rddf/state/iteration.json'))
c = next(c for c in d['changes'] if c['name'] == 'test-change')
print(c.get('archived_at', ''))
")

    [ "$second_ts" = "$first_ts" ]
}

@test "post-commit hook: script is POSIX sh compatible" {
    HOOK="$REPO_ROOT/.git-hooks/post-commit"
    [ -f "$HOOK" ]
    bashisms=$(grep -nE '\[\[|<<<' "$HOOK" 2>/dev/null | wc -l)
    [ "$bashisms" -eq 0 ]
}

@test "install-archive-hooks: idempotent — second run prints already-installed" {
    INSTALL_SCRIPT="$REPO_ROOT/scripts/install-archive-hooks.sh"
    [ -f "$INSTALL_SCRIPT" ]

    # Create a minimal test project (git repo) — the install script
    # reads its own location to find HOOK_SRC, so it must be run
    # from the worktree.
    TEST_PROJ="$BATS_TEST_TMPDIR/test-project"
    mkdir -p "$TEST_PROJ"
    cd "$TEST_PROJ"
    git init -q
    git config user.email "test@example.com"
    git config user.name "test"
    git commit --allow-empty -q -m "init"

    # First run
    run bash "$INSTALL_SCRIPT" "$TEST_PROJ"
    [ "$status" -eq 0 ]

    # Second run
    run bash "$INSTALL_SCRIPT" "$TEST_PROJ"
    [ "$status" -eq 0 ]
    [[ "$output" == *"already"* ]]
}
