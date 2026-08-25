#!/usr/bin/env bats
#
# tests/integration/test_iteration_deps_sync_no_phantom.bats
#
# Regression tests for set_deps_info no-phantom-create (Bug A).
# Bug A: deps.md Step 6 sync_iteration_from_analysis calls set_deps_info
#        for every change in deps-analysis.json. If the change name is
#        not in iteration.json, set_deps_info auto-creates an entry with
#        status="proposed". When deps-analysis.json contains names from
#        proposal-approved.md that were never actually proposed via
#        OpenSpec CLI, this creates phantom entries that diverge from
#        disk state.
#
# Fix: set_deps_info must NOT create new entries. Caller must run
#      propose.md first to ensure entry exists. If entry doesn't exist,
#      set_deps_info logs a warning and returns unchanged.
#
# These tests verify the new "skip-on-missing" behavior.

# test_helper.bash is auto-loaded by bats; do not `load test_helper`.

load ../test_helper

setup() {
    TEST_PROJECT_ROOT="$(mktemp -d)"
    cd "$TEST_PROJECT_ROOT" || exit 1
    git init -q .
    git config user.email "test@example.com"
    git config user.name "test"
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'EOF'
{"version": 6, "updated_at": "2026-08-24T00:00:00+00:00", "current_phase": "default", "changes": []}
EOF
}

teardown() {
    cd /
    rm -rf "$TEST_PROJECT_ROOT"
}

@test "set_deps_info does NOT create entry for missing change (Bug A)" {
    # Empty iteration.json; deps analysis surfaces a name
    SKILLS_PARENT="$REPO_ROOT" \
    MAIN_ROOT="$TEST_PROJECT_ROOT" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib import iteration as it_mod

# Initial state: empty iteration.json
data = it_mod.load(os.environ['MAIN_ROOT'])
assert data['changes'] == [], f'iteration.json should start empty, got {data}'

# Call set_deps_info for a brand-new name
data = it_mod.set_deps_info(data, name='phantom-candidate', blocker=None, parallel_group=0, conflicts=[])
it_mod.save(os.environ['MAIN_ROOT'], data)

# Reload and check — should still be empty (Bug A fix)
data2 = it_mod.load(os.environ['MAIN_ROOT'])
names = [c['name'] for c in data2['changes']]
assert 'phantom-candidate' not in names, f'set_deps_info created phantom entry: {data2[\"changes\"]}'
"
}

@test "set_deps_info updates EXISTING entry's deps metadata (preserve behavior)" {
    SKILLS_PARENT="$REPO_ROOT" \
    MAIN_ROOT="$TEST_PROJECT_ROOT" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib import iteration as it_mod

# Pre-populate with an entry (as if propose.md already ran)
data = it_mod.add_or_update_change(it_mod.create_empty(), name='real-candidate', status='proposed', phase='v2.2', category='core')
it_mod.save(os.environ['MAIN_ROOT'], data)

# Call set_deps_info for that name
data = it_mod.load(os.environ['MAIN_ROOT'])
data = it_mod.set_deps_info(data, name='real-candidate', blocker='dep-1', parallel_group=1, conflicts=['dep-2'])
it_mod.save(os.environ['MAIN_ROOT'], data)

# Verify deps fields updated, status preserved
data2 = it_mod.load(os.environ['MAIN_ROOT'])
entry = next(c for c in data2['changes'] if c['name'] == 'real-candidate')
assert entry['status'] == 'proposed', f'status should be preserved, got {entry[\"status\"]}'
assert entry['blocker'] == 'dep-1', f'blocker should be updated, got {entry[\"blocker\"]}'
assert entry['parallel_group'] == 1
assert 'last_deps_at' in entry, 'last_deps_at should be set'
assert 'phase' in entry, 'phase should be preserved (was set by add_or_update_change)'
"
}

@test "deps sync_iteration_from_analysis skips names not in iteration.json (Bug A fix e2e)" {
    # Write a deps-analysis.json with a name that has no corresponding change
    mkdir -p .rddf/state
    cat > .rddf/state/deps-analysis.json <<'EOF'
{
  "version": 1,
  "updated_at": "2026-08-24T09:27:22Z",
  "fallback": true,
  "changes": {
    "ghost-candidate": {
      "name": "ghost-candidate",
      "phase": null,
      "category": null,
      "status": "ready",
      "blocker": null,
      "blocks": [],
      "parallel_group": 0,
      "conflicts": [],
      "confidence": "high"
    }
  }
}
EOF

    SKILLS_PARENT="$REPO_ROOT" \
    PROJECT_ROOT="$TEST_PROJECT_ROOT" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib import iteration as it_mod
from skills.deps.scripts import deps_output as do_mod

# Empty iteration.json
data = it_mod.load(os.environ['PROJECT_ROOT'])
assert data['changes'] == []

# Run sync
count = do_mod.sync_iteration_from_analysis(os.environ['PROJECT_ROOT'], it_mod)
print(f'sync count: {count}')  # should be 0 if Bug A is fixed

# Verify no phantom entry created
data2 = it_mod.load(os.environ['PROJECT_ROOT'])
names = [c['name'] for c in data2['changes']]
assert 'ghost-candidate' not in names, f'sync created phantom entry: {data2[\"changes\"]}'
assert count == 0, f'sync should skip missing entries; count={count}'
"
}