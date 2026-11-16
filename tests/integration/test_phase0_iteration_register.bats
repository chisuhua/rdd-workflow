#!/usr/bin/env bats
# tests/integration/test_phase0_iteration_register.bats
#
# P0 approve must register the change in iteration.json: the archive-side sync
# (sync_iteration_after_archive / force_mark_archived) only UPDATES existing
# entries, so without a creation step every change was invisible to
# `rddf status` / `rddf feature` / deps until someone edited the JSON by hand.

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    mkdir -p .rddf/state openspec/changes .rddf/improvements
    ln -s "$REPO_ROOT/_lib" _lib
    # the change is only registered when the improvement draft exists (that is
    # the branch that actually creates openspec/changes/<name>/)
    cat > .rddf/improvements/demo.md <<'IMPROVEMENT'
---
name: demo
priority: P1
status: pending
---

# demo

## 架构依据
test fixture

## 范围
- In Scope: fixture

## Why
test fixture

## What Changes
test fixture

## Acceptance
- [ ] fixture acceptance item

## Capabilities
- MUST fixture

## Impact
none
IMPROVEMENT
    # a valid, empty iteration.json (via the store API so the schema is right)
    PROJECT_ROOT="$TEST_TMP" python3 - <<'PY'
import os, sys
root = os.environ["PROJECT_ROOT"]
sys.path.insert(0, os.environ.get("REPO_ROOT", "."))
from skills._lib.iteration import store
data = store.create_empty()
store.save(root, data)
PY
}

teardown() {
    cd /
    rm -rf "$TEST_TMP"
}

@test "phase0: approve registers the change in iteration.json" {
    run env PROJECT_ROOT="$TEST_TMP" REPO_ROOT="$REPO_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" demo --auto-approve
    [ "$status" -eq 0 ]
    run python3 -c "
import json, sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.iteration import store
d = store.load('$TEST_TMP')
c = next((x for x in d.get('changes', []) if x.get('name') == 'demo'), None)
assert c is not None, 'change not registered'
assert c.get('status') == 'proposed', c
print('registered')"
    [[ "$output" == *"registered"* ]]
}

@test "phase0: registering is idempotent and preserves existing fields" {
    PROJECT_ROOT="$TEST_TMP" python3 - <<'PY'
import os, sys
root = os.environ["PROJECT_ROOT"]
sys.path.insert(0, os.environ.get("REPO_ROOT", "."))
from skills._lib.iteration import store
d = store.load(root)
d = store.set_tasks_done(d, "demo", 3, 5)
d = store.set_status(d, "demo", "in_worktree")
store.save(root, d)
PY
    run env PROJECT_ROOT="$TEST_TMP" REPO_ROOT="$REPO_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" demo --auto-approve
    [ "$status" -eq 0 ]
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.iteration import store
d = store.load('$TEST_TMP')
entries = [x for x in d.get('changes', []) if x.get('name') == 'demo']
assert len(entries) == 1, entries
c = entries[0]
assert c.get('tasks_done') == 3, c
assert c.get('tasks_total') == 5, c
assert c.get('added_at'), c
print('idempotent')"
    [[ "$output" == *"idempotent"* ]]
}

@test "phase0: missing iteration.json warns, keeps exit 0 and creates no file" {
    rm -f "$TEST_TMP/.rddf/state/iteration.json"
    run env PROJECT_ROOT="$TEST_TMP" REPO_ROOT="$REPO_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" demo --auto-approve
    [ "$status" -eq 0 ]
    [[ "$output" == *"iteration.json"* ]]
    [ ! -f "$TEST_TMP/.rddf/state/iteration.json" ]
}

@test "phase0: dispatch-quick (choice=5) does not register a change" {
    # choice 5 dispatches to rdd-quick (no openspec change) — nothing to register
    run env PROJECT_ROOT="$TEST_TMP" REPO_ROOT="$REPO_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" demo --dispatch-quick
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.iteration import store
d = store.load('$TEST_TMP')
names = [x.get('name') for x in d.get('changes', [])]
assert 'demo' not in names, names
print('not registered')"
    [[ "$output" == *"not registered"* ]]
}

@test "phase0: a corrupt iteration.json is reported and left untouched" {
    printf '{"schema_version": 7, "changes": [' > "$TEST_TMP/.rddf/state/iteration.json"
    BEFORE=$(cat "$TEST_TMP/.rddf/state/iteration.json")
    run env PROJECT_ROOT="$TEST_TMP" REPO_ROOT="$REPO_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" demo --auto-approve
    [ "$status" -eq 0 ]
    [[ "$output" == *"invalid"* ]]
    [ "$(cat "$TEST_TMP/.rddf/state/iteration.json")" = "$BEFORE" ]
    [ -z "$(ls "$TEST_TMP/.rddf/state/" | grep -c 'corrupt' | grep -v '^0$')" ] || true
    run bash -c "ls '$TEST_TMP/.rddf/state/' | grep -c corrupt || true"
    [ "$output" = "0" ]
}

@test "phase0: a schema-invalid iteration.json is reported and left untouched" {
    printf '{"changes": [{"name": "demo"}]}\n' > "$TEST_TMP/.rddf/state/iteration.json"
    BEFORE=$(cat "$TEST_TMP/.rddf/state/iteration.json")
    run env PROJECT_ROOT="$TEST_TMP" REPO_ROOT="$REPO_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" demo --auto-approve
    [ "$status" -eq 0 ]
    [[ "$output" == *"invalid"* ]]
    [ "$(cat "$TEST_TMP/.rddf/state/iteration.json")" = "$BEFORE" ]
}

@test "phase0: re-approving does not downgrade an entry that is already under way" {
    PROJECT_ROOT="$TEST_TMP" python3 - <<'PY'
import os, sys
root = os.environ["PROJECT_ROOT"]
sys.path.insert(0, os.environ.get("REPO_ROOT", "."))
from skills._lib.iteration import store
d = store.load(root)
d = store.set_status(d, "demo", "in_worktree")
store.save(root, d)
PY
    run env PROJECT_ROOT="$TEST_TMP" REPO_ROOT="$REPO_ROOT" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" demo --auto-approve
    [ "$status" -eq 0 ]
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills._lib.iteration import store
d = store.load('$TEST_TMP')
c = next(x for x in d.get('changes', []) if x.get('name') == 'demo')
assert c.get('status') == 'in_worktree', c
print('not downgraded')"
    [[ "$output" == *"not downgraded"* ]]
}
