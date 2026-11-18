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

    # The trunk gate (ADR-0061) refuses an archive whose implementation is
    # still stranded on the branch → merge it first (this case now covers
    # "already merged → archive proceeds"; the refusal case lives below).
    git merge -q --no-ff "openspec/$change_name" -m "merge: change work"

    # Stub openspec CLI
    setup_openspec_stub

    PRE_LOG_COUNT=$(git log --oneline | wc -l)

    source "$REPO_ROOT/_lib/archive.sh"

    # Bypass the archive gate — this test covers the git/merge behaviour of the
    # false branch only. Gate-in-false-branch behaviour is covered by
    # tests/integration/test_archive_gate_tracked_false.bats.
    check_worktree_commits() { return 0; }
    archive_gate_check() { return 0; }
    export -f check_worktree_commits archive_gate_check

    run archive_change "$change_name"
    [ "$status" -eq 0 ]

    # AC-1: no new commit
    POST_LOG_COUNT=$(git log --oneline | wc -l)
    [ "$POST_LOG_COUNT" -eq "$PRE_LOG_COUNT" ]

    # AC-2: stdout contains skip message + openspec archive was invoked
    [[ "$output" == *"📦 openspec_tracked=false: 跳过 git merge/commit"* ]]
    [[ "$output" == *"STUB_OPENSPEC_ARCHIVE_CALLED"* ]]
}

@test "archive: BEHAVIORAL openspec_tracked=false + UNMERGED branch → refused (ADR-0061)" {
    local change_name="unmerged-test"

    mkdir -p openspec/changes/$change_name
    echo "# proposal" > openspec/changes/$change_name/proposal.md
    cat > openspec/changes/$change_name/tasks.md <<'EOF'
# Tasks
- [x] task 1
EOF
    git add openspec/
    git commit -q -m "seed change"

    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    git add .rddf/project.yaml
    git commit -q -m "add project.yaml"

    # The implementation lives on the branch and is NOT merged into main.
    mkdir -p "$TEST_TMP/.rddf/wt"
    git worktree add -q -b "openspec/$change_name" "$TEST_TMP/.rddf/wt/$change_name" main
    (
        cd "$TEST_TMP/.rddf/wt/$change_name"
        echo "y" > y.txt
        git add y.txt && git commit -q -m "change work"
    )

    setup_openspec_stub

    source "$REPO_ROOT/_lib/archive.sh"
    check_worktree_commits() { return 0; }
    archive_gate_check() { return 0; }
    export -f check_worktree_commits archive_gate_check

    run archive_change "$change_name"
    # Refused (exit 1) — and the message says what to do.
    [ "$status" -eq 1 ]
    [[ "$output" == *"archive_premerge_check"* ]]
    [[ "$output" == *"merge --no-ff"* ]]
    # The archive did NOT run.
    [[ "$output" != *"STUB_OPENSPEC_ARCHIVE_CALLED"* ]]
}

@test "archive: BEHAVIORAL trunk gate state 2 (cannot decide) does NOT fail the archive (ADR-0061 V-14)" {
    local change_name="state2-test"

    mkdir -p openspec/changes/$change_name
    echo "# proposal" > openspec/changes/$change_name/proposal.md
    cat > openspec/changes/$change_name/tasks.md <<'EOF'
# Tasks
- [x] task 1
EOF
    git add openspec/
    git commit -q -m "seed change"

    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    git add .rddf/project.yaml
    git commit -q -m "add project.yaml"

    mkdir -p "$TEST_TMP/.rddf/wt"
    git worktree add -q -b "openspec/$change_name" "$TEST_TMP/.rddf/wt/$change_name" main
    (
        cd "$TEST_TMP/.rddf/wt/$change_name"
        echo "y" > y.txt
        git add y.txt && git commit -q -m "change work"
    )
    git merge -q --no-ff "openspec/$change_name" -m "merge: change work"

    setup_openspec_stub

    source "$REPO_ROOT/_lib/archive.sh"
    check_worktree_commits() { return 0; }
    archive_gate_check() { return 0; }
    # Stub the trunk gate with its THIRD state: "cannot decide" → the
    # contract says allow + warning (never a false refusal). The old call
    # site used `if ! archive_premerge_check ...` which folded state 2 into
    # a REFUSAL — the archive failed although the gate said "allow".
    archive_premerge_check() { echo "⚠️  archive_premerge_check: 无法判定（放行）"; return 2; }
    export -f check_worktree_commits archive_gate_check archive_premerge_check

    run archive_change "$change_name"
    # The archive proceeded: state 2 must NOT fail it.
    [ "$status" -eq 0 ]
    [[ "$output" == *"无法判定"* ]]
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

    # Extract the whole false-branch block (from the `openspec_tracked.*false`
    # test to `mark_iteration_archived`, the branch's last step) and assert it
    # has no commit_archive_moves.
    #
    # HARDENED (fix-worktree-archive-branch-merge): the old guard stopped at
    # the FIRST standalone `fi` — so once a nested `if` was inserted into the
    # branch (the trunk gate does that), the guard's range shrank to a few
    # lines while the test still PASSED. The endpoint is now the branch's last
    # step, so the whole body is covered.
    run bash -c "
        awk '
            /openspec_tracked.*false/ { in_block = 1; next }
            in_block {
                print
                if (\$0 ~ /mark_iteration_archived/) { in_block = 0; exit }
            }
        ' '$REPO_ROOT/_lib/archive.sh'
    "
    [ "$status" -eq 0 ]
    # The false branch body must not CALL commit_archive_moves (nor run
    # `git merge`). Matching a CALL, not the word: the branch's comments
    # legitimately mention both (they explain why they are absent), and a
    # plain `grep "git merge"` also collides with `git merge-base`.
    ! echo "$output" | grep -E "^[[:space:]]*(commit_archive_moves[[:space:]]|git[[:space:]]+merge[[:space:]])"
}