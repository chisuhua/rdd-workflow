#!/usr/bin/env bats
#
# Integration test for ``rddf migrate-improvements`` subcommand.
#
# Exercises the migration workflow end-to-end via the real Python CLI entry
# point (``python3 -m skills._lib.cli migrate-improvements``) against
# ephemeral third-party project fixtures built in $BATS_TMPDIR. Verifies:
#
#   1. End-to-end success path (mv fallback for non-git tmp dir)
#   2. Refuses when running inside the rdd-workflow source repo itself
#   3. No-op (exit 0) when improvements/ does not exist
#   4. Refuses (exit 1) when .rddf/improvements/ already exists
#   5. Help flag prints usage and returns 0 without touching anything
#   6. --dry-run reports the plan without modifying any files
#   7. Updates markdown links in proposal-approved.md + proposal-suggestions.md
#   8. Updates iteration.json path fields

load ../test_helper

setup() {
    PROJECT_ROOT="$(make_fake_third_party_project)"
    export RDDF_PROJECT_ROOT="$PROJECT_ROOT"
}

teardown() {
    cleanup_fake_project "$PROJECT_ROOT"
}

# ── helpers ──────────────────────────────────────────────────────

make_fake_third_party_project() {
    local proj
    proj="$(mktemp -d -t rddwf-migrate-XXXXXX)"
    mkdir -p "$proj/improvements" "$proj/.rddf/state"
    echo "# Foo"   > "$proj/improvements/foo.md"
    echo "# Bar"   > "$proj/improvements/bar.md"
    cat > "$proj/proposal-approved.md" <<'EOF'
| name | link |
|------|------|
| foo | [foo](improvements/foo.md) |
| bar | [bar](improvements/bar.md) |
EOF
    cat > "$proj/proposal-suggestions.md" <<'EOF'
| name | link |
|------|------|
| foo | [foo](improvements/foo.md) |
EOF
    printf '{"version":1,"changes":[{"name":"foo","path":"improvements/foo.md"}]}' \
        > "$proj/.rddf/state/iteration.json"
    echo "$proj"
}

cleanup_fake_project() {
    local proj="$1"
    [ -n "$proj" ] && [ -d "$proj" ] && rm -rf "$proj"
}

run_migrate() {
    run bash "$REPO_ROOT/skills/cli/rddf.sh" migrate-improvements "$@"
}

# ── tests ────────────────────────────────────────────────────────

@test "migrate-improvements: end-to-end mv fallback path" {
    run_migrate
    [ "$status" -eq 0 ] || { echo "stdout=$output"; return 1; }
    [ -f "$PROJECT_ROOT/.rddf/improvements/foo.md" ]
    [ -f "$PROJECT_ROOT/.rddf/improvements/bar.md" ]
    [ ! -d "$PROJECT_ROOT/improvements" ]
    [[ "$output" == *"迁移完成"* ]] || [[ "$output" == *"2"* ]]
}

@test "migrate-improvements: refuses inside rdd-workflow source repo" {
    # Project root already has skills/INSTALL.md (rdd-workflow source layout)
    mkdir -p "$PROJECT_ROOT/skills"
    touch "$PROJECT_ROOT/skills/INSTALL.md"
    mkdir -p "$PROJECT_ROOT/.rddf/improvements"

    run_migrate
    [ "$status" -eq 1 ]
    [[ "$output" == *"rdd-workflow"* ]] || [[ "$output" == *"源仓库"* ]] || [[ "$output" == *"source"* ]]
    # Improvements dir must be untouched
    [ -f "$PROJECT_ROOT/improvements/foo.md" ]
}

@test "migrate-improvements: no-op when improvements/ missing" {
    rm -rf "$PROJECT_ROOT/improvements"

    run_migrate
    [ "$status" -eq 0 ]
    [[ "$output" == *"improvements/"* ]] || [[ "$output" == *"无需迁移"* ]]
}

@test "migrate-improvements: refuses when .rddf/improvements/ already exists" {
    mkdir -p "$PROJECT_ROOT/.rddf/improvements"
    echo "# keep" > "$PROJECT_ROOT/.rddf/improvements/sentinel.md"

    run_migrate
    [ "$status" -eq 1 ]
    [[ "$output" == *"已存在"* ]] || [[ "$output" == *"exists"* ]]
    [ -f "$PROJECT_ROOT/.rddf/improvements/sentinel.md" ]
    [ -f "$PROJECT_ROOT/improvements/foo.md" ]
}

@test "migrate-improvements: --help prints usage and exits 0" {
    run_migrate --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"usage"* ]] || [[ "$output" == *"用法"* ]]
    [[ "$output" == *"improvements"* ]]
    # Help must not touch files
    [ -f "$PROJECT_ROOT/improvements/foo.md" ]
    [ ! -d "$PROJECT_ROOT/.rddf/improvements" ]
}

@test "migrate-improvements: --dry-run leaves filesystem unchanged" {
    run_migrate --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"[DRY-RUN]"* ]] || [[ "$output" == *"Dry-Run"* ]] || [[ "$output" == *"Dry"* ]]
    [ -f "$PROJECT_ROOT/improvements/foo.md" ]
    [ -f "$PROJECT_ROOT/improvements/bar.md" ]
    [ ! -d "$PROJECT_ROOT/.rddf/improvements" ]
}

@test "migrate-improvements: updates markdown links in proposal files" {
    run_migrate
    [ "$status" -eq 0 ]
    grep -q "\[foo\](.rddf/improvements/foo.md)" "$PROJECT_ROOT/proposal-approved.md"
    grep -q "\[bar\](.rddf/improvements/bar.md)" "$PROJECT_ROOT/proposal-approved.md"
    ! grep -q "](improvements/" "$PROJECT_ROOT/proposal-approved.md"
    grep -q "\[foo\](.rddf/improvements/foo.md)" "$PROJECT_ROOT/proposal-suggestions.md"
    ! grep -q "](improvements/" "$PROJECT_ROOT/proposal-suggestions.md"
}

@test "migrate-improvements: updates iteration.json path fields" {
    run_migrate
    [ "$status" -eq 0 ]
    local iter_json
    iter_json="$(cat "$PROJECT_ROOT/.rddf/state/iteration.json")"
    [[ "$iter_json" == *".rddf/improvements/foo.md"* ]]
    [[ "$iter_json" != *"improvements/foo.md"* ]] || [[ "$iter_json" == *".rddf/improvements/foo.md"* ]]
}

@test "migrate-improvements: preserves content of improvement files" {
    local original_foo original_bar
    original_foo="$(cat "$PROJECT_ROOT/improvements/foo.md")"
    original_bar="$(cat "$PROJECT_ROOT/improvements/bar.md")"

    run_migrate
    [ "$status" -eq 0 ]

    [ "$(cat "$PROJECT_ROOT/.rddf/improvements/foo.md")" = "$original_foo" ]
    [ "$(cat "$PROJECT_ROOT/.rddf/improvements/bar.md")" = "$original_bar" ]
}