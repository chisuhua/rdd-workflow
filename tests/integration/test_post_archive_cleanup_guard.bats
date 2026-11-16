#!/usr/bin/env bats
# tests/integration/test_post_archive_cleanup_guard.bats
#
# _lib/post_archive_cleanup.sh is a LIBRARY (functions only, no entry point).
# Executing it with `bash` used to be a silent no-op with exit 0 — that is how
# phase3 lost the improvement-approved.md sync (doctor proposal-section
# CRITICAL). These tests pin the loud failure, the visible source warning, and
# the e2e that the CORRECT call actually syncs.

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    git init -q .
    git config user.email t@t.invalid
    git config user.name tester
    mkdir -p .rddf openspec/changes/archive/2026-01-01-demo
    ln -s "$REPO_ROOT/_lib" _lib
    cat > improvement-approved.md <<'MD'
# 已批准提案

## 已批准提案

| 提案 | 优先级 | 批准时间 | 批准者 |
|------|--------|----------|--------|
| [demo](.rddf/improvements/demo.md) | P1 | 2026-01-01 | rdd-planner |

## 已实施

| 提案 | 优先级 | 实现时间 | 状态 |
|------|--------|----------|------|
MD
    git add -A
    git commit -q -m fixture
}

teardown() {
    cd /
    rm -rf "$TEST_TMP"
}

@test "cleanup: executing the library directly fails loudly instead of doing nothing" {
    run bash "$REPO_ROOT/_lib/post_archive_cleanup.sh" "$TEST_TMP" demo
    [ "$status" -eq 2 ]
    [[ "$output" == *"library"* ]]
    [[ "$output" == *"post_archive_cleanup <project_root> <change_name>"* ]]
}

@test "cleanup: warns when state.sh cannot be found anywhere" {
    # Copy the library to a directory without state.sh so neither the project
    # copy nor the self-discovery fallback can resolve it.
    mkdir -p "$TEST_TMP/libonly"
    cp "$REPO_ROOT/_lib/post_archive_cleanup.sh" "$TEST_TMP/libonly/"
    rm -f "$TEST_TMP/_lib"
    run bash -c "source '$TEST_TMP/libonly/post_archive_cleanup.sh'; post_archive_cleanup '$TEST_TMP' demo"
    [[ "$output" == *"state.sh not found"* ]]
}

@test "cleanup: global-install shape (no project _lib) still syncs via self-discovery" {
    # Simulates a user project: _lib/ is NOT under the project root, the
    # library lives in the install tree. The sync must still work — silence
    # here would be the pre-fix behaviour, a WARN on every archive would be noise.
    mkdir -p "$TEST_TMP/install/_lib"
    cp "$REPO_ROOT/_lib/post_archive_cleanup.sh" "$REPO_ROOT/_lib/state.sh" "$TEST_TMP/install/_lib/"
    rm -f "$TEST_TMP/_lib"
    run bash -c "source '$TEST_TMP/install/_lib/post_archive_cleanup.sh'; post_archive_cleanup '$TEST_TMP' demo"
    grep -qE "\| \[demo\]\(\.rddf/improvements/demo\.md\) \| P1 \| [0-9-]+ \| 已实施 \|" \
        "$TEST_TMP/improvement-approved.md"
    [[ "$output" != *"state.sh not found"* ]]
}

@test "cleanup: the correct call syncs improvement-approved.md (e2e)" {
    run bash -c "source '$REPO_ROOT/_lib/post_archive_cleanup.sh'; post_archive_cleanup '$TEST_TMP' demo"
    # the completion date is rewritten to "today" by mark_approved_completed,
    # so assert the row's new shape, not its original date
    grep -qE "\| \[demo\]\(\.rddf/improvements/demo\.md\) \| P1 \| [0-9-]+ \| 已实施 \|" \
        "$TEST_TMP/improvement-approved.md"
}

@test "cleanup: repeated calls stay idempotent (no duplicate rows)" {
    bash -c "source '$REPO_ROOT/_lib/post_archive_cleanup.sh'; post_archive_cleanup '$TEST_TMP' demo" >/dev/null 2>&1
    bash -c "source '$REPO_ROOT/_lib/post_archive_cleanup.sh'; post_archive_cleanup '$TEST_TMP' demo" >/dev/null 2>&1
    [ "$(grep -c '| \[demo\](' "$TEST_TMP/improvement-approved.md")" -eq 1 ]
}
