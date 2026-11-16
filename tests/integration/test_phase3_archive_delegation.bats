#!/usr/bin/env bats
# tests/integration/test_phase3_archive_delegation.bats
#
# P3 must delegate worktree-mode archiving to archive_change (the single
# implementation) and map its return codes:
#   0 → 0 (archived)   3 → 7 (gate refused)   1 → 3 (precondition/merge failed)
#
# Delegating also fixes the record loss: archive_change archives in the MAIN
# repo, while the previous inline path archived inside the worktree — a
# throwaway copy when openspec/ is untracked.

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    git init -q .
    git config user.email t@t.invalid
    git config user.name tester
    mkdir -p .rddf/state/builder openspec/changes/demo bin
    ln -s "$REPO_ROOT/_lib" _lib
    printf '# demo\n\n## Acceptance\n\n- [ ] AC one\n' > openspec/changes/demo/proposal.md
    printf '## Tasks\n\n- [x] task one\n' > openspec/changes/demo/tasks.md
    printf '{"execution_mode_decision": {"mode": "worktree"}}\n' > .rddf/state/builder/demo.json
    printf '#!/bin/sh\nexit 0\n' > bin/openspec
    chmod +x bin/openspec
    git add -A
    git commit -q -m fixture
}

teardown() {
    cd /
    rm -rf "$TEST_TMP"
}

@test "phase3: worktree mode without a worktree exits 3" {
    run env PROJECT_ROOT="$TEST_TMP" PATH="$TEST_TMP/bin:$PATH" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
    [ "$status" -eq 3 ]
}

@test "phase3: no longer calls 'openspec archive' itself in worktree mode" {
    # The delegation owns the archive; a second call would archive twice.
    # Exactly one EXECUTABLE call must remain: the lightweight branch.
    # (Comments mentioning the command are not calls.)
    run grep -E "^[[:space:]]+openspec archive" \
        "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh"
    [ "$(echo "$output" | grep -c "openspec archive")" -eq 1 ]
}

@test "phase3: no longer calls post_archive_cleanup itself (archive_change does)" {
    run grep -c "post_archive_cleanup" "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh"
    [ "$output" -eq 0 ]
}

@test "phase3: worktree mode delegates to archive_change" {
    run grep -c "archive_change \"\$CHANGE_NAME\"" \
        "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh"
    [ "$output" -eq 1 ]
}

@test "phase3: maps archive_change exit 3 (gate refused) to exit 7" {
    run grep -A 6 "archive_change \"\$CHANGE_NAME\"" \
        "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh"
    [[ "$output" == *"3)"* ]]
    [[ "$output" == *"exit 7"* ]]
}
