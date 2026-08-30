#!/usr/bin/env bats
# tests/integration/test_install_git_hooks.bats
#
# Verifies `install.sh --git-hooks` installs a repo-local post-commit hook
# and that the hook is executable.
#
# Runs from the repo root (like other install_* tests) — creates a throwaway
# git repo under $BATS_TMPDIR, never touches the source repo's .git/.

load test_helper

setup() {
    export GIT_HOOK_TEST_DIR
    GIT_HOOK_TEST_DIR="$(mktemp -d "${BATS_TMPDIR}/install-git-hooks.XXXXXX")"
}

teardown() {
    rm -rf "$GIT_HOOK_TEST_DIR"
}

@test "install.sh: --git-hooks installs post-commit hook" {
    [ -x "$REPO_ROOT/install.sh" ] || skip "install.sh not present"

    cd "$GIT_HOOK_TEST_DIR"
    git init -q .

    run bash "$REPO_ROOT/install.sh" --git-hooks "$GIT_HOOK_TEST_DIR"
    [ "$status" -eq 0 ]
    assert_file_exists "$GIT_HOOK_TEST_DIR/.git/hooks/post-commit"
    [ -x "$GIT_HOOK_TEST_DIR/.git/hooks/post-commit" ]
    assert_file_contains "$GIT_HOOK_TEST_DIR/.git/hooks/post-commit" "rddf"
}