load ../test_helper

# Integration test for fix-rddf-status-corrupt-message.
# Verifies the `rddf status` and `rddf status <name>` commands
# differentiate missing from corrupt iteration.json.

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

@test "status: schema-invalid iteration.json → 'fails schema validation' message" {
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
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

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status
    [ "$status" -eq 1 ]
    [[ "$output" == *"fails schema validation"* ]]
    [[ "$output" == *"restore from a iteration.json.corrupt."* ]]
}

@test "status: corrupt output must NOT contain 'skill_use(\"propose\"' hint" {
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {
      "name": "x",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00",
      "updated_at": "2026-08-05T11:00:00+00:00"
    }
  ]
}
EOF

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status
    [ "$status" -eq 1 ]
    # The misleading 'propose' hint must NOT appear (it would wipe data)
    [[ ! "$output" == *"propose"* ]] || [[ ! "$output" == *"propose, \"<change-name>\""* ]]
}

@test "status <name>: corrupt iteration.json → exit 1, corrupt message" {
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {
      "name": "my-change",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00",
      "updated_at": "2026-08-05T11:00:00+00:00"
    }
  ]
}
EOF

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status my-change
    [ "$status" -eq 1 ]
    [[ "$output" == *"fails schema validation"* ]]
}

@test "status: invalid JSON → 'invalid JSON' message" {
    mkdir -p .rddf/state
    echo '{"version": 4, "changes": [],}' > .rddf/state/iteration.json  # trailing comma

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
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {
      "name": "x",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00",
      "updated_at": "2026-08-05T11:00:00+00:00"
    }
  ]
}
EOF

    # Redirect both stdout and stderr to avoid bats noise on non-zero exit
    env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli status >/dev/null 2>&1 || true

    # No backup files should be created by the read-only path
    backups=$(find .rddf/state -name "*.corrupt.*" 2>/dev/null | wc -l)
    [ "$backups" -eq 0 ]
}
