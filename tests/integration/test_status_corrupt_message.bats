load ../test_helper

# `rddf status` no longer reads `.rddf/state/iteration.json`
# (change `rddf-status-based-on-improvements`).
#
# The former contract verified how status *reported* missing/corrupt/v4
# iteration.json. That whole surface is gone: iteration.json is procedural
# state, not the truth source for what status reports. These tests pin the
# replacement contract:
#
#   1. status works regardless of iteration.json's state (missing /
#      invalid JSON / schema-invalid / old version)
#   2. `status <name>` derives its detail from disk
#   3. the command remains read-only (it must not touch iteration.json)

setup() {
    BATS_TEST_TMPDIR="$(mktemp -d)"
    cd "$BATS_TEST_TMPDIR"

    # Init a git repo so __main__.py::resolve_project_root() works
    # (otherwise it prints "not a rdd-workflow project" and exits 0).
    git init -q
    git config user.email "test@example.com"
    git config user.name "test"
    git commit --allow-empty -q -m "init"

    export RDDF_PROJECT_ROOT="$BATS_TEST_TMPDIR"

    # One improvement proposal (the truth source status reports on).
    mkdir -p .rddf/improvements
    cat > .rddf/improvements/sample-proposal.md <<'EOF'
---
优先级: P1
状态: 待讨论
阶段: phase-2
---

# sample-proposal
EOF

    # One active change on disk.
    mkdir -p openspec/changes/disk-change
    cat > openspec/changes/disk-change/tasks.md <<'EOF'
- [x] first task
- [ ] second task
EOF
}

teardown() {
    [ -n "$BATS_TEST_TMPDIR" ] && rm -rf "$BATS_TEST_TMPDIR"
}

_write_iteration() {
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<EOF
$1
EOF
}

@test "status: works with no iteration.json at all" {
    [ ! -e .rddf/state/iteration.json ]
    run rddf status
    [ "$status" -eq 0 ]
    [[ "$output" == *"Improvement proposals"* ]]
    [[ "$output" == *"sample-proposal"* ]]
    [[ "$output" == *"disk-change"* ]]
    [[ "$output" != *"not found"* ]]
}

@test "status: invalid JSON iteration.json does not break status" {
    _write_iteration '{not valid json'
    run rddf status
    [ "$status" -eq 0 ]
    [[ "$output" == *"sample-proposal"* ]]
    [[ "$output" != *"invalid JSON"* ]]
    [[ "$output" != *"fails schema validation"* ]]
}

@test "status: schema-invalid iteration.json does not break status" {
    _write_iteration '{"version": 5, "illegal_root_field": "not allowed"}'
    run rddf status
    [ "$status" -eq 0 ]
    [[ "$output" == *"sample-proposal"* ]]
    [[ "$output" != *"fails schema validation"* ]]
}

@test "status: old-version iteration.json is irrelevant to status" {
    _write_iteration '{"version": 4, "updated_at": "2026-08-01T00:00:00+00:00", "current_phase": "default", "changes": []}'
    run rddf status
    [ "$status" -eq 0 ]
    [[ "$output" == *"sample-proposal"* ]]
}

@test "status <name>: corrupt iteration.json still yields the disk-derived detail" {
    _write_iteration '{not valid json'
    run rddf status disk-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"Change: disk-change"* ]]
    [[ "$output" == *"Tasks: 1/2"* ]]
    [[ "$output" != *"fails schema validation"* ]]
}

@test "status <name>: unknown change exits 1 even when iteration.json lists it" {
    _write_iteration '{"version": 5, "updated_at": "2026-08-01T00:00:00+00:00", "current_phase": "default", "changes": [{"name": "ghost", "status": "proposed", "added_at": "2026-08-01T00:00:00+00:00"}]}'
    run rddf status ghost
    [ "$status" -eq 1 ]
    [[ "$output" == *"not found"* ]]
}

@test "status: read-only contract — iteration.json is not touched" {
    _write_iteration '{not valid json'
    before=$(sha256sum .rddf/state/iteration.json | awk '{print $1}')
    before_listing=$(ls .rddf/state/)
    run rddf status
    [ "$status" -eq 0 ]
    after=$(sha256sum .rddf/state/iteration.json | awk '{print $1}')
    after_listing=$(ls .rddf/state/)
    [ "$before" = "$after" ]
    [ "$before_listing" = "$after_listing" ]
    # No .corrupt.<ts> backup may be created by a read.
    run bash -c 'ls .rddf/state/*.corrupt.* 2>/dev/null | wc -l'
    [ "$output" -eq 0 ]
}

@test "status --iteration is rejected (Mode E removed)" {
    run rddf status --iteration
    [ "$status" -eq 2 ]
    [[ "$output" == *"unknown flag"* ]]
}

@test "status: improvement collector surfaces unreadable files" {
    # A file whose front-matter cannot be parsed must not blank the table.
    printf 'not a front-matter at all\n' > .rddf/improvements/broken.md
    run rddf status
    [ "$status" -eq 0 ]
    [[ "$output" == *"sample-proposal"* ]]
}
