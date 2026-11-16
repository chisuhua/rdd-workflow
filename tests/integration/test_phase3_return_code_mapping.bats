#!/usr/bin/env bats
# tests/integration/test_phase3_return_code_mapping.bats
#
# Behavioural tests for P3's exit-code contract in worktree mode. The
# delegation maps archive_change's returns onto P3's own contract:
#
#   archive_change 0 (archived)            → phase3 0
#   archive_change 3 (gate refused)        → phase3 7
#   archive_change 1 (precondition failed) → phase3 3
#
# These are deliberately behavioural (the script is executed), not source-text
# assertions: under `set -euo pipefail` a bare failing call would abort the
# script before the mapping runs, which a grep-based test cannot see.

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    git init -q .
    git config user.email t@t.invalid
    git config user.name tester
    git commit -q --allow-empty -m init
    git branch -M main
    mkdir -p .rddf/state/builder openspec/changes/demo bin
    ln -s "$REPO_ROOT/_lib" _lib
    # .rddf/state/ is runtime-only in the real repo (gitignored). Without it,
    # the verdict cache written into the worktree would count as an untracked
    # file and `git worktree remove` would refuse to remove the worktree.
    printf '.rddf/state/\n' > .gitignore
    printf '# demo\n\n## Acceptance\n\n- [ ] AC one\n' > openspec/changes/demo/proposal.md
    printf '## Tasks\n\n- [x] task one\n' > openspec/changes/demo/tasks.md
    printf '{"execution_mode_decision": {"mode": "worktree"}}\n' > .rddf/state/builder/demo.json
    printf '#!/bin/sh\necho "OPENSPEC_ARCHIVE_CALLED $PWD" >> "$OPENSPEC_CALL_LOG"\nexit 0\n' > bin/openspec
    chmod +x bin/openspec
    git add -A
    git commit -q -m "fixture change"
    export OPENSPEC_CALL_LOG="$TEST_TMP/calls.log"
}

teardown() {
    cd /
    rm -rf "$TEST_TMP"
}

_add_worktree_commit() {
    git worktree add -q .rddf/wt/demo -b openspec/demo
    (
        cd .rddf/wt/demo
        echo "feature" > feature.txt
        git add feature.txt
        git commit -q -m "feature work"
    )
}

_write_cache_in() {   # $1 = root whose HEAD the cache is stamped at
    mkdir -p "$1/.rddf/state/verifier"
    SHA="$(git -C "$1" rev-parse HEAD)" \
    CACHE="$1/.rddf/state/verifier/.ac-verdict-demo.json" python3 - <<'PY'
import json, os
json.dump({
    "schema_version": 2, "version": 2, "change": "demo",
    "codebase_commit": os.environ["SHA"],
    "verdict": [{"ac_id": "AC-1", "description": "a", "status": "pass",
                 "confidence": 0.95, "evidence": [], "reasoning": "fixture"}],
    "verification_state": "passed", "failed_acs": [],
}, open(os.environ["CACHE"], "w"))
PY
}

_phase3() {
    run env PROJECT_ROOT="$TEST_TMP" PATH="$TEST_TMP/bin:$PATH" \
        OPENSPEC_CALL_LOG="$TEST_TMP/calls.log" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
}

@test "gate refusal (no verdict cache) → phase3 exits 7" {
    _add_worktree_commit
    _phase3
    [ "$status" -eq 7 ]
    [[ "$output" == *"no valid verdict cache"* ]]
}

@test "precondition failure (branch without new commits) → phase3 exits 3" {
    git worktree add -q .rddf/wt/demo -b openspec/demo
    _phase3
    [ "$status" -eq 3 ]
}

@test "success → phase3 exits 0 and the worktree branch is merged into the default branch" {
    _add_worktree_commit
    # tracked openspec ⇒ the gate root is the worktree ⇒ stamp the cache there
    _write_cache_in "$TEST_TMP/.rddf/wt/demo"
    _phase3
    [ "$status" -eq 0 ]
    run git -C "$TEST_TMP" log --oneline main
    [[ "$output" == *"feature work"* ]]
    [ ! -d "$TEST_TMP/.rddf/wt/demo" ]
}
