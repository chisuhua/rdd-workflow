load ../test_helper

@test "archive-proposal-status: update script exists" {
    PROJECT_ROOT="$REPO_ROOT"
    run test -f "$PROJECT_ROOT/skills/propose/scripts/update_proposal_status.py"
    [ "$status" -eq 0 ]
}

@test "archive-proposal-status: normal update changes status" {
    TEST_DIR=$(mktemp -d)
    # Proposal model migrated from JSON (proposal-suggestions.md) to dual-index
    # markdown (proposal-approved.md + .rddf/improvements/). The update script now
    # reads proposal-approved.md and moves the entry to the "已实施" section.
    mkdir -p "$TEST_DIR/.rddf/improvements"
    cat > "$TEST_DIR/proposal-approved.md" <<'MD'
# 已批准提案

| Proposal | Priority | Approved |
|----------|----------|----------|
| [test-change](.rddf/improvements/test-change.md) | P1 | 2026-07-20 |

## 已实施

| Proposal | Priority | Completed |
|----------|----------|-----------|
MD
    echo "# test change" > "$TEST_DIR/.rddf/improvements/test-change.md"
    PROJECT_ROOT="$REPO_ROOT"
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
| [other](.rddf/improvements/other.md) | P1 | 2026-07-20 |

## 已实施

| Proposal | Priority | Completed |
|----------|----------|-----------|
MD
    PROJECT_ROOT="$REPO_ROOT"
    run python3 "$PROJECT_ROOT/skills/propose/scripts/update_proposal_status.py" "nonexistent" "$TEST_DIR"
    [ "$status" -eq 1 ]
    rm -rf "$TEST_DIR"
}

@test "archive-proposal-status: archive.sh calls update_proposal_status" {
    PROJECT_ROOT="$REPO_ROOT"
    run grep -c "update_proposal_status" "$PROJECT_ROOT/_lib/archive.sh"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "archive-proposal-status: preserves existing completed entries" {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/.rddf/improvements"
    cat > "$TEST_DIR/proposal-approved.md" <<'MD'
# 已批准提案

| Proposal | Priority | Approved |
|----------|----------|----------|
| [new-change](.rddf/improvements/new-change.md) | P1 | 2026-07-31 |

## 已实施

| Proposal | Priority | Completed |
|----------|----------|-----------|
| [old-a](.rddf/improvements/old-a.md) | P0 | 2026-07-20 |
| [old-b](.rddf/improvements/old-b.md) | P1 | 2026-07-22 |
MD
    echo "# old a" > "$TEST_DIR/.rddf/improvements/old-a.md"
    echo "# old b" > "$TEST_DIR/.rddf/improvements/old-b.md"
    echo "# new change" > "$TEST_DIR/.rddf/improvements/new-change.md"
    PROJECT_ROOT="$REPO_ROOT"
    run python3 "$PROJECT_ROOT/skills/propose/scripts/update_proposal_status.py" "new-change" "$TEST_DIR"
    [ "$status" -eq 0 ]
    # 已实施表必须包含 new-change + 全部旧条目 (old-a, old-b)
    completed_entries=$(python3 -c "
with open('$TEST_DIR/proposal-approved.md') as f:
    content = f.read()
section = content.split('## 已实施')[1]
import re
names = re.findall(r'\[([^\]]+)\]\(.rddf/improvements/', section)
print(' '.join(sorted(names)))
")
    [ "$completed_entries" = "new-change old-a old-b" ]
    rm -rf "$TEST_DIR"
}

@test "archive-proposal-status: consecutive archives accumulate entries" {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/.rddf/improvements"
    cat > "$TEST_DIR/proposal-approved.md" <<'MD'
# 已批准提案

| Proposal | Priority | Approved |
|----------|----------|----------|
| [c1](.rddf/improvements/c1.md) | P0 | 2026-07-31 |
| [c2](.rddf/improvements/c2.md) | P1 | 2026-07-31 |
| [c3](.rddf/improvements/c3.md) | P2 | 2026-07-31 |

## 已实施

| Proposal | Priority | Completed |
|----------|----------|-----------|
| [base](.rddf/improvements/base.md) | P1 | 2026-07-01 |
MD
    echo "# x" > "$TEST_DIR/.rddf/improvements/c1.md"
    echo "# x" > "$TEST_DIR/.rddf/improvements/c2.md"
    echo "# x" > "$TEST_DIR/.rddf/improvements/c3.md"
    echo "# x" > "$TEST_DIR/.rddf/improvements/base.md"
    PROJECT_ROOT="$REPO_ROOT"
    for c in c1 c2 c3; do
        run python3 "$PROJECT_ROOT/skills/propose/scripts/update_proposal_status.py" "$c" "$TEST_DIR"
        [ "$status" -eq 0 ]
    done
    count=$(grep -c '.rddf/improvements/' "$TEST_DIR/proposal-approved.md" 2>/dev/null || true)
    # 已批准区 0 + 已实施区 4 (base+c1+c2+c3)
    [ "$count" -eq 4 ]
    rm -rf "$TEST_DIR"
}
