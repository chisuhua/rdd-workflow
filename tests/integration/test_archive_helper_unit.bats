load ../test_helper

@test "archive_helper: archive_test_setup creates temp git repo with openspec structure" {
    source "$REPO_ROOT/tests/_lib/test_archive_helper.bash"
    archive_test_setup "test-change"

    [[ -d "$TEST_REPO_DIR" ]]
    [[ -f "$TEST_REPO_DIR/README.md" ]]
    [[ -d "$TEST_REPO_DIR/openspec/changes/test-change" ]]
    [[ -d "$TEST_REPO_DIR/openspec/changes/archive" ]]
    [[ -d "$TEST_REPO_DIR/openspec/specs" ]]
    [[ -n "$TEST_CHANGE_NAME" ]]
    [[ "$TEST_CHANGE_NAME" == "test-change" ]]

    archive_test_teardown
}

@test "archive_helper: archive_test_setup supports custom change name" {
    source "$REPO_ROOT/tests/_lib/test_archive_helper.bash"
    archive_test_setup "my-feature"
    [[ "$TEST_CHANGE_NAME" == "my-feature" ]]
    [[ -d "$TEST_REPO_DIR/openspec/changes/my-feature" ]]
    archive_test_teardown
}
