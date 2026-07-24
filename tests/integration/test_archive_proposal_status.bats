load ../test_helper

@test "archive-proposal-status: update script exists" {
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run test -f "$PROJECT_ROOT/skills/propose/scripts/update_proposal_status.py"
    [ "$status" -eq 0 ]
}

@test "archive-proposal-status: normal update changes status" {
    TEST_DIR=$(mktemp -d)
    # Proposal model migrated from JSON (proposal-suggestions.md) to dual-index
    # markdown (proposal-approved.md + improvements/). The update script now
    # reads proposal-approved.md and moves the entry to the "已实施" section.
    mkdir -p "$TEST_DIR/improvements"
    cat > "$TEST_DIR/proposal-approved.md" <<'MD'
# 已批准提案

| Proposal | Priority | Approved |
|----------|----------|----------|
| [test-change](improvements/test-change.md) | P1 | 2026-07-20 |

## 已实施

| Proposal | Priority | Completed |
|----------|----------|-----------|
MD
    echo "# test change" > "$TEST_DIR/improvements/test-change.md"
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    run python3 "$PROJECT_ROOT/skills/propose/scripts/update_proposal_status.py" "test-change" "$TEST_DIR"
    [ "$status" -eq 0 ]
    # Verify the entry was moved to "已实施" section
    result=$(python3 -c "
with open('$TEST_DIR/proposal-approved.md') as f:
    content = f.read()
lines = content.split('\n')
in_completed = False
found = False
for line in lines:
    if line.startswith('## 已实施'):
        in_completed = True
        continue
    if in_completed and 'test-change' in line:
        found = True
        break
print('completed' if found else 'not-completed')
")
    [ "$result" = "completed" ]
    rm -rf "$TEST_DIR"
}

@test "archive-proposal-status: missing entry returns 1" {
    TEST_DIR=$(mktemp -d)
    # Use the new dual-index markdown format
    cat > "$TEST_DIR/proposal-approved.md" <<'MD'
# 已批准提案

| Proposal | Priority | Approved |
|----------|----------|----------|
| [other](improvements/other.md) | P1 | 2026-07-20 |

## 已实施

| Proposal | Priority | Completed |
|----------|----------|-----------|
MD
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
