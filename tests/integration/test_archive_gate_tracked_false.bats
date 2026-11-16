#!/usr/bin/env bats
# tests/integration/test_archive_gate_tracked_false.bats
#
# archive_change must run archive_gate_check on the openspec_tracked=false
# branch too (per fix-p3-verifier-gate). Historically that branch returned 0
# before reaching the gate call, so a project with an untracked openspec/
# never got an AC gate at all.
#
# The tasks_root handed to the gate is $main_root, not $wt_path: this branch
# exists precisely because openspec/ is untracked, and a fresh `git worktree`
# carries neither openspec/ nor the gitignored .rddf/state/ (verified).

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    git init -q .
    git config user.email t@t.invalid
    git config user.name tester
    git commit -q --allow-empty -m "init"
    git branch -M main
    mkdir -p .rddf openspec/changes/demo _lib
    # archive_change only reads git.openspec_tracked when project_config.sh
    # is present in the project root.
    cp "$REPO_ROOT/_lib/project_config.sh" _lib/
    printf 'git:\n  openspec_tracked: false\n' > .rddf/project.yaml
    printf '# proposal\n\n## Acceptance\n\n- [ ] AC one\n' > openspec/changes/demo/proposal.md
    printf '## Tasks\n\n- [x] task one\n' > openspec/changes/demo/tasks.md
    git add -A
    git commit -q -m "fixture change"
    git worktree add -q .rddf/wt/demo -b openspec/demo
}

teardown() {
    cd /
    git -C "$TEST_TMP" worktree remove --force "$TEST_TMP/.rddf/wt/demo" 2>/dev/null || true
    rm -rf "$TEST_TMP"
}

@test "tracked=false: archive_change refuses when no verdict cache exists" {
    run bash -c "cd '$TEST_TMP' && source '$REPO_ROOT/_lib/archive.sh' && archive_change demo"
    [ "$status" -ne 0 ]
}

@test "tracked=false: rejection comes from the AC gate, not worktree lookup" {
    run bash -c "cd '$TEST_TMP' && source '$REPO_ROOT/_lib/archive.sh' && archive_change demo"
    [[ "$output" != *"找不到 worktree"* ]]
    [[ "$output" == *"no valid verdict cache"* ]]
    [ "$status" -eq 3 ]
}

@test "tracked=false: gate passes through to openspec archive when cache is valid" {
    mkdir -p "$TEST_TMP/.rddf/state/verifier"
    sha=$(git -C "$TEST_TMP" rev-parse main)
    CACHE="$TEST_TMP/.rddf/state/verifier/.ac-verdict-demo.json" SHA="$sha" python3 - <<'PY'
import json, os
json.dump({
    "schema_version": 2, "version": 2, "change": "demo",
    "codebase_commit": os.environ["SHA"],
    "verdict": [{"ac_id": "AC-1", "description": "d", "status": "pass",
                 "confidence": 0.95, "evidence": [], "reasoning": "fixture"}],
    "verification_state": "passed", "failed_acs": [],
}, open(os.environ["CACHE"], "w"))
PY
    mkdir -p "$TEST_TMP/bin"
    printf '#!/bin/sh\nexit 0\n' > "$TEST_TMP/bin/openspec"
    chmod +x "$TEST_TMP/bin/openspec"
    run env PATH="$TEST_TMP/bin:$PATH" SKIP_VERIFIER_CONTRACT=yes bash -c \
        "cd '$TEST_TMP' && source '$REPO_ROOT/_lib/archive.sh' && archive_change demo"
    [ "$status" -eq 0 ]
}

@test "tracked=true: gate behaviour unchanged (still reached at step 2.5)" {
    # Sanity check that the false-branch change did not alter the tracked path.
    grep -q 'archive_gate_check "\$name" "\$wt_path"' "$REPO_ROOT/_lib/archive.sh"
}
