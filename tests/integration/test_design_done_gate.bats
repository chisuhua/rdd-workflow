load ../test_helper

# Regression test for design-done gate column index bug.
#
# Bug: check_design_done_gate() in skills/guide-design/SKILL.md destructured
#      a 5-column row into 6 bash variables: `read -r _ _ _ _ status _`.
#      But `|` splits a 5-column row into 7 fields (empty + name + pri +
#      source + time + status + empty). The 5th variable (named `status`)
#      was actually reading the `added_at` column, not the `状态` column.
# Result: every proposal was treated as pending regardless of its real
#         status, making design-done always fail.
#
# Fix: read -r _ _ _ _ _ status _ (7 vars for 7 fields).
#
# These tests extract the function from SKILL.md (so they test the actual
# code, not a copy) and run it against mock proposal-suggestions.md files
# with hand-crafted column values to nail the regression.

# Extract the function definition from SKILL.md (between `check_design_done_gate() {`
# and the next `^}` at column 0). Source it via eval in setup().
_extract_gate() {
    local skill_md="$REPO_ROOT/skills/guide-design/SKILL.md"
    sed -n '/^check_design_done_gate() {/,/^}$/p' "$skill_md"
}

setup() {
    BATS_TEST_TMPDIR="$(mktemp -d)"
    export PROJECT_ROOT="$BATS_TEST_TMPDIR"
    eval "$(_extract_gate)"
}

teardown() {
    [ -n "$BATS_TEST_TMPDIR" ] && rm -rf "$BATS_TEST_TMPDIR"
}

# Write a mock proposal-suggestions.md with the given data rows.
# Caller passes the rows (without the table header).
_write_suggestions() {
    local data_rows="$1"
    cat > "$BATS_TEST_TMPDIR/proposal-suggestions.md" <<EOF
# 提案池

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
${data_rows}
EOF
}

@test "design-done-gate: all approved → exit 0 (regression for column index bug)" {
    _write_suggestions "| [a](.rddf/improvements/a.md) | P1 | src | 2026-08-01T00:00:00Z | 已批准 |
| [b](.rddf/improvements/b.md) | P0 | src | 2026-08-02T00:00:00Z | 已批准 |"
    run check_design_done_gate
    [ "$status" -eq 0 ]
    [[ "$output" == *"✅"* ]]
}

@test "design-done-gate: pending mixed with approved → exit 1, list pending rows" {
    _write_suggestions "| [a](.rddf/improvements/a.md) | P1 | src | 2026-08-01T00:00:00Z | 已批准 |
| [b](.rddf/improvements/b.md) | P0 | src | 2026-08-02T00:00:00Z | pending |
| [c](.rddf/improvements/c.md) | P1 | src | 2026-08-03T00:00:00Z | 已批准 |"
    run check_design_done_gate
    [ "$status" -eq 1 ]
    [[ "$output" == *"pending"* ]]
}

@test "design-done-gate: rejected and deferred also count as decided" {
    _write_suggestions "| [a](.rddf/improvements/a.md) | P1 | src | 2026-08-01T00:00:00Z | 已拒绝 |
| [b](.rddf/improvements/b.md) | P0 | src | 2026-08-02T00:00:00Z | 延迟 |"
    run check_design_done_gate
    [ "$status" -eq 0 ]
    [[ "$output" == *"✅"* ]]
}

# --- These two tests specifically nail the column index bug ---

@test "design-done-gate: COLUMN INDEX — added_at='pending' must NOT cause gate to fail (status='已批准')" {
    # The bug: buggy version read added_at as status, so this row would
    # be treated as pending. After fix, status column is honored.
    _write_suggestions "| [a](.rddf/improvements/a.md) | P1 | src | pending | 已批准 |"
    run check_design_done_gate
    [ "$status" -eq 0 ]
    [[ "$output" == *"✅"* ]]
}

@test "design-done-gate: COLUMN INDEX — added_at='已批准' must NOT mask real pending status" {
    # Inverse: buggy version would read added_at='已批准' as status and
    # incorrectly accept this row. After fix, status='pending' is detected.
    _write_suggestions "| [a](.rddf/improvements/a.md) | P1 | src | 已批准 | pending |"
    run check_design_done_gate
    [ "$status" -eq 1 ]
    [[ "$output" == *"pending"* ]]
}

# --- Edge cases ---

@test "design-done-gate: empty file → exit 0" {
    : > "$BATS_TEST_TMPDIR/proposal-suggestions.md"
    run check_design_done_gate
    [ "$status" -eq 0 ]
}

@test "design-done-gate: header-only file (no data rows) → exit 0" {
    _write_suggestions ""
    run check_design_done_gate
    [ "$status" -eq 0 ]
}

@test "design-done-gate: missing file → exit 0 (graceful)" {
    # No file created
    run check_design_done_gate
    [ "$status" -eq 0 ]
}

@test "design-done-gate: realistic 7-row batch (matches this session's approval) → exit 0" {
    _write_suggestions "| [fix-rddf-status-corrupt-message](.rddf/improvements/fix-rddf-status-corrupt-message.md) | P1 | src | 2026-08-05T15:59:41Z | 已批准 |
| [fix-archive-iteration-sync](.rddf/improvements/fix-archive-iteration-sync.md) | P0 | src | 2026-08-05T16:05:00Z | 已批准 |
| [fix-archive-on-main-flow](.rddf/improvements/fix-archive-on-main-flow.md) | P0 | src | 2026-08-05T16:05:00Z | 已批准 |
| [add-archive-post-commit-hook-and-force-flag](.rddf/improvements/add-archive-post-commit-hook-and-force-flag.md) | P0 | src | 2026-08-05T16:36:37Z | 已批准 |
| [rddf-iteration-strict-schema](.rddf/improvements/rddf-iteration-strict-schema.md) | P1 | src | 2026-08-05T16:05:00Z | 已批准 |
| [fix-tasks-md-archive-residue](.rddf/improvements/fix-tasks-md-archive-residue.md) | P1 | src | 2026-08-05T16:05:00Z | 已批准 |
| [collect-l2-violation-count-on-archive](.rddf/improvements/collect-l2-violation-count-on-archive.md) | P2 | src | 2026-08-05T16:05:00Z | 已批准 |"
    run check_design_done_gate
    [ "$status" -eq 0 ]
    [[ "$output" == *"✅"* ]]
}
