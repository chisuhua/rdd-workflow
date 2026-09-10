#!/usr/bin/env bats

# test_commit_archive_moves.bats — verify archive auto-commit helper
#
# Per ADR-0036 M3 + complete-project-yaml-config-gaps spec
# §archive-openspec-tracked-skip-git L246-262: when
# `.rddf/project.yaml` sets `git.openspec_tracked: false`,
# commit_archive_moves SHALL short-circuit (defense-in-depth).

load ../test_helper

setup() {
    cd "$BATS_TEST_TMPDIR"
    rm -rf .git openspec .rddf _lib 2>/dev/null || true
}

@test "commit_archive_moves: stages 3 paths and produces 1 commit" {
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"

    # Simulate state BEFORE openspec archive: active change + new spec already created
    mkdir -p openspec/changes/my-change/specs/my-cap
    mkdir -p openspec/specs/my-cap
    echo "original" > openspec/changes/my-change/.openspec.yaml
    echo "spec" > openspec/changes/my-change/specs/my-cap/spec.md
    git add openspec/
    git commit -q -m "add my-change skeleton"

    # Simulate openspec archive effect: move files
    mkdir -p openspec/changes/archive/2026-07-15-my-change/specs/my-cap
    mv openspec/changes/my-change/.openspec.yaml openspec/changes/archive/2026-07-15-my-change/
    mv openspec/changes/my-change/specs/my-cap/spec.md openspec/changes/archive/2026-07-15-my-change/specs/my-cap/
    rmdir openspec/changes/my-change/specs/my-cap
    rmdir openspec/changes/my-change/specs
    rmdir openspec/changes/my-change

    # Working tree is now dirty. Call helper.
    source "$REPO_ROOT/_lib/archive.sh"
    run commit_archive_moves "my-change" "$(pwd)"
    [ "$status" -eq 0 ]

    # Verify exactly 1 new commit
    NEW_COMMITS=$(git log --oneline | wc -l)
    [ "$NEW_COMMITS" -eq 2 ]

    # Verify message
    SUBJECT=$(git log -1 --format=%s)
    [[ "$SUBJECT" == "archive(my-change): archive completed" ]]

    # Working tree now clean
    [ -z "$(git status --porcelain)" ]
}

@test "commit_archive_moves: SKIP_ARCHIVE_AUTO_COMMIT=yes skips" {
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
    mkdir -p openspec/changes/my-change
    echo "x" > openspec/changes/my-change/.openspec.yaml
    git add openspec/
    git commit -q -m "init"

    export SKIP_ARCHIVE_AUTO_COMMIT=yes
    source "$REPO_ROOT/_lib/archive.sh"
    commit_archive_moves "my-change" "$(pwd)"

    # No new commit
    [ "$(git log --oneline | wc -l)" -eq 1 ]
}

@test "commit_archive_moves: idempotent on already-committed archive" {
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"

    # Pre-committed clean state
    mkdir -p openspec/changes/archive/2026-07-15-done
    echo "x" > openspec/changes/archive/2026-07-15-done/.openspec.yaml
    git add openspec/
    git commit -q -m "init"

    source "$REPO_ROOT/_lib/archive.sh"
    run commit_archive_moves "done" "$(pwd)"
    [ "$status" -eq 0 ]

    # Still just 1 commit
    [ "$(git log --oneline | wc -l)" -eq 1 ]
}

@test "commit_archive_moves: git.openspec_tracked=false skips (defense-in-depth)" {
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
    # project_yaml_get reads PROJECT_ROOT (env) — point at bats temp dir
    export PROJECT_ROOT="$(pwd)"

    # Simulate mixed-state: openspec/ files were previously tracked
    mkdir -p openspec/changes/my-change
    mkdir -p openspec/changes/archive/2026-09-10-my-change
    mkdir -p openspec/specs/my-cap
    echo "tracked-change" > openspec/changes/my-change/.openspec.yaml
    echo "archived" > openspec/changes/archive/2026-09-10-my-change/.openspec.yaml
    echo "spec" > openspec/specs/my-cap/spec.md
    git add openspec/
    git commit -q -m "tracked openspec skeleton"

    # Simulate openspec archive effect: move tracked file
    rm openspec/changes/my-change/.openspec.yaml
    rmdir openspec/changes/my-change 2>/dev/null || true
    # After move: working tree dirty with deleted tracked + new untracked

    # Configure project.yaml: openspec_tracked=false
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    # Symlink _lib for project_config.sh
    mkdir -p _lib
    ln -sfn "$REPO_ROOT/_lib/project_config.sh" _lib/project_config.sh
    git add .rddf/project.yaml _lib/project_config.sh
    git commit -q -m "add project.yaml with openspec_tracked=false"

    PRE_LOG_COUNT=$(git log --oneline | wc -l)

    # Invoke helper directly (NOT via archive_change)
    source "$REPO_ROOT/_lib/archive.sh"
    run commit_archive_moves "my-change" "$(pwd)"
    [ "$status" -eq 0 ]

    # No new commit
    POST_LOG_COUNT=$(git log --oneline | wc -l)
    [ "$POST_LOG_COUNT" -eq "$PRE_LOG_COUNT" ]

    # Stdout contains SKIPPED + openspec_tracked=false
    [[ "$output" == *"SKIPPED"* ]]
    [[ "$output" == *"openspec_tracked=false"* ]]
}

@test "commit_archive_moves: openspec_tracked=false takes precedence over dirty tree" {
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
    # project_yaml_get reads PROJECT_ROOT (env) — point at bats temp dir
    export PROJECT_ROOT="$(pwd)"

    # No tracked openspec files at all — greenfield false-mode
    mkdir -p .rddf
    cat > .rddf/project.yaml <<'EOF'
git:
  openspec_tracked: false
EOF
    mkdir -p _lib
    ln -sfn "$REPO_ROOT/_lib/project_config.sh" _lib/project_config.sh
    git add .rddf/ _lib/
    git commit -q -m "init"

    # Even with completely dirty working tree, openspec_tracked=false wins
    mkdir -p openspec/changes/my-change
    echo "dirty" > openspec/changes/my-change/.openspec.yaml

    source "$REPO_ROOT/_lib/archive.sh"
    run commit_archive_moves "my-change" "$(pwd)"
    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIPPED"* ]]

    # No new commit created
    [ "$(git log --oneline | wc -l)" -eq 1 ]
}