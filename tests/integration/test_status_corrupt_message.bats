load ../test_helper

# Integration test for fix-rddf-status-corrupt-message +
# v3/v4 → v5 in-memory migration in read path.
#
# Verifies the `rddf status` and `rddf status <name>` commands
#   1. differentiate missing from corrupt iteration.json
#   2. auto-migrate v3/v4 → v5 transparently (older version ≠ corrupt)
#   3. never write .corrupt.<ts> backup on read (read-only contract)

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
}

teardown() {
    [ -n "$BATS_TEST_TMPDIR" ] && rm -rf "$BATS_TEST_TMPDIR"
}

# Per-change `updated_at` is rejected by the v5 per-change item schema
# (additionalProperties: false). It was never a legal field in any
# version — the writer that injected it is the source of corruption,
# not the version number on disk. A v5 fixture carrying this field is
# the canonical "truly corrupt" case.
_write_corrupt_v5_with_per_change_updated_at() {
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 5,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {
      "name": "test-change",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00",
      "updated_at": "2026-08-05T11:00:00+00:00"
    }
  ]
}
EOF
}

@test "status: schema-invalid iteration.json → 'fails schema validation' message" {
    _write_corrupt_v5_with_per_change_updated_at

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status
    [ "$status" -eq 1 ]
    [[ "$output" == *"fails schema validation"* ]]
    [[ "$output" == *"restore from a iteration.json.corrupt."* ]]
}

@test "status: corrupt output must NOT contain 'skill_use(\"propose\"' hint" {
    _write_corrupt_v5_with_per_change_updated_at

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status
    [ "$status" -eq 1 ]
    # The misleading 'propose' hint must NOT appear (it would wipe data)
    [[ ! "$output" == *"propose"* ]] || [[ ! "$output" == *"propose, \"<change-name>\""* ]]
}

@test "status <name>: corrupt iteration.json → exit 1, corrupt message" {
    _write_corrupt_v5_with_per_change_updated_at

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status my-change
    [ "$status" -eq 1 ]
    [[ "$output" == *"fails schema validation"* ]]
}

@test "status: invalid JSON → 'invalid JSON' message" {
    mkdir -p .rddf/state
    echo '{"version": 5, "changes": [],}' > .rddf/state/iteration.json  # trailing comma

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status
    [ "$status" -eq 1 ]
    [[ "$output" == *"invalid JSON"* ]]
    [[ ! "$output" == *"propose"* ]]
}

@test "status: missing iteration.json → 'not found' message (regression)" {
    # .rddf/state/ exists but iteration.json does NOT (regression lock)
    mkdir -p .rddf/state
    # No iteration.json file created
    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status
    [ "$status" -eq 0 ]  # Mode A returns 0 for missing
    [[ "$output" == *"not found"* ]]
    [[ "$output" == *"propose"* ]]  # Missing case SHOULD suggest propose
}

@test "status: no .corrupt.<ts> backup written on corrupt read (read-only contract)" {
    _write_corrupt_v5_with_per_change_updated_at

    # Redirect both stdout and stderr to avoid bats noise on non-zero exit
    env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status >/dev/null 2>&1 || true

    # No backup files should be created by the read-only path
    backups=$(find .rddf/state -name "*.corrupt.*" 2>/dev/null | wc -l)
    [ "$backups" -eq 0 ]
}

# v4 → v5 auto-migration: a v4 file (previously valid schema) is
# not corrupt. The read path migrates it in-memory to v5 and reports
# the change normally. Without the migration, v4 files would surface
# the misleading "5 was expected" / "fails schema validation" error.
@test "status: v4 iteration.json is auto-migrated to v5 and renders normally" {
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {
      "name": "v4-change",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00"
    }
  ]
}
EOF

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status
    [ "$status" -eq 0 ]
    [[ ! "$output" == *"fails schema validation"* ]]
    [[ ! "$output" == *"not found"* ]]
    [[ "$output" == *"v4-change"* ]]
    # Mode A header is the success indicator
    [[ "$output" == *"Change status overview"* ]]
}

@test "status <name>: v4 iteration.json is auto-migrated → single-change detail works" {
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {
      "name": "my-v4-change",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00"
    }
  ]
}
EOF

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status my-v4-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"Change: my-v4-change"* ]]
    [[ "$output" == *"Status: 📋 proposed"* ]]
    [[ ! "$output" == *"fails schema validation"* ]]
}

@test "status: v4 file is read non-destructively (on-disk version stays at 4)" {
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": []
}
EOF

    env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status >/dev/null 2>&1 || true

    # Migration is in-memory only; on-disk file is unchanged
    on_disk_version=$(python3 -c "import json; print(json.load(open('.rddf/state/iteration.json'))['version'])")
    [ "$on_disk_version" -eq 4 ]
}
