#!/usr/bin/env bats
# tests/integration/test_index_file_location.bats
#
# The two proposal index files are canonical at `.rddf/<name>` (ADR-0026) with
# the legacy project-root copy still honored — `_lib/core/rddf_paths.py` is the
# rule, `_lib/state.sh::rddf_index_file` the bash mirror. These cases pin the
# precedence and the link form each location needs; without them the resolver
# would be an unverified claim.
#
# Run: bats tests/integration/test_index_file_location.bats

load ../test_helper

@test "rddf_index_file: .rddf/ copy wins when both exist" {
    source "$REPO_ROOT/_lib/state.sh"
    d=$(mktemp -d)
    mkdir -p "$d/.rddf"
    echo "# canon" > "$d/.rddf/improvement-approved.md"
    echo "# legacy" > "$d/improvement-approved.md"

    run rddf_index_file "$d" improvement-approved.md
    [ "$status" -eq 0 ]
    [ "$output" = "$d/.rddf/improvement-approved.md" ]
    rm -rf "$d"
}

@test "rddf_index_file: legacy root copy is still resolved" {
    source "$REPO_ROOT/_lib/state.sh"
    d=$(mktemp -d)
    echo "# legacy" > "$d/improvement-suggestions.md"

    run rddf_index_file "$d" improvement-suggestions.md
    [ "$status" -eq 0 ]
    [ "$output" = "$d/improvement-suggestions.md" ]
    rm -rf "$d"
}

@test "rddf_index_file: defaults to the canonical .rddf/ path" {
    source "$REPO_ROOT/_lib/state.sh"
    d=$(mktemp -d)

    run rddf_index_file "$d" improvement-approved.md
    [ "$status" -eq 0 ]
    [ "$output" = "$d/.rddf/improvement-approved.md" ]
    rm -rf "$d"
}

@test "link prefix: relative for a .rddf/-hosted index, root-relative otherwise" {
    source "$REPO_ROOT/_lib/state.sh"

    run rddf_improvement_link_prefix "/p/.rddf/improvement-approved.md"
    [ "$output" = "improvements/" ]

    run rddf_improvement_link_prefix "/p/improvement-approved.md"
    [ "$output" = ".rddf/improvements/" ]
}

@test "append_approved: writes a relative link into a .rddf/-hosted index" {
    d=$(mktemp -d)
    mkdir -p "$d/.rddf"
    cat > "$d/.rddf/improvement-approved.md" << 'EOF'
# 已批准提案

| 提案 | 优先级 | 批准时间 | 批准人 |
|------|--------|----------|--------|

## 已实施

| 提案 | 优先级 | 实施时间 |
|------|--------|----------|
EOF

    source "$REPO_ROOT/_lib/state.sh"
    append_approved "$d" "new-approval" "P2"
    grep -q '\[new-approval\](improvements/new-approval.md)' "$d/.rddf/improvement-approved.md"
    rm -rf "$d"
}

@test "sync_suggestions: removes the row from a .rddf/-hosted suggestions index" {
    d=$(mktemp -d)
    mkdir -p "$d/.rddf"
    cat > "$d/.rddf/improvement-suggestions.md" << 'EOF'
# 提案池

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [done-one](improvements/done-one.md) | P1 | audit | 2026-11-01 | 待讨论 |
EOF

    source "$REPO_ROOT/_lib/state.sh"
    sync_suggestions "$d" "done-one" "approved"
    ! grep -q 'done-one' "$d/.rddf/improvement-suggestions.md"
    rm -rf "$d"
}
