load ../test_helper

# Integration test for rddf-iteration-strict-schema.
# Verifies the `rddf iteration lint` and `rddf iteration allowed-fields`
# subcommands provide write-side pre-check tools (complement to the
# read-side fix in fix-rddf-status-corrupt-message).

setup() {
    BATS_TEST_TMPDIR="$(mktemp -d)"
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "test@example.com"
    git config user.name "test"
    git commit --allow-empty -q -m "init"
    export RDDF_PROJECT_ROOT="$BATS_TEST_TMPDIR"
}

teardown() {
    [ -n "$BATS_TEST_TMPDIR" ] && rm -rf "$BATS_TEST_TMPDIR"
}

# --- rddf iteration lint ---

@test "iteration lint: valid iteration.json → exit 0, 'no issues' message" {
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
      "added_at": "2026-08-01T00:00:00+00:00"
    }
  ]
}
EOF

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli iteration lint .
    [ "$status" -eq 0 ]
    [[ "$output" == *"no issues"* ]]
}

@test "iteration lint: schema-invalid (extra field) → exit 1, lists invalid + allowed" {
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
      "archive_commit": "BAD_FIELD"
    }
  ]
}
EOF

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli iteration lint .
    [ "$status" -eq 1 ]
    [[ "$output" == *"archive_commit"* ]]
    [[ "$output" == *"allowed"* ]]
    [[ "$output" == *"name"* ]]
    [[ "$output" == *"status"* ]]
}

@test "iteration lint: no backup files written (read-only)" {
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
      "bogus": "BAD"
    }
  ]
}
EOF

    env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli iteration lint . >/dev/null 2>&1 || true
    backups=$(find .rddf/state -name "*.corrupt.*" 2>/dev/null | wc -l)
    [ "$backups" -eq 0 ]
}

# --- rddf iteration allowed-fields ---

@test "iteration allowed-fields: prints per-change field names" {
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": []
}
EOF

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli iteration allowed-fields .
    [ "$status" -eq 0 ]
    [[ "$output" == *"name"* ]]
    [[ "$output" == *"status"* ]]
    [[ "$output" == *"added_at"* ]]
    [[ "$output" == *"archived_at"* ]]
    [[ "$output" == *"tasks_done"* ]]
    [[ "$output" == *"plan_path"* ]]
}

@test "iteration allowed-fields: not a rdd-workflow project → friendly message" {
    # No .rddf/state/ directory
    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli iteration allowed-fields .
    [ "$status" -eq 0 ]
    [[ "$output" == *"not a rdd-workflow"* ]]
}

# --- _backup_corrupt_file .reason.txt sidecar ---

@test "_backup_corrupt_file: writes .reason.txt sidecar alongside .corrupt.<ts>" {
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
    # store.load() looks for .rddf/state/iteration.json under the given
    # project_root. Use pwd (the current test dir is already the root).
    PROJECT_ROOT_FOR_LOAD="$(pwd)"
    python3 -c "
import sys, os
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.iteration import store
result = store.load('$PROJECT_ROOT_FOR_LOAD')
print('result keys:', list(result.get('changes', []))[:1])
"
    # Check the backup files were created. The backup name strips
    # the .json extension: iteration.corrupt.<ts> (not iteration.json.corrupt.<ts>).
    corrupt_files=$(ls .rddf/state/iteration.corrupt.* 2>/dev/null | grep -v reason.txt | wc -l)
    reason_files=$(ls .rddf/state/iteration.corrupt.*.reason.txt 2>/dev/null | wc -l)
    [ "$corrupt_files" -eq 1 ]
    [ "$reason_files" -eq 1 ]
}
