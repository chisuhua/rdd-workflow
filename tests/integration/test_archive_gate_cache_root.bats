#!/usr/bin/env bats
# tests/integration/test_archive_gate_cache_root.bats
#
# fix-verifier-gate-cache-root — the 2×2 matrix for the gate's cache lookup.
#
# Before the fix the gate and its writers disagreed about TWO things:
#   * which ROOT the verdict cache lives in (the gate's bash segment read
#     $tasks_root, its python segment read the main repo root);
#   * which REF the freshness anchor is (the bash segment compared against
#     HEAD, the write side records the openspec/<change> branch tip).
#
# The anchor is now the branch tip (root-independent — see
# openspec/specs/verifier-lifecycle/spec.md § "Implementation commit SHALL be
# the openspec branch tip"), and the gate reads the cache from the gate root
# first and the canonical state root second.
#
# Every case asserts WHICH side was read — without that assertion the matrix
# would be a fake green light (both sides would "pass" for the same reason).

load ../test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    TEST_TMP="$(mktemp -d)"
    MAIN="$TEST_TMP/main"
    WT="$TEST_TMP/wt"
    mkdir -p "$MAIN"
    git -C "$MAIN" init -q -b main
    git -C "$MAIN" config user.email t@t.invalid
    git -C "$MAIN" config user.name tester
    printf 'base\n' > "$MAIN/base.txt"
    git -C "$MAIN" add -A
    git -C "$MAIN" commit -q -m init
    # A REAL worktree on the implementation branch.
    git -C "$MAIN" worktree add -q "$WT" -b openspec/matrix-change
    # The change's artifacts live in the worktree = the GATE ROOT.
    mkdir -p "$WT/openspec/changes/matrix-change"
    printf -- '## Tasks\n- [x] task one\n' > "$WT/openspec/changes/matrix-change/tasks.md"
    printf -- '## Acceptance Criteria\n- AC-1: works\n' \
        > "$WT/openspec/changes/matrix-change/proposal.md"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# _seed_cache <root> <codebase_commit>
_seed_cache() {
    local root="$1" sha="$2"
    mkdir -p "$root/.rddf/state/verifier"
    CACHE="$root/.rddf/state/verifier/.ac-verdict-matrix-change.json" \
    SHA="$sha" python3 - <<'PY'
import json, os
json.dump({
    "schema_version": 2, "version": 2, "change": "matrix-change",
    "codebase_commit": os.environ["SHA"],
    "verdict": [{"ac_id": "AC-1", "status": "pass", "confidence": 0.95,
                 "evidence": [{"tool": "Grep", "query": "x",
                               "result_summary": "y"}], "reasoning": "ok"}],
    "verification_state": "passed", "failed_acs": [],
}, open(os.environ["CACHE"], "w"))
PY
}

_run_gate() {
    run bash -c "source '$REPO_ROOT/_lib/archive.sh' && archive_gate_check 'matrix-change' '$WT'"
}

@test "matrix A: cache only in the MAIN repo → READY, and the gate says which side it read" {
    local tip
    tip="$(git -C "$WT" rev-parse openspec/matrix-change)"
    _seed_cache "$MAIN" "$tip"

    _run_gate
    [ "$status" -eq 0 ]
    [[ "$output" == *"Reusing verifier verdict cache"* ]]
    # The cache was found in the canonical state root, NOT in the gate root.
    [[ "$output" == *"verdict cache found in $MAIN"* ]]
    [[ "$output" != *"also exists in"* ]]
}

@test "matrix B: cache only in the WORKTREE → READY, and the gate says which side it read" {
    local tip
    tip="$(git -C "$WT" rev-parse openspec/matrix-change)"
    _seed_cache "$WT" "$tip"

    _run_gate
    [ "$status" -eq 0 ]
    [[ "$output" == *"Reusing verifier verdict cache"* ]]
    # The gate root (the CONTRACT root) won — no fallback message.
    [[ "$output" != *"verdict cache found in"* ]]
    [[ "$output" != *"also exists in"* ]]
}

@test "matrix C: codebase_commit != branch tip → stale (freshness is NOT relaxed)" {
    _seed_cache "$WT" "0000000000000000000000000000000000000000"

    _run_gate
    [ "$status" -eq 1 ]
    [[ "$output" == *"stale"* ]]
    [[ "$output" == *"no valid verdict cache"* ]]
}

@test "matrix D: both sides hold a cache → the gate root wins and the other side is reported" {
    local tip
    tip="$(git -C "$WT" rev-parse openspec/matrix-change)"
    _seed_cache "$WT" "$tip"
    _seed_cache "$MAIN" "$tip"

    _run_gate
    [ "$status" -eq 0 ]
    [[ "$output" == *"also exists in $MAIN"* ]]
    # The gate root was used — the fallback message must NOT appear.
    [[ "$output" != *"verdict cache found in"* ]]
}

# _put_artifacts_in_main <root>
#   The openspec_tracked=false layout: openspec/ is untracked, so the change's
#   artifacts live in the MAIN repo and the gate root is the MAIN repo.
_put_artifacts_in_main() {
    local root="$1"
    mkdir -p "$root/openspec/changes/matrix-change"
    printf -- '## Tasks\n- [x] task one\n' > "$root/openspec/changes/matrix-change/tasks.md"
    printf -- '## Acceptance Criteria\n- AC-1: works\n' \
        > "$root/openspec/changes/matrix-change/proposal.md"
}

@test "matrix E: the anchor is the BRANCH TIP, not HEAD (false-branch path)" {
    # The openspec_tracked=false path: the gate root is the MAIN repo, whose
    # HEAD is the DEFAULT branch — not the implementation commit. A cache
    # stamped with the branch tip must stay fresh (the pre-fix HEAD anchor
    # reported it as stale: the false branch switches the main repo to the
    # default branch right before running the gate).
    local tip
    tip="$(git -C "$WT" rev-parse openspec/matrix-change)"
    _put_artifacts_in_main "$MAIN"
    _seed_cache "$MAIN" "$tip"
    # The default branch moved past the branch tip.
    git -C "$MAIN" commit -q --allow-empty -m "default branch moved on"

    run bash -c "source '$REPO_ROOT/_lib/archive.sh' && archive_gate_check 'matrix-change' '$MAIN'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Reusing verifier verdict cache"* ]]
}

@test "matrix F: a cache stamped with the default branch's HEAD is stale" {
    # The pre-fix anchor was HEAD; with the branch-tip anchor a cache stamped
    # with the default branch's tip no longer authorizes the archive.
    _put_artifacts_in_main "$MAIN"
    git -C "$MAIN" commit -q --allow-empty -m "default branch moved on"
    local head_sha
    head_sha="$(git -C "$MAIN" rev-parse HEAD)"
    _seed_cache "$MAIN" "$head_sha"

    run bash -c "source '$REPO_ROOT/_lib/archive.sh' && archive_gate_check 'matrix-change' '$MAIN'"
    [ "$status" -eq 1 ]
    [[ "$output" == *"stale"* ]]
}

@test "matrix G: missing branch → the gate fails closed (no HEAD fallback)" {
    # A change whose implementation branch does not exist: the anchor cannot
    # be resolved, so the gate must fail closed instead of falling back to
    # HEAD (openspec/specs/verifier-lifecycle/spec.md § "Branch missing fails
    # closed").
    mkdir -p "$WT/openspec/changes/no-branch-change"
    printf -- '## Tasks\n- [x] task one\n' > "$WT/openspec/changes/no-branch-change/tasks.md"
    printf -- '## Acceptance Criteria\n- AC-1: works\n' \
        > "$WT/openspec/changes/no-branch-change/proposal.md"
    _seed_cache "$WT" "0000000000000000000000000000000000000000"

    run bash -c "source '$REPO_ROOT/_lib/archive.sh' && archive_gate_check 'no-branch-change' '$WT'"
    [ "$status" -eq 1 ]
    [[ "$output" == *"cannot resolve the implementation branch"* ]]
    [[ "$output" == *"no valid verdict cache"* ]]
}

@test "matrix H: SKIP_RDD_VERIFIER + reason still bypasses when the anchor cannot be resolved" {
    # AC: the audited bypass must stay reachable — a root/anchor resolution
    # failure must not short-circuit it.
    mkdir -p "$WT/openspec/changes/no-branch-change"
    printf -- '## Tasks\n- [x] task one\n' > "$WT/openspec/changes/no-branch-change/tasks.md"
    printf -- '## Acceptance Criteria\n- AC-1: works\n' \
        > "$WT/openspec/changes/no-branch-change/proposal.md"

    # The bypass-audit log lands in ${RDDF_PROJECT_ROOT:-$PWD}, and
    # verifier_contract_check UNSETS RDDF_PROJECT_ROOT on the way out ⇒ the
    # effective root is the CWD. Run the gate from this test's fake worktree so
    # the audit lands there and NOT in the real repo (before this, every run
    # of this file added one entry to the repo's .rddf/state/.bypass-audit.jsonl
    # — which is what tripped doctor's bypass-audit WARNING: SKIP_RDD_VERIFIER=9
    # over a limit of 5).
    SKIP_RDD_VERIFIER=yes RDDF_VERIFIER_BYPASS_REASON="matrix fixture" \
        run bash -c "cd '$WT' && source '$REPO_ROOT/_lib/archive.sh' && archive_gate_check 'no-branch-change' '$WT'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"bypassed"* ]]
}
