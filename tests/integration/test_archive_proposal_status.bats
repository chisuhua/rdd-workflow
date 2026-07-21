load ../test_helper

@test "archive-proposal-status: update script exists" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run test -f "$PROJECT_ROOT/skills/propose/scripts/update_proposal_status.py"
    [ "$status" -eq 0 ]
}

@test "archive-proposal-status: normal update changes status" {
    TEST_DIR=$(mktemp -d)
    echo '[{"name":"test-change","status":"skeleton"},{"name":"other","status":"completed"}]' > "$TEST_DIR/proposal-suggestions.md"
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run python3 "$PROJECT_ROOT/skills/propose/scripts/update_proposal_status.py" "test-change" "$TEST_DIR"
    [ "$status" -eq 0 ]
    result=$(python3 -c "import json; d=json.load(open('$TEST_DIR/proposal-suggestions.md')); print([i['status'] for i in d if i['name']=='test-change'][0])")
    [ "$result" = "已完成" ]
    rm -rf "$TEST_DIR"
}

@test "archive-proposal-status: missing entry returns 1" {
    TEST_DIR=$(mktemp -d)
    echo '[{"name":"other","status":"completed"}]' > "$TEST_DIR/proposal-suggestions.md"
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run python3 "$PROJECT_ROOT/skills/propose/scripts/update_proposal_status.py" "nonexistent" "$TEST_DIR"
    [ "$status" -eq 1 ]
    rm -rf "$TEST_DIR"
}

@test "archive-proposal-status: archive.sh calls update_proposal_status" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run grep -c "update_proposal_status" "$PROJECT_ROOT/skills/_lib/archive.sh"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}
