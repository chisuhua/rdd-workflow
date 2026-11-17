#!/usr/bin/env bats
# tests/integration/test_phase3_archives_in_main_repo.bats
#
# The F-7 fix: when openspec/ is untracked (git.openspec_tracked=false), the
# worktree's openspec/ is a throwaway COPY — archiving inside the worktree
# wrote the record into that copy, and the worktree cleanup then deleted it.
# P3 now delegates to archive_change, which archives in the MAIN repo (the
# authoritative openspec/).
#
# The stub records its cwd, so the assertion is about WHERE the archive ran,
# not about how many times it ran.

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    git init -q .
    git config user.email t@t.invalid
    git config user.name tester
    git commit -q --allow-empty -m init
    git branch -M main
    mkdir -p .rddf/state/builder .rddf/state/verifier openspec/changes/demo _lib bin
    cp "$REPO_ROOT/_lib/project_config.sh" _lib/
    printf 'git:\n  openspec_tracked: false\n' > .rddf/project.yaml
    printf '# demo\n\n## Acceptance\n\n- [ ] AC one\n' > openspec/changes/demo/proposal.md
    printf '## Tasks\n\n- [x] task one\n' > openspec/changes/demo/tasks.md
    printf '{"execution_mode_decision": {"mode": "worktree"}}\n' > .rddf/state/builder/demo.json
    git add -A
    git commit -q -m "fixture change"
    git worktree add -q .rddf/wt/demo -b openspec/demo
    (
        cd .rddf/wt/demo
        echo "feature" > feature.txt
        git add feature.txt
        git commit -q -m "feature work"
    )
    # The branch is merged before archiving (the workflow requirement: the
    # code must reach the default branch BEFORE the verdict cache is stamped).
    git merge -q --no-ff openspec/demo -m "merge: feature work"
    # The cache is stamped with the IMPLEMENTATION BRANCH TIP — the anchor the
    # gate compares against (openspec/specs/verifier-lifecycle/spec.md). It is
    # root-independent, so the false branch (which switches the main repo to
    # the default branch before running the gate) still sees a fresh cache.
    SHA="$(git rev-parse openspec/demo)" CACHE="$TEST_TMP/.rddf/state/verifier/.ac-verdict-demo.json" python3 - <<'PY'
import json, os
json.dump({
    "schema_version": 2, "version": 2, "change": "demo",
    "codebase_commit": os.environ["SHA"],
    "verdict": [{"ac_id": "AC-1", "description": "a", "status": "pass",
                 "confidence": 0.95, "evidence": [], "reasoning": "fixture"}],
    "verification_state": "passed", "failed_acs": [],
}, open(os.environ["CACHE"], "w"))
PY
    cat > bin/openspec <<'SH'
#!/usr/bin/env bash
echo "CWD=$(pwd)" >> "$OPENSPEC_CALL_LOG"
exit 0
SH
    chmod +x bin/openspec
}

teardown() {
    cd /
    rm -rf "$TEST_TMP"
}

@test "phase3: the archive runs in the MAIN repo, not in the worktree" {
    run env PROJECT_ROOT="$TEST_TMP" PATH="$TEST_TMP/bin:$PATH" \
        OPENSPEC_CALL_LOG="$TEST_TMP/calls.log" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/calls.log" ]
    grep -q "CWD=$TEST_TMP" "$TEST_TMP/calls.log"
    ! grep -q "CWD=$TEST_TMP/.rddf/wt/demo" "$TEST_TMP/calls.log"
}

@test "phase3: the worktree is cleaned up after the delegated archive" {
    run env PROJECT_ROOT="$TEST_TMP" PATH="$TEST_TMP/bin:$PATH" \
        OPENSPEC_CALL_LOG="$TEST_TMP/calls.log" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
    [ "$status" -eq 0 ]
    [ ! -d "$TEST_TMP/.rddf/wt/demo" ]
}

@test "phase3: the builder handoff records archive_status=archived" {
    run env PROJECT_ROOT="$TEST_TMP" PATH="$TEST_TMP/bin:$PATH" \
        OPENSPEC_CALL_LOG="$TEST_TMP/calls.log" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
    [ "$status" -eq 0 ]
    run grep -o '"archive_status": *"archived"' "$TEST_TMP/.rddf/state/builder/demo.json"
    [ -n "$output" ]
}
