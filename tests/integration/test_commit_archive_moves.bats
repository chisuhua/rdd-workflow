#!/usr/bin/env bats

# test_commit_archive_moves.bats — verify archive auto-commit helper

load ../test_helper

setup() {
    cd "$BATS_TEST_TMPDIR"
    rm -rf .git openspec 2>/dev/null || true
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
