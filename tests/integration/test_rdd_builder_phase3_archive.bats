#!/usr/bin/env bats
# tests/integration/test_rdd_builder_phase3_archive.bats
#
# P3 archive gate (per fix-p3-verifier-gate). P3 must not produce a verdict of
# its own: it checks the verdict cache written by the agent (rdd-verifier skill,
# ADR-0045) through _lib/archive.sh::archive_gate_check.
#
# States covered: cache complete+sha-match / cache missing / cache stale /
# bypass without reason / bypass with reason / worktree mode without worktree.

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    git init -q .
    git config user.email t@t.invalid
    git config user.name tester
    mkdir -p .rddf/state/builder openspec/changes/demo bin
    ln -s "$REPO_ROOT/_lib" _lib
    printf '# demo\n\n## Acceptance\n\n- [ ] AC one\n- [ ] AC two\n' \
        > openspec/changes/demo/proposal.md
    printf '## Tasks\n\n- [x] task one\n' > openspec/changes/demo/tasks.md
    # lightweight mode → no worktree needed
    printf '{"execution_mode_decision": {"mode": "lightweight"}}\n' \
        > .rddf/state/builder/demo.json
    printf '#!/bin/sh\nexit 0\n' > bin/openspec
    chmod +x bin/openspec
    git add -A
    git commit -q -m fixture
}

teardown() {
    cd /
    rm -rf "$TEST_TMP"
}

_write_cache() {  # $1 = codebase_commit ; $2 = pass|fail
    mkdir -p "$TEST_TMP/.rddf/state/verifier"
    CACHE="$TEST_TMP/.rddf/state/verifier/.ac-verdict-demo.json" \
    SHA="$1" MODE="$2" python3 - <<'PY'
import json, os
mode = os.environ["MODE"]
status = "pass" if mode == "pass" else "fail"
verdict = [
    {"ac_id": "AC-1", "description": "a", "status": status, "confidence": 0.9,
     "evidence": [], "reasoning": "fixture"},
    {"ac_id": "AC-2", "description": "b", "status": status, "confidence": 0.9,
     "evidence": [], "reasoning": "fixture"},
]
json.dump({
    "schema_version": 2, "version": 2, "change": "demo",
    "codebase_commit": os.environ["SHA"],
    "verdict": verdict,
    "verification_state": "passed" if status == "pass" else "failed",
    "failed_acs": [] if status == "pass" else ["AC-1", "AC-2"],
}, open(os.environ["CACHE"], "w"))
PY
}

_phase3() {
    run env PROJECT_ROOT="$TEST_TMP" PATH="$TEST_TMP/bin:$PATH" \
        SKIP_VERIFIER_CONTRACT=yes "$@" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
}

@test "phase3: refuses to archive when no verdict cache exists" {
    _phase3
    [ "$status" -eq 7 ]
    [[ "$output" == *"no valid verdict cache"* ]]
    [[ "$output" == *"rdd-verifier"* ]]
}

@test "phase3: archives when cache is complete and sha matches HEAD" {
    _write_cache "$(git -C "$TEST_TMP" rev-parse HEAD)" pass
    _phase3
    [ "$status" -eq 0 ]
}

@test "phase3: refuses when cached codebase_commit is stale" {
    _write_cache "0000000000000000000000000000000000000000" pass
    _phase3
    [ "$status" -eq 7 ]
    [[ "$output" == *"stale"* || "$output" == *"no valid verdict cache"* ]]
}

@test "phase3: SKIP_RDD_VERIFIER without reason fails closed" {
    _phase3 SKIP_RDD_VERIFIER=yes
    [ "$status" -eq 7 ]
    [[ "$output" == *"RDDF_VERIFIER_BYPASS_REASON"* ]]
}

@test "phase3: SKIP_RDD_VERIFIER with reason passes and writes bypass audit" {
    _phase3 SKIP_RDD_VERIFIER=yes RDDF_VERIFIER_BYPASS_REASON="integration fixture"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.rddf/state/.bypass-audit.jsonl" ]
}

@test "phase3: worktree mode without a worktree exits 3" {
    printf '{"execution_mode_decision": {"mode": "worktree"}}\n' \
        > .rddf/state/builder/demo.json
    _phase3
    [ "$status" -eq 3 ]
    [[ "$output" == *"worktree not found"* ]]
}

@test "phase3: incomplete tasks.md is refused by the gate (exit 7, not a silent abort)" {
    # set -euo pipefail + grep -c returning 1 (no completed tasks) must still
    # surface the gate's own message, not abort the script silently.
    printf '## Tasks\n\n- [ ] task one\n' > openspec/changes/demo/tasks.md
    _write_cache "$(git -C "$TEST_TMP" rev-parse HEAD)" pass
    _phase3
    [ "$status" -eq 7 ]
    [[ "$output" == *"未实现"* ]]
}

@test "phase3: cache with failed ACs only warns by default (archiving proceeds)" {
    _write_cache "$(git -C "$TEST_TMP" rev-parse HEAD)" fail
    _phase3
    [ "$status" -eq 0 ]
    [[ "$output" == *"failed ACs"* ]]
}

@test "phase3: cache with failed ACs blocks under STRICT_AC_GATE=yes" {
    _write_cache "$(git -C "$TEST_TMP" rev-parse HEAD)" fail
    _phase3 STRICT_AC_GATE=yes
    [ "$status" -eq 7 ]
    [[ "$output" == *"STRICT_AC_GATE"* ]]
}

@test "phase3: package-root resolver mirrors phase2_execute.sh candidate order" {
    # In a user project `_lib/` lives in the installed package, not $PROJECT_ROOT.
    grep -q '_resolve_pkg_root' "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh"
    for c in ".opencode/skills/rdd-workflow" ".agents/skills/rdd-workflow" ".agents/skills"; do
        grep -q "$c" "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" || return 1
    done
    grep -q '_resolve_pkg_root' "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh"
}

@test "phase3: no longer treats a verifier exit code as a verdict" {
    ! grep -q "verifier_run" "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh"
    ! grep -q "VERIFIER_EXIT" "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh"
    grep -q "archive_gate_check" "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh"
}
