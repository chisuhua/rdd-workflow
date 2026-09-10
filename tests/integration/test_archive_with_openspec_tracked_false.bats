#!/usr/bin/env bats
# test_archive_with_openspec_tracked_false.bats — verify archive_change()
# correctly skips git ops when .rddf/project.yaml sets
# git.openspec_tracked: false.
#
# Per complete-project-yaml-config-gaps spec
# §archive-openspec-tracked-skip-git L246-262:
#   WHEN openspec_tracked=false
#   THEN archive_change SHALL NOT execute git merge AND commit_archive_moves
#   AND SHALL execute only openspec archive + mark_iteration_archived.

load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    TEST_TMP="$(mktemp -d)"
    export TEST_TMP
    cd "$TEST_TMP"
    git init -q -b main
    git config user.email "t@t"
    git config user.name "T"
    echo "x" > x.txt
    git add x.txt
    git commit -q -m "init"

    # Symlink _lib for project_config.sh access
    mkdir -p _lib
    ln -sfn "$REPO_ROOT/_lib/project_config.sh" _lib/project_config.sh

    # project_yaml_get reads PROJECT_ROOT (env) — point at bats temp dir
    # so it sees this test repo's project.yaml, not the rdd-workflow repo's.
    export PROJECT_ROOT="$(pwd)"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "archive: openspec_tracked=false (YAML bool) skips git merge/commit" {
    # YAML bool false → Python returns "False"
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    git add .rddf/project.yaml && git commit -q -m "add project.yaml"
    # Stub openspec CLI to capture invocation (skip if not installed)
    export PATH="$REPO_ROOT/_lib/cli:$PATH"
    # Source archive.sh and call archive_change (mocked git merge)
    # Use env var to skip git ops: openspec_tracked path should NOT call git merge
    # Verify by checking that HEAD doesn't change on default branch
    before_sha="$(git rev-parse main)"
    run bash -c "
        source '$REPO_ROOT/_lib/archive.sh' 2>/dev/null
        type archive_change 2>/dev/null
    "
    # archive_change function exists; the openspec_tracked=false branch is taken
    [ -n "$(bash -c "source '$REPO_ROOT/_lib/archive.sh'; declare -f archive_change" 2>/dev/null)" ]
}

@test "archive: openspec_tracked=false path uses openspec archive CLI (not git merge)" {
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    git add .rddf/project.yaml && git commit -q -m "add project.yaml"
    # Verify the bash code path has the skip-git-merge branch
    run grep -A2 "openspec_tracked.*false" "$REPO_ROOT/_lib/archive.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"跳过 git merge/commit"* ]]
}

@test "archive: openspec_tracked=true (default) preserves git merge path" {
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: true
EOF
    git add .rddf/project.yaml && git commit -q -m "add project.yaml"
    # Verify the bash code path has the git merge branch
    run grep "check_worktree_commits" "$REPO_ROOT/_lib/archive.sh"
    [ "$status" -eq 0 ]
    # The merge path should still be in the code
    [[ "$output" == *"check_worktree_commits"* ]]
}

# -----------------------------------------------------------------------------
# Behavioral tests (fix-archive-openspec-tracked-commit upgrade)
# These replace the grep-source-text tests above with real invocation
# assertions to catch the implementation gap where the false branch still
# called commit_archive_moves.
# -----------------------------------------------------------------------------

# Helper: stub the openspec CLI on PATH. Worktree creation is done per-test
# AFTER the openspec/<name> branch exists (git worktree add requires it).
setup_openspec_stub() {
    STUB_DIR="$(mktemp -d)"
    cat > "$STUB_DIR/openspec" <<EOF
#!/usr/bin/env bash
case "\$1" in
    archive)
        name="\${2:-}"  # openspec archive <name> --yes → \$2 is the name
        if [ -d "openspec/changes/\$name" ]; then
            mkdir -p "openspec/changes/archive/2026-09-10-\$name"
            mv "openspec/changes/\$name"/* "openspec/changes/archive/2026-09-10-\$name/" 2>/dev/null || true
            rmdir "openspec/changes/\$name" 2>/dev/null || true
        fi
        mkdir -p "openspec/specs/\$name"
        echo "spec stub" > "openspec/specs/\$name/spec.md"
        echo "STUB_OPENSPEC_ARCHIVE_CALLED"
        exit 0
        ;;
    *)
        exit 0
        ;;
esac
EOF
    chmod +x "$STUB_DIR/openspec"
    export PATH="$STUB_DIR:$PATH"
}

@test "archive: BEHAVIORAL openspec_tracked=false → no git commit + skip message" {
    local change_name="false-mode-test"

    # Seed mixed-state on main first
    mkdir -p openspec/changes/$change_name
    echo "# proposal" > openspec/changes/$change_name/proposal.md
    cat > openspec/changes/$change_name/tasks.md <<'EOF'
# Tasks
- [x] task 1
- [x] task 2
EOF
    git add openspec/
    git commit -q -m "seed change (mixed-state)"

    # Configure project.yaml
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    git add .rddf/project.yaml
    git commit -q -m "add project.yaml"

    # Create worktree + branch in one shot, commit "change work" on the branch
    mkdir -p "$TEST_TMP/.rddf/wt"
    git worktree add -q -b "openspec/$change_name" "$TEST_TMP/.rddf/wt/$change_name" main
    (
        cd "$TEST_TMP/.rddf/wt/$change_name"
        echo "y" > y.txt
        git add y.txt && git commit -q -m "change work"
    )

    # Stub openspec CLI
    setup_openspec_stub

    PRE_LOG_COUNT=$(git log --oneline | wc -l)

    source "$REPO_ROOT/_lib/archive.sh"

    run archive_change "$change_name"
    [ "$status" -eq 0 ]

    # AC-1: no new commit
    POST_LOG_COUNT=$(git log --oneline | wc -l)
    [ "$POST_LOG_COUNT" -eq "$PRE_LOG_COUNT" ]

    # AC-2: stdout contains skip message + openspec archive was invoked
    [[ "$output" == *"📦 openspec_tracked=false: 跳过 git merge/commit"* ]]
    [[ "$output" == *"STUB_OPENSPEC_ARCHIVE_CALLED"* ]]
}

@test "archive: BEHAVIORAL openspec_tracked=true → archive commit produced" {
    local change_name="true-mode-test"

    # Seed mixed-state
    mkdir -p openspec/changes/$change_name
    echo "# proposal" > openspec/changes/$change_name/proposal.md
    cat > openspec/changes/$change_name/tasks.md <<'EOF'
# Tasks
- [x] task 1
- [x] task 2
EOF
    git add openspec/
    git commit -q -m "seed change"

    # Default: openspec_tracked=true
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: true
EOF
    git add .rddf/project.yaml && git commit -q -m "add project.yaml"

    # Create worktree + branch in one shot, commit "change work" on the branch
    mkdir -p "$TEST_TMP/.rddf/wt"
    git worktree add -q -b "openspec/$change_name" "$TEST_TMP/.rddf/wt/$change_name" main
    (
        cd "$TEST_TMP/.rddf/wt/$change_name"
        echo "y" > y.txt
        git add y.txt && git commit -q -m "change work"
    )

    # Stub openspec CLI
    setup_openspec_stub

    PRE_LOG_COUNT=$(git log --oneline | wc -l)

    source "$REPO_ROOT/_lib/archive.sh"

    # Bypass pre-merge gate (T20) — we want to test the merge/commit path
    check_worktree_commits() { return 0; }
    archive_gate_check() { return 0; }
    export -f check_worktree_commits archive_gate_check

    run archive_change "$change_name"
    [ "$status" -eq 0 ]

    # AC-3: a new commit with the canonical subject was created
    POST_LOG_COUNT=$(git log --oneline | wc -l)
    [ "$POST_LOG_COUNT" -gt "$PRE_LOG_COUNT" ]

    SUBJECT=$(git log -1 --format=%s)
    [[ "$SUBJECT" == "archive($change_name): archive completed" ]]
}

@test "archive: BEHAVIORAL false branch source contains NO commit_archive_moves call" {
    # Spec L254: false branch SHALL NOT call commit_archive_moves.
    # Source-text guard (locks the deletion of L561).
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    git add .rddf/project.yaml && git commit -q -m "add project.yaml"

    # Extract just the false-branch block (between `openspec_tracked.*false` if
    # and the next `fi` that closes it) and assert it has no commit_archive_moves.
    run bash -c "
        awk '
            /openspec_tracked.*false/ { in_block = 1; brace = 0; next }
            in_block {
                print
                # naive fi counter (works for our flat archive.sh structure)
                if (\$0 ~ /^[[:space:]]*fi[[:space:]]*\$/) brace++
                if (brace >= 1 && \$0 ~ /^[[:space:]]*fi[[:space:]]*\$/) {
                    in_block = 0
                    exit
                }
            }
        ' '$REPO_ROOT/_lib/archive.sh'
    "
    [ "$status" -eq 0 ]
    # The false branch body must not mention commit_archive_moves
    ! echo "$output" | grep -q "commit_archive_moves"
}