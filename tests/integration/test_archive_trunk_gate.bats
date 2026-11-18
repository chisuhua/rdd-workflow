#!/usr/bin/env bats
# tests/integration/test_archive_trunk_gate.bats
#
# ADR-0061 —— the "trunk gate" (`archive_premerge_check`): the archive never
# merges for you, but it must not claim success while the implementation is
# still stranded on the branch.
#
# Judgment order (ADR-0061 decision 2):
#   (0) branch ref exists?   no  → 1  (refuse; fail closed like the verifier)
#   (1) worktree dirty?      yes → 1  (refuse; uncommitted work dies with it)
#   (2) is-ancestor?         yes → 0  (allow)
#   (3) content-equivalent (patch-id)  → 0 + warning (allow)
#   (4) not merged           → 1  (refuse)
#   (5) cannot decide        → 2  (allow + warning)

load ../test_helper

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export REPO_ROOT
    TEST_TMP="$(mktemp -d)"
    export TEST_TMP
    MAIN="$TEST_TMP/main"
    WT="$TEST_TMP/wt"
    mkdir -p "$MAIN"
    git -C "$MAIN" init -q -b main
    git -C "$MAIN" config user.email t@t.invalid
    git -C "$MAIN" config user.name tester
    printf 'base\n' > "$MAIN/base.txt"
    git -C "$MAIN" add -A
    git -C "$MAIN" commit -q -m init
    git -C "$MAIN" worktree add -q "$WT" -b openspec/demo
    # The worktree carries the artifacts the system itself copies in — they
    # must NOT count as "uncommitted work" (noise exclusion).
    mkdir -p "$WT/openspec/changes/demo" "$WT/.rddf/plans"
    printf -- '- [x] task\n' > "$WT/openspec/changes/demo/tasks.md"
    printf -- '### Task 1\n' > "$WT/.rddf/plans/demo.md"
    source "$REPO_ROOT/_lib/archive.sh"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# _commit_on_branch <file> <message>
_commit_on_branch() {
    printf '%s\n' "$1" > "$WT/$1"
    git -C "$WT" add "$1"
    git -C "$WT" commit -q -m "$2"
}

@test "trunk gate: branch ref missing → refuse (fail closed, not 'cannot decide')" {
    # Remove the worktree FIRST — a branch checked out in a worktree cannot
    # be deleted while the worktree exists.
    git -C "$MAIN" worktree remove --force "$WT" >/dev/null 2>&1 || true
    git -C "$MAIN" branch -D openspec/demo >/dev/null 2>&1 || true

    run archive_premerge_check "$MAIN" "openspec/demo" "main" ""
    [ "$status" -eq 1 ]
    [[ "$output" == *"不存在"* ]]
    # The recovery hint, not a merge command (there is no branch to merge).
    [[ "$output" == *"reflog"* ]]
}

@test "trunk gate: already merged → allow" {
    _commit_on_branch "impl.py" "impl"
    git -C "$MAIN" merge -q --no-ff openspec/demo -m "merge impl"

    run archive_premerge_check "$MAIN" "openspec/demo" "main" ""
    [ "$status" -eq 0 ]
}

@test "trunk gate: not merged → refuse + a copy-pasteable merge command" {
    _commit_on_branch "impl.py" "impl"

    run archive_premerge_check "$MAIN" "openspec/demo" "main" ""
    [ "$status" -eq 1 ]
    [[ "$output" == *"尚未合入"* ]]
    [[ "$output" == *"merge --no-ff 'openspec/demo'"* ]]
    [[ "$output" == *"ARCHIVE_ALLOW_UNMERGED"* ]]
}

@test "trunk gate: content-equivalent (squash-merge) → allow with a warning" {
    # The branch's commit is squashed into main: same content, different SHA.
    _commit_on_branch "impl.py" "impl"
    git -C "$MAIN" merge -q --squash openspec/demo
    git -C "$MAIN" commit -q -m "squashed impl"

    run archive_premerge_check "$MAIN" "openspec/demo" "main" ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"patch-id 等价"* ]]
}

@test "trunk gate: worktree dirty → refuse (uncommitted work dies with the worktree)" {
    _commit_on_branch "impl.py" "impl"
    printf 'dirty\n' > "$WT/dirty.py"

    run archive_premerge_check "$MAIN" "openspec/demo" "main" "$WT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"未提交的改动"* ]]
    [[ "$output" == *"commit -m"* ]]
}

@test "trunk gate: the artifacts the system copies in do NOT count as dirty" {
    _commit_on_branch "impl.py" "impl"
    # openspec/changes/demo/ and .rddf/plans/demo.md are untracked in the
    # worktree (that is how the copy lands) — they must be excluded.

    run archive_premerge_check "$MAIN" "openspec/demo" "main" "$WT"
    # Still refused — but for "not merged", NOT for "dirty".
    [ "$status" -eq 1 ]
    [[ "$output" != *"未提交的改动"* ]]
    [[ "$output" == *"尚未合入"* ]]
}

@test "trunk gate: dirty beats 'already merged' (precedence)" {
    _commit_on_branch "impl.py" "impl"
    git -C "$MAIN" merge -q --no-ff openspec/demo -m "merge impl"
    printf 'dirty\n' > "$WT/dirty.py"

    run archive_premerge_check "$MAIN" "openspec/demo" "main" "$WT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"未提交的改动"* ]]
}

@test "trunk gate: opt-in without a reason does NOT release the refusal" {
    _commit_on_branch "impl.py" "impl"

    ARCHIVE_ALLOW_UNMERGED=yes run archive_premerge_check "$MAIN" "openspec/demo" "main" ""
    [ "$status" -eq 1 ]
    [[ "$output" == *"RDDF_ARCHIVE_UNMERGED_REASON"* ]]
}

@test "trunk gate: opt-in with a reason releases the refusal and leaves an audit record" {
    _commit_on_branch "impl.py" "impl"

    RDDF_PROJECT_ROOT="$MAIN" \
    ARCHIVE_ALLOW_UNMERGED=yes RDDF_ARCHIVE_UNMERGED_REASON="hotfix fixture" \
        run archive_premerge_check "$MAIN" "openspec/demo" "main" ""
    [ "$status" -eq 0 ]
    [[ "$output" == *"已显式放行"* ]]

    AUDIT="$MAIN/.rddf/state/.bypass-audit.jsonl"
    [ -f "$AUDIT" ]
    grep -q "ARCHIVE_ALLOW_UNMERGED" "$AUDIT"
    grep -q "hotfix fixture" "$AUDIT"
}

@test "trunk gate: opt-in + FORCE_BRANCH_DELETE is refused (that combination deletes the code)" {
    _commit_on_branch "impl.py" "impl"

    ARCHIVE_ALLOW_UNMERGED=yes RDDF_ARCHIVE_UNMERGED_REASON="fixture" \
        FORCE_BRANCH_DELETE=yes \
        run archive_premerge_check "$MAIN" "openspec/demo" "main" ""
    [ "$status" -eq 1 ]
    [[ "$output" == *"不得与 FORCE_BRANCH_DELETE=yes 同时生效"* ]]
}

@test "cleanup: prints 'Worktree 已删除' ONLY when the removal really happened" {
    # A registered-but-dirty worktree cannot be removed without --force.
    _commit_on_branch "impl.py" "impl"
    printf 'dirty\n' > "$WT/dirty.py"

    run cleanup_worktree_and_branch "demo" "$MAIN" "$WT" "openspec/demo"
    [ "$status" -eq 2 ]
    [[ "$output" != *"✅ Worktree 已删除"* ]]
    [[ "$output" == *"worktree remove 失败"* ]]
    [[ "$output" == *"worktree remove --force"* ]]
}

@test "cleanup: an unregistered residual directory gets its own message" {
    # Remove the directory AND unregister it → what is left is an orphan
    # directory that git does not know about.
    rm -rf "$WT"
    git -C "$MAIN" worktree prune
    mkdir -p "$WT"

    run cleanup_worktree_and_branch "demo" "$MAIN" "$WT" "openspec/demo"
    [ "$status" -eq 2 ]
    [[ "$output" == *"未注册为 worktree"* ]]
    [[ "$output" == *"rm -rf"* ]]
}

@test "cleanup: never removes the MAIN repo as if it were a worktree" {
    run cleanup_worktree_and_branch "demo" "$MAIN" "$MAIN" "openspec/demo"
    # The main worktree is listed by `git worktree list`; removing it would
    # target the repository itself.
    [[ "$output" != *"✅ Worktree 已删除"* ]]
    [ -d "$MAIN" ]
}

@test "cleanup: an unmerged branch is kept (return 1) unless FORCE_BRANCH_DELETE=yes" {
    _commit_on_branch "impl.py" "impl"
    # Clean the worktree (the copied artifacts are untracked) so the removal
    # succeeds — this case is about the BRANCH, not about worktree residue.
    git -C "$WT" clean -fdq

    run cleanup_worktree_and_branch "demo" "$MAIN" "$WT" "openspec/demo"
    [ "$status" -eq 1 ]
    [[ "$output" == *"未合并的提交"* ]]
    git -C "$MAIN" rev-parse --verify --quiet refs/heads/openspec/demo >/dev/null

    FORCE_BRANCH_DELETE=yes run cleanup_worktree_and_branch "demo" "$MAIN" "$WT" "openspec/demo"
    [[ "$output" == *"强制删除"* ]]
}

@test "trunk gate: the ref-missing path gives NO merge command (there is nothing to merge)" {
    git -C "$MAIN" worktree remove --force "$WT" >/dev/null 2>&1 || true
    git -C "$MAIN" branch -D openspec/demo >/dev/null 2>&1 || true

    run archive_premerge_check "$MAIN" "openspec/demo" "main" ""
    [ "$status" -eq 1 ]
    [[ "$output" == *"reflog"* ]]
    # ADR-0061 decision 3 (fourth branch) + V-5(d): no merge command here.
    [[ "$output" != *"merge --no-ff"* ]]
}

@test "trunk gate: a non-git directory is 'cannot decide' (2), not 'branch missing' (1)" {
    local nogit="$TEST_TMP/not-a-repo"
    mkdir -p "$nogit"

    run archive_premerge_check "$nogit" "openspec/demo" "main" ""
    [ "$status" -eq 2 ]
    [[ "$output" == *"不是 git 仓库"* ]]
    # The misleading "the branch does not exist (deleted by the last archive)"
    # message must NOT be used for a directory that is not a repository.
    [[ "$output" != *"不存在"* ]]
}

@test "trunk gate: dirty worktree WITH commits on the branch → two-step guidance" {
    _commit_on_branch "impl.py" "impl"
    printf 'dirty\n' > "$WT/dirty.py"

    run archive_premerge_check "$MAIN" "openspec/demo" "main" "$WT"
    [ "$status" -eq 1 ]
    # ADR-0061 decision 3 (third branch) + V-5(c): commit first, then merge.
    [[ "$output" == *"两步"* ]]
    [[ "$output" == *"commit -m"* ]]
    [[ "$output" == *"merge --no-ff"* ]]
}

@test "trunk gate: dirty worktree with NO commits on the branch → commit-only guidance" {
    # The branch carries no commit beyond main's tip → there is nothing to
    # merge yet, so only the commit command can unblock the archive.
    printf 'dirty\n' > "$WT/dirty.py"

    run archive_premerge_check "$MAIN" "openspec/demo" "main" "$WT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"没有新提交"* ]]
    [[ "$output" == *"commit -m"* ]]
    [[ "$output" != *"merge --no-ff"* ]]
}

@test "docs: the gates catalogue names the trunk gate and 'the archive never merges'" {
    DOC="$REPO_ROOT/docs/architecture/gates-and-quality.md"
    [ -f "$DOC" ]
    grep -q "archive_premerge_check" "$DOC"
    grep -q "archive_gate_check" "$DOC"
    grep -qi "never merges" "$DOC"
}
