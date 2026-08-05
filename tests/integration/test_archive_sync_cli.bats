load ../test_helper

# Integration test for rddf archive-sync CLI subcommand.
# Tests the data-reconcile tool that repairs iteration.json drift
# after bare git mv + openspec archive + git commit (the path the
# post-commit hook covers; archive-sync is the manual one-shot for
# historical drift like the HydraForge 7 + UsrLinuxEmu 5 stale
# entries from the proposal).

setup() {
    BATS_TEST_TMPDIR="$(mktemp -d)"
    export RDDF_PROJECT_ROOT="$BATS_TEST_TMPDIR"

    # Minimal project layout
    mkdir -p "$BATS_TEST_TMPDIR/openspec/changes"
    mkdir -p "$BATS_TEST_TMPDIR/.rddf/state"

    # iteration.json with one proposed change
    cat > "$BATS_TEST_TMPDIR/.rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {
      "name": "my-change",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00"
    }
  ]
}
EOF

    # Create an archive dir for my-change (simulates the post-archive
    # state that needs reconciliation)
    mkdir -p "$BATS_TEST_TMPDIR/openspec/changes/archive/2026-08-05-my-change"
}

teardown() {
    [ -n "$BATS_TEST_TMPDIR" ] && rm -rf "$BATS_TEST_TMPDIR"
}

@test "archive-sync: single name → updates iteration.json" {
    cd "$BATS_TEST_TMPDIR"
    PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli archive-sync my-change

    status=$(python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/.rddf/state/iteration.json'))
c = next(c for c in d['changes'] if c['name'] == 'my-change')
print(c.get('status', ''))
")
    [ "$status" = "archived" ]
}

@test "archive-sync: missing change name → returns warning, exit 1" {
    cd "$BATS_TEST_TMPDIR"
    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli archive-sync nonexistent-change
    [ "$status" -eq 1 ]
    [[ "$output" == *"nonexistent-change"* ]]
}

@test "archive-sync: no args → exit 2 (invalid usage)" {
    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli archive-sync
    [ "$status" -eq 2 ]
    [[ "$output" == *"no change names"* ]]
}

@test "archive-sync: --all finds drift candidates" {
    cd "$BATS_TEST_TMPDIR"
    # Add a second drift candidate (archive dir exists, active dir missing)
    mkdir -p "openspec/changes/archive/2026-08-05-drift-2"

    cat > ".rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {
      "name": "my-change",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00"
    },
    {
      "name": "drift-2",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00"
    }
  ]
}
EOF

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli archive-sync --all
    [ "$status" -eq 0 ]
    [[ "$output" == *"my-change"* ]]
    [[ "$output" == *"drift-2"* ]]
    [[ "$output" == *"2 change(s) reconciled"* ]]
}

@test "archive-sync: --all with no drift candidates → exit 0, no-op" {
    cd "$BATS_TEST_TMPDIR"
    # Remove the archive dir so there are no candidates
    rm -rf "openspec/changes/archive"

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli archive-sync --all
    [ "$status" -eq 0 ]
    [[ "$output" == *"no drift"* ]]
}

@test "archive-sync: multiple names → all reconciled" {
    cd "$BATS_TEST_TMPDIR"
    # Add a second archive dir
    mkdir -p "openspec/changes/archive/2026-08-05-other-change"
    cat > ".rddf/state/iteration.json" <<'EOF'
{
  "version": 4,
  "updated_at": "2026-08-01T00:00:00+00:00",
  "current_phase": "default",
  "changes": [
    {
      "name": "my-change",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00"
    },
    {
      "name": "other-change",
      "status": "proposed",
      "added_at": "2026-08-01T00:00:00+00:00"
    }
  ]
}
EOF

    run env PYTHONPATH="$REPO_ROOT" python3 -m skills._lib.cli archive-sync my-change other-change
    [ "$status" -eq 0 ]

    python3 -c "
import json
d = json.load(open('$BATS_TEST_TMPDIR/.rddf/state/iteration.json'))
for name in ['my-change', 'other-change']:
    c = next(c for c in d['changes'] if c['name'] == name)
    assert c.get('status') == 'archived', f'{name} not archived: {c}'
print('OK')
"
}
