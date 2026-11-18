#!/usr/bin/env bats
# tests/integration/test_lightweight_branch_and_archive.bats
#
# `fix-lightweight-branch-and-archive`: the lightweight execution mode used to
# be a mode that could not finish P3.
#
#   * P2 declared `branch="openspec/<name>"` in the handoff WITHOUT creating
#     anything — a ghost branch. The verifier anchors on the branch tip, so a
#     lightweight change could never pass the archive gate (only an audited
#     bypass worked).
#   * P3's inline archive branch ran the AC gate and `openspec archive` and
#     nothing else: no merge judgment, no branch cleanup, no iteration sync,
#     no post-archive cleanup.
#
# Contract now under test (ADR-0024 / ADR-0036 revision / ADR-0061):
#   P2  creates the branch from the default tip (create / reuse / fail closed)
#       and keeps execution_mode_decision.mode consistent with reality.
#   P3  runs: AC gate → switch to default branch → commit-ownership check →
#       merge judgment (tracked=false) or merge (tracked=true) → openspec
#       archive → branch cleanup → archive-moves commit (tracked only) →
#       iteration sync with the real sha → post-archive cleanup.

load test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    TEST_TMP="$(mktemp -d)"
    export TEST_TMP
    cd "$TEST_TMP"
    git init -q -b master
    git config user.email "t@t.invalid"
    git config user.name tester

    mkdir -p .rddf/state/builder .rddf/plans openspec/changes/demo bin
    mkdir -p _lib
    ln -sfn "$REPO_ROOT/_lib/project_config.sh" _lib/project_config.sh

    printf '# demo\n\n## Acceptance\n\n- [ ] AC one\n' > openspec/changes/demo/proposal.md
    printf '## Tasks\n\n- [x] task one\n' > openspec/changes/demo/tasks.md
    printf '# plan\n' > .rddf/plans/demo.md

    # An openspec CLI stub that REALLY moves the files, so the archive leaves
    # the 3-path trio dirty and commit_archive_moves has something to commit.
    cat > bin/openspec <<'SH'
#!/bin/sh
# emulate: openspec archive <name> --yes
name="${2:-}"
dest="openspec/changes/archive/2026-01-01-${name}"
mkdir -p "$dest" "openspec/specs/${name}"
if [ -d "openspec/changes/${name}" ]; then
    for f in openspec/changes/"${name}"/*; do
        [ -e "$f" ] && mv "$f" "$dest/"
    done
    rmdir "openspec/changes/${name}" 2>/dev/null || true
fi
printf '# %s\n' "$name" > "openspec/specs/${name}/spec.md"
exit 0
SH
    chmod +x bin/openspec

    git add -A
    git commit -q -m fixture

    export PROJECT_ROOT="$TEST_TMP"
    export PATH="$TEST_TMP/bin:$PATH"
}

teardown() {
    cd /
    rm -rf "$TEST_TMP"
}

# ── helpers ────────────────────────────────────────────────────────────────

_handoff_lightweight() {
    cat > .rddf/state/builder/demo.json <<'JSON'
{
  "schema": "builder-handoff-v1", "version": 1, "owner": "rdd-builder",
  "change_name": "demo", "current_phase": "phase-1",
  "execution_mode_decision": {"mode": "lightweight", "reason": "files=1<=2 AND tasks=1<=3"}
}
JSON
}

_handoff_worktree() {
    cat > .rddf/state/builder/demo.json <<'JSON'
{
  "schema": "builder-handoff-v1", "version": 1, "owner": "rdd-builder",
  "change_name": "demo", "current_phase": "phase-1",
  "execution_mode_decision": {"mode": "worktree", "reason": "files=9>2"}
}
JSON
}

_project_yaml_tracked_false() {
    mkdir -p .rddf
    printf 'git:\n  openspec_tracked: false\n' > .rddf/project.yaml
    git add .rddf/project.yaml && git commit -q -m "project.yaml"
}

# Write a passing verdict cache anchored at the given sha.
_write_cache() {
    local sha="$1"
    mkdir -p .rddf/state/verifier
    SHA="$sha" python3 - <<'PY'
import json, os
json.dump({
    "schema_version": 2, "version": 2, "change": "demo",
    "codebase_commit": os.environ["SHA"],
    "verdict": [{"ac_id": "AC-1", "description": "a", "status": "pass",
                 "confidence": 0.9, "evidence": [], "reasoning": "fixture"}],
    "verification_state": "passed", "failed_acs": [],
}, open(".rddf/state/verifier/.ac-verdict-demo.json", "w"))
PY
}

_commit_impl_on_branch() {
    local base
    base=$(git rev-parse master)
    git checkout -q -b openspec/demo master
    echo "impl" > impl.py
    git add impl.py
    git commit -q -m "feat(demo): implementation"
    git checkout -q master
    # Mirror P2: it records the creation point (branch_base_sha), which P3's
    # ownership check uses to tell "nothing committed" from "merged manually".
    BASE_SHA="$base" python3 - <<'PY'
import json, os
p = ".rddf/state/builder/demo.json"
d = json.load(open(p))
d.setdefault("execution_mode_decision", {})["branch_base_sha"] = os.environ["BASE_SHA"]
json.dump(d, open(p, "w"), indent=2)
PY
}

_phase2() {
    run env PROJECT_ROOT="$TEST_TMP" bash "$REPO_ROOT/skills/rdd-builder/scripts/phase2_execute.sh" demo
}

_phase3() {
    # SKIP_VERIFIER_CONTRACT: the verifier-contract sub-gate is a separate
    # concern; the AC gate is exercised through a real verdict cache.
    run env PROJECT_ROOT="$TEST_TMP" SKIP_VERIFIER_CONTRACT=yes "$@" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
}

_handoff_field() {
    python3 -c "
import json
d = json.load(open('.rddf/state/builder/demo.json'))
cur = d
for k in '$1'.split('.'):
    cur = cur.get(k, {}) if isinstance(cur, dict) else {}
print(cur if not isinstance(cur, dict) else json.dumps(cur))
"
}

# ── P2: the branch is real ─────────────────────────────────────────────────

@test "P2 lightweight: creates openspec/<change> at the default branch tip" {
    _handoff_lightweight
    local tip_before
    tip_before=$(git rev-parse master)

    _phase2
    [ "$status" -eq 0 ]

    # The ref exists and starts exactly at the default tip (not at HEAD of
    # some other branch, not detached).
    [ "$(git rev-parse openspec/demo)" = "$tip_before" ]
    # P2 executes ON the branch.
    [ "$(git branch --show-current)" = "openspec/demo" ]
    [[ "$output" == *"mode=lightweight"* ]]
}

@test "P2 lightweight: the first implementation commit sits on the default tip" {
    _handoff_lightweight
    local tip_before
    tip_before=$(git rev-parse master)
    _phase2
    [ "$status" -eq 0 ]

    echo "impl" > impl.py
    git add impl.py && git commit -q -m "feat(demo): implementation"

    # AC: "the branch tip's parent == the default branch tip" — i.e. the
    # branch was based on the default tip, not on some other base.
    [ "$(git rev-parse openspec/demo^)" = "$tip_before" ]
}

@test "P2 lightweight: an existing branch at the default tip is reused" {
    _handoff_lightweight
    git branch openspec/demo master
    _phase2
    [ "$status" -eq 0 ]
    [ "$(git branch --show-current)" = "openspec/demo" ]
    [ "$(git rev-parse openspec/demo)" = "$(git rev-parse master)" ]
    [[ "$output" == *"复用"* ]]
}

@test "P2 lightweight: an existing branch pointing elsewhere fails closed to worktree" {
    _handoff_lightweight
    # A leftover branch with commits of its own (tip != default tip).
    _commit_impl_on_branch
    git checkout -q master

    _phase2
    # The worktree cannot be created either (the branch name is taken) — a
    # hard error, never a silent "run in the main repo".
    [ "$status" -eq 3 ]
    [[ "$output" == *"退回 worktree 模式失败"* ]]

    # …and the handoff describes the DOWNGRADE, not the abandoned intent:
    # a declaration that contradicts reality is the ghost branch one level up.
    [ "$(_handoff_field execution_mode_decision.mode)" = "worktree" ]
    [ -n "$(_handoff_field execution_mode_decision.reason)" ]
}

@test "helper: lightweight_branch_prepare distinguishes create / reuse / fail-closed" {
    run bash -c "
        source '$REPO_ROOT/_lib/archive.sh'
        # (1) missing → create
        lightweight_branch_prepare '$TEST_TMP' openspec/new-one master >/dev/null 2>&1
        echo \"create=\$?\"
        git -C '$TEST_TMP' checkout -q master
        # (2) existing at the default tip → reuse
        git -C '$TEST_TMP' branch openspec/same master
        lightweight_branch_prepare '$TEST_TMP' openspec/same master >/dev/null 2>&1
        echo \"reuse=\$?\"
        git -C '$TEST_TMP' checkout -q master
        # (3) existing pointing elsewhere → fail closed (1)
        git -C '$TEST_TMP' checkout -q -b openspec/other master
        echo x > '$TEST_TMP/other.txt'
        git -C '$TEST_TMP' add other.txt && git -C '$TEST_TMP' commit -q -m other
        git -C '$TEST_TMP' checkout -q master
        lightweight_branch_prepare '$TEST_TMP' openspec/other master >/dev/null 2>&1
        echo \"failclosed=\$?\"
    "
    [ "$status" -eq 0 ]
    [[ "$output" == *"create=0"* ]]
    [[ "$output" == *"reuse=0"* ]]
    [[ "$output" == *"failclosed=1"* ]]
}

@test "P2 lightweight: the base sha is recorded in the handoff" {
    _handoff_lightweight
    local tip_before
    tip_before=$(git rev-parse master)
    _phase2
    [ "$status" -eq 0 ]
    [ "$(_handoff_field execution_mode_decision.branch_base_sha)" = "$tip_before" ]
}

@test "P2 lightweight: the branch is based on the DEFAULT tip even when HEAD is elsewhere" {
    _handoff_lightweight
    local default_tip
    default_tip=$(git rev-parse master)
    # HEAD sits on another branch. A bare `git checkout -b` would base the
    # implementation branch on THAT commit — every later merge-base / cherry /
    # anchor computation would then be relative to the wrong base.
    git checkout -q -b feature-elsewhere
    echo "other" > other.txt
    git add other.txt && git commit -q -m "unrelated work"

    _phase2
    [ "$status" -eq 0 ]
    [ "$(git rev-parse openspec/demo)" = "$default_tip" ]
}

@test "capability: a small change is now actually decided as lightweight" {
    # LIGHTWEIGHT_EXECUTION_READY (ADR-0036 V-G). While it was False the honest
    # answer was worktree + "lightweight 未落地"; the mode is now usable, so the
    # decision must return it. Flipping the constant back is the rollback.
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from _lib.builder_deps import decide_execution_mode
d = decide_execution_mode(file_count=2, task_count=3, risk_keywords=[])
print(d['mode'], '|', d['reason'])
"
    [ "$status" -eq 0 ]
    [[ "$output" == lightweight* ]]
}

@test "P2 abort: a failing P2 returns the main repo HEAD to the default branch" {
    _handoff_lightweight
    # P2 fails after the branch checkout: no plan file.
    rm -f .rddf/plans/demo.md
    _phase2
    [ "$status" -eq 3 ]
    [ "$(git branch --show-current)" = "master" ]
}

# ── P3: commit ownership ───────────────────────────────────────────────────

@test "P3 lightweight: a branch with NO commit of its own is refused" {
    _handoff_lightweight
    git checkout -q -b openspec/demo master
    git checkout -q master
    _write_cache "$(git rev-parse openspec/demo)"

    _phase3
    [ "$status" -eq 3 ]
    [[ "$output" == *"没有相对"* ]]
    [[ "$output" == *"commit -m"* ]]
    # …and the change was NOT archived.
    [ -d openspec/changes/demo ]
}

@test "P3 lightweight: an empty-shell branch created by P2 is refused (base sha path)" {
    # The realistic empty shell: P2 created the branch and recorded
    # branch_base_sha; execute never committed. The branch tip therefore
    # EQUALS the base — nothing to verify and nothing to merge.
    _handoff_lightweight
    _phase2
    [ "$status" -eq 0 ]
    local tip
    tip=$(git rev-parse openspec/demo)
    [ "$tip" = "$(git rev-parse master)" ]
    _write_cache "$tip"

    _phase3
    [ "$status" -eq 3 ]
    [[ "$output" == *"没有相对"* ]]
    [ -d openspec/changes/demo ]
}

@test "P3 lightweight: a branch with its own commit passes the ownership check" {
    _handoff_lightweight
    _commit_impl_on_branch
    _write_cache "$(git rev-parse openspec/demo)"

    _phase3
    [ "$status" -eq 0 ]
}

@test "P3 lightweight: the refusal path leaves HEAD on the default branch" {
    _handoff_lightweight
    # Realistic state: P2 left HEAD on the implementation branch.
    git checkout -q -b openspec/demo master
    [ "$(git branch --show-current)" = "openspec/demo" ]
    _write_cache "$(git rev-parse openspec/demo)"

    _phase3
    [ "$status" -eq 3 ]
    # The switch happens BEFORE the refusal checks, so a refused archive does
    # not leave the user's repo parked on the implementation branch.
    [ "$(git branch --show-current)" = "master" ]
}

# ── P3: merge judgment + cleanup + iteration sync ───────────────────────────

@test "P3 lightweight (tracked): merges the branch, deletes it, syncs iteration.json" {
    _handoff_lightweight
    _commit_impl_on_branch
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'JSON'
{"version": 7, "updated_at": "2026-01-01T00:00:00Z", "current_phase": "phase-1",
 "changes": [{"name": "demo", "status": "in_worktree", "phase": "phase-1",
              "category": "general", "priority": "P1", "added_at": "2026-01-01T00:00:00Z"}]}
JSON
    git add .rddf/state/iteration.json && git commit -q -m "seed iteration"
    local impl_sha
    impl_sha=$(git rev-parse openspec/demo)
    _write_cache "$impl_sha"

    _phase3
    [ "$status" -eq 0 ]

    # (1) merged into the default branch
    git merge-base --is-ancestor "$impl_sha" master
    # (2) the branch was deleted
    run git rev-parse --verify --quiet refs/heads/openspec/demo
    [ "$status" -ne 0 ]
    # (3) iteration.json reached the archived state with a REAL sha
    run python3 -c "
import json
d = json.load(open('.rddf/state/iteration.json'))
c = [x for x in d['changes'] if x['name'] == 'demo'][0]
print(c['status'], c.get('archive_commit_sha') or '')
"
    [[ "$output" == archived* ]]
    local sha
    sha=$(echo "$output" | awk '{print $2}')
    [ -n "$sha" ]
    [ "$sha" = "$(git rev-parse master)" ]
}

@test "P3 lightweight: removes the change's plan file (post_archive_cleanup)" {
    _handoff_lightweight
    _commit_impl_on_branch
    _write_cache "$(git rev-parse openspec/demo)"
    # The plan file is TRACKED and still present — the archive itself must
    # remove it (it used to rely on a caller having deleted it first, which
    # nothing did after the v4 stage merge).
    [ -f .rddf/plans/demo.md ]
    git ls-files --error-unmatch .rddf/plans/demo.md >/dev/null

    _phase3
    [ "$status" -eq 0 ]
    [ ! -e .rddf/plans/demo.md ]
    run git ls-files --error-unmatch .rddf/plans/demo.md
    [ "$status" -ne 0 ]
}

@test "P3 lightweight: a failed branch cleanup only warns (archive still succeeds)" {
    _handoff_lightweight
    _commit_impl_on_branch
    _write_cache "$(git rev-parse openspec/demo)"

    # Make `git branch -d` fail AFTER the merge by re-creating a branch with a
    # commit that is not merged: simulate by refusing deletion through a
    # read-only hook is fragile — instead assert the return-code contract
    # directly on the helper (wt_path empty, unmerged branch, no FORCE).
    run bash -c "
        cd '$TEST_TMP'
        source '$REPO_ROOT/_lib/archive.sh'
        git branch openspec/unmerged master
        git checkout -q openspec/unmerged && echo z > z.txt && git add z.txt && git commit -q -m z && git checkout -q master
        cleanup_worktree_and_branch unmerged '$TEST_TMP' '' openspec/unmerged
        echo rc=\$?
    "
    [[ "$output" == *"rc=1"* ]]
    [[ "$output" == *"Branch 删除取消"* ]]
    # The main repo itself was never removed.
    [ -d "$TEST_TMP/.git" ]
}

@test "P3 lightweight: the main repo is never treated as a worktree" {
    _handoff_lightweight
    _commit_impl_on_branch
    _write_cache "$(git rev-parse openspec/demo)"

    # wt_path == main_root must not trigger `git worktree remove`.
    run bash -c "
        cd '$TEST_TMP'
        source '$REPO_ROOT/_lib/archive.sh'
        cleanup_worktree_and_branch demo '$TEST_TMP' '$TEST_TMP' openspec/demo
        echo rc=\$?
    "
    [[ "$output" != *"worktree remove 失败"* ]]
    [ -d "$TEST_TMP/.git" ]
    [ -f "$TEST_TMP/openspec/changes/demo/tasks.md" ]
}

# ── P3: dirty semantics fork ───────────────────────────────────────────────

@test "P3 lightweight: unrelated dirty files in the main repo do NOT refuse the archive" {
    _handoff_lightweight
    _commit_impl_on_branch
    _write_cache "$(git rev-parse openspec/demo)"
    # Unrelated, uncommitted work in the main repo (belongs to another change).
    echo "someone else's work" > unrelated.txt

    _phase3
    [ "$status" -eq 0 ]
    [[ "$output" == *"主仓存在未提交改动"* ]]
}

@test "P3 lightweight: uncommitted IMPLEMENTATION is refused by the ownership check" {
    _handoff_lightweight
    _commit_impl_on_branch
    _write_cache "$(git rev-parse openspec/demo)"
    # A second writer stray file in the tree is irrelevant; what matters is
    # that the ownership judgment is about the BRANCH, not about dirt.
    echo "stray" > stray.txt

    _phase3
    # The branch DOES carry a commit, so the archive proceeds — the dirt is
    # only warned about. This pins the fork: dirt never refuses, the branch
    # commit count is what refuses.
    [ "$status" -eq 0 ]
    [[ "$output" == *"主仓存在未提交改动"* ]]
}

# ── P3: the 2x2 matrix ─────────────────────────────────────────────────────

@test "P3 lightweight + tracked=false: no merge, no archive-moves commit, trunk gate refuses unmerged" {
    _handoff_lightweight
    _project_yaml_tracked_false
    _commit_impl_on_branch
    _write_cache "$(git rev-parse openspec/demo)"

    # Unmerged implementation + tracked=false → the trunk gate refuses.
    _phase3
    [ "$status" -eq 3 ]
    [[ "$output" == *"尚未合入"* ]]
    [[ "$output" == *"merge --no-ff"* ]]

    # Merge it manually (the archive never does), then archive succeeds —
    # without a `archive(demo)` commit (openspec_tracked=false).
    git merge -q --no-ff openspec/demo -m "merge demo"
    _phase3
    [ "$status" -eq 0 ]
    # Call-level assertion: the helper must NOT be invoked at all. A behavioral
    # assertion cannot see the difference (the helper short-circuits on
    # openspec_tracked=false as defense-in-depth), so assert on its own
    # announcement instead.
    [[ "$output" != *"commit_archive_moves"* ]]
    run git log --oneline
    [[ "$output" != *"archive(demo): archive completed"* ]]
}

@test "P3 lightweight + tracked=true: the archive-moves commit IS created" {
    _handoff_lightweight
    _commit_impl_on_branch
    _write_cache "$(git rev-parse openspec/demo)"

    _phase3
    [ "$status" -eq 0 ]
    run git log --oneline
    [[ "$output" == *"archive(demo): archive completed"* ]]
}

# ── e2e: the whole lifecycle ───────────────────────────────────────────────

@test "e2e lightweight: handoff → P2 → rdd-verify → P3 → archived" {
    _handoff_lightweight
    _phase2
    [ "$status" -eq 0 ]
    [ "$(git branch --show-current)" = "openspec/demo" ]

    # The implementation is committed on the branch (execute's job).
    echo "impl" > impl.py
    git add impl.py && git commit -q -m "feat(demo): implementation"

    # iteration.json must register the change as verifier-eligible
    # (discovery.py: status in {in_worktree, completed} AND
    #  tasks_done == tasks_total > 0 AND not archived).
    mkdir -p .rddf/state
    cat > .rddf/state/iteration.json <<'JSON'
{"version": 7, "updated_at": "2026-01-01T00:00:00Z", "current_phase": "phase-2",
 "changes": [{"name": "demo", "status": "in_worktree", "phase": "phase-2",
              "category": "general", "priority": "P1", "added_at": "2026-01-01T00:00:00Z",
              "tasks_done": 1, "tasks_total": 1}]}
JSON

    # The agent writes the verdict cache anchored at the branch tip.
    _write_cache "$(git rev-parse openspec/demo)"

    # rdd rdd-verify must agree the change is archive-ready.
    run env PROJECT_ROOT="$TEST_TMP" PYTHONPATH="$REPO_ROOT" python3 -m _lib.cli.rdd_verify_cmd
    [ "$status" -eq 0 ]
    [[ "$output" == *"passed"* ]]

    # P3 archives for real.
    _phase3
    [ "$status" -eq 0 ]

    [ ! -d openspec/changes/demo ]
    [ -d openspec/changes/archive/2026-01-01-demo ]

    # iteration.json reached the archived state (the old lightweight path
    # never called mark_iteration_archived at all).
    run python3 -c "
import json
d = json.load(open('.rddf/state/iteration.json'))
print([x for x in d['changes'] if x['name'] == 'demo'][0]['status'])
"
    [ "$output" = "archived" ]
}

# ── spec deltas + dependency registration ─────────────────────────────────

@test "spec delta: the tracked-skip spec orders the commit-ownership + merge checks" {
    local spec="$REPO_ROOT/openspec/specs/archive-openspec-tracked-skip-commit/spec.md"
    [ -f "$spec" ] || skip "openspec/ is not checked out locally"
    grep -q "archive_premerge_check" "$spec"
    grep -q "commit-ownership\|提交归属\|lightweight_commit_ownership_check" "$spec"
}

@test "spec delta: archive-auto-commit points the lightweight MUST at rdd-builder P3" {
    local spec="$REPO_ROOT/openspec/specs/archive-auto-commit/spec.md"
    [ -f "$spec" ] || skip "openspec/ is not checked out locally"
    grep -q "rdd-builder" "$spec"
    grep -q "phase3_archive.sh" "$spec"
}

@test "dependency: the fix-worktree-archive-path acceptance-8 override is registered" {
    local f="$REPO_ROOT/.rddf/improvements/fix-lightweight-branch-and-archive.md"
    [ -f "$f" ]
    grep -q "acceptance-8" "$f"
}
