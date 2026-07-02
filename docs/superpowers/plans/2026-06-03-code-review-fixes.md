# Code Review Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the 7 remaining real bugs in this repository that were identified in `CODE_REVIEW.md` but are still present in the actual code (many CODE_REVIEW items have already been fixed by prior commits and are not in scope here).

**Architecture:** Each fix is a single-file, local edit that preserves the surrounding workflow. No new dependencies. No new files. The fixes are batched into 7 atomic commits (one per real bug) so each commit is independently revertable.

**Tech Stack:** Markdown skill files containing embedded bash/Python code blocks. Git for atomic commits. POSIX sh + coreutils for shell logic. No new tools introduced.

**Spec:** [`docs/superpowers/specs/2026-06-03-code-review-fixes-design.md`](../specs/2026-06-03-code-review-fixes-design.md) (commit `50c4bbb`)

---

## Pre-Plan Verification (read before starting)

`CODE_REVIEW.md` was reviewed against the actual current code on `master` (`6d89e35` + `50c4bbb` spec). **The following CODE_REVIEW items are already fixed in real code and are NOT in scope:**

- #1, #2 (Python f-string / shell var in f-string) — `propose.md:135-156` uses `os.environ.get` and double quotes correctly.
- #4 (empty WORKTREE_PATH) — `status.md:352` already guards with `&& [ "$WORKTREE_PATH" != "/" ]`.
- #6 (jq arithmetic) — `status.md:137` validates with `[[ "$COMPLETE" =~ ^[0-9]+$ ]]`.
- #7 (grep regex injection) — `guide.md:188` already uses `grep -qF`.
- #8 (portable stat) — `plan.md:81-90` defines `get_mtime()`.
- #9 (portable readlink) — `INSTALL.md:84` uses `realpath`.
- #10 (portable nproc) — `execute.md:181-189` defines `get_nproc()`.
- #12 (set -euo pipefail) — `install.sh:6` already has it.
- #14/#32 in `status.md` (merge --ff-only fallback) — `status.md:323-330` has `if MERGE_BASE = MAIN_TIP; then --ff-only else --no-ff -m` pattern.
- #15 (git branch --format) — `plan.md:55` doesn't use `--format`.
- #29 (grep `\|` → `-E`) — `propose.md:214` uses `-E`.

**What IS still real** (verified by reading the actual files):

| CODE_REVIEW # | Bug | Files |
|---|---|---|
| #3 | `wc -l` on potentially empty input returns 1, not 0 | guide.md, execute.md, status.md, plan.md, propose.md |
| #5 | `$PROJECT_ROOT` unquoted in path expansions | guide.md |
| #11 | `for wt in $(... | awk '{print $1}')` word-splits on whitespace | guide.md |
| #34 | `git branch -d` fails on unmerged commits (no `-D` fallback) | guide.md |
| #32 (guide.md portion) | `git merge` after `--ff-only` failure lacks `-m "..."` (pattern mismatch with status.md) | guide.md |
| #25 | `mktemp /tmp/...` hardcodes `/tmp` | execute.md, status.md |
| #28 | Hardcoded fallback `"/workspace/project/CppHDL"` | status.md, execute.md, guide.md |

---

## Task 0: Baseline Verification

**Files:** none (read-only check)

- [ ] **Step 1: Confirm working tree is clean and on master**

```bash
git status && git branch --show-current
```

Expected output:
```
On branch master
Your branch is up to date with 'origin/master'.
nothing to commit, working tree clean
master
```

- [ ] **Step 2: Confirm spec commit is present**

```bash
git log --oneline -3
```

Expected output includes `50c4bbb docs(spec): add design spec for CODE_REVIEW Critical+High fixes`.

- [ ] **Step 3: Run negative grep baseline (capture before-state)**

```bash
git grep -nE 'wc -l|\$\(.*\)\s*-\s*gt 0|for wt in \$\(git worktree list' skills/ install.sh
```

Expected: 8+ matches captured (the bugs to fix). Save output to compare after each task.

---

## Task 1: Fix `wc -l` on empty input in `guide.md` (5 locations)

**Files:**
- Modify: `skills/guide.md:263, 286, 366, 919, 1168`

- [ ] **Step 1: Read each of the 5 lines to confirm context**

```bash
sed -n '263p;286p;366p;919p;1168p' skills/guide.md
```

Expected: 5 lines, each containing `wc -l` (likely with different surrounding code).

- [ ] **Step 2: Replace line 263 (`GIT_CLEAN`)**

Old:
```bash
GIT_CLEAN=$(git status --porcelain | wc -l)
```

New:
```bash
GIT_CLEAN=$(git status --porcelain | grep -c . || true)
```

- [ ] **Step 3: Replace line 286 (`ACTIVE`)**

Old:
```bash
ACTIVE=$(ls -d $PROJECT_ROOT/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
```

New (also fixes issue #5 — quotes `$PROJECT_ROOT`):
```bash
ACTIVE=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | grep -c . || true)
```

- [ ] **Step 4: Replace line 366 (`ACTIVE_CHANGES`)**

Old:
```bash
ACTIVE_CHANGES=$(ls -d $PROJECT_ROOT/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
```

New (also fixes issue #5):
```bash
ACTIVE_CHANGES=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | grep -c . || true)
```

- [ ] **Step 5: Replace line 919 (`WORKTREE_COUNT`)**

Old:
```bash
WORKTREE_COUNT=$(git worktree list | grep "openspec/" | wc -l)
```

New:
```bash
WORKTREE_COUNT=$(git worktree list | grep -c "openspec/" || true)
```

- [ ] **Step 6: Replace line 1168 (`REMAINING_WT`)**

Old:
```bash
REMAINING_WT=$(git worktree list | awk '$2 ~ /^openspec\// {print $1}' | wc -l)
```

New:
```bash
REMAINING_WT=$(git worktree list | awk '$2 ~ /^openspec\// {print $1}' | grep -c . || true)
```

- [ ] **Step 7: Verify no `wc -l` remains in guide.md's path-counting code**

```bash
git grep -nE 'wc -l' skills/guide.md
```

Expected: zero matches in path-counting contexts (may still appear in valid contexts like `wc -l < known-file >` — review any remaining hits manually).

- [ ] **Step 8: Verify bash syntax of modified blocks**

Extract the modified bash blocks into a temp file and run `bash -n`:

```bash
awk '/^```bash$/,/^```$/' skills/guide.md > /tmp/guide_blocks.sh
bash -n /tmp/guide_blocks.sh
```

Expected: no syntax error.

- [ ] **Step 9: Commit**

```bash
git add skills/guide.md
git commit -m "fix(guide): replace wc -l with grep -c on potentially empty input (CODE_REVIEW #3)

Five sites in guide.md counted lines of possibly-empty command output
with 'wc -l', which returns 1 for empty input (counts trailing newline).
Replaced each with 'grep -c .' which returns 0 for empty input.

Lines fixed: 263, 286, 366, 919, 1168.
Lines 286 and 366 also now quote \$PROJECT_ROOT (CODE_REVIEW #5).

Closes CODE_REVIEW.md issue #3 in skills/guide.md."
```

---

## Task 1b: Fix `wc -l` on empty input in `execute.md`, `status.md`, `plan.md`, `propose.md` (5 more sites)

> **Why a separate task:** Task 1 covered only `guide.md` per the original plan. Baseline verification (Task 0) revealed 5 more `wc -l` sites in 4 other files. Bundling them into the Task 1 commit would mix concerns and bloat a single commit; a separate atomic commit keeps each fix independently revertable.

**Files:**
- Modify: `skills/execute.md:283`
- Modify: `skills/status.md:150, 294`
- Modify: `skills/plan.md:664`
- Modify: `skills/propose.md:611`

- [ ] **Step 1: Replace `execute.md:283` (`OTHER_WTS`)**

Old:
```bash
OTHER_WTS=$(git worktree list | awk '$2 ~ /^openspec\// && $2 != "openspec/'"$CHANGE_NAME"'" {print $1}' | wc -l)
```

New:
```bash
OTHER_WTS=$(git worktree list | awk '$2 ~ /^openspec\// && $2 != "openspec/'"$CHANGE_NAME"'" {print $1}' | grep -c . || true)
```

- [ ] **Step 2: Replace `status.md:150` (`WT_DIRTY`)**

Old:
```bash
    WT_DIRTY=$(cd "$WORKTREE_PATH" && git status --porcelain | wc -l)
```

New:
```bash
    WT_DIRTY=$(cd "$WORKTREE_PATH" && git status --porcelain | grep -c . || true)
```

- [ ] **Step 3: Replace `status.md:294` (`DIRTY`)**

Old:
```bash
    DIRTY=$(cd "$WORKTREE_PATH" && git status --porcelain | wc -l)
```

New:
```bash
    DIRTY=$(cd "$WORKTREE_PATH" && git status --porcelain | grep -c . || true)
```

- [ ] **Step 4: Replace `plan.md:664` (`UNPLANNED` count)**

Old:
```bash
done | wc -l)
```

New:
```bash
done | grep -c . || true)
```

- [ ] **Step 5: Replace `propose.md:611` (`UNCOMMITTED`)**

Old:
```bash
UNCOMMITTED=$(git status --porcelain openspec/changes/ 2>/dev/null | wc -l)
```

New:
```bash
UNCOMMITTED=$(git status --porcelain openspec/changes/ 2>/dev/null | grep -c . || true)
```

- [ ] **Step 6: Verify no `wc -l` in path-counting contexts remains in those files**

```bash
git grep -nE 'wc -l' skills/execute.md skills/status.md skills/plan.md skills/propose.md
```

Expected: zero matches.

- [ ] **Step 7: Verify bash syntax of modified blocks**

```bash
for f in skills/execute.md skills/status.md skills/plan.md skills/propose.md; do
    echo "=== $f ==="
    awk '/^```bash$/,/^```$/' "$f" > /tmp/check.sh
    bash -n /tmp/check.sh && echo "  OK"
done
```

Expected: every file reports "OK".

- [ ] **Step 8: Commit**

```bash
git add skills/execute.md skills/status.md skills/plan.md skills/propose.md
git commit -m "fix(execute,status,plan,propose): replace wc -l with grep -c on empty input (CODE_REVIEW #3)

Five more sites outside guide.md counted lines of possibly-empty
output with 'wc -l' (returns 1 for empty input). Replaced with
'grep -c .' which returns 0 for empty input.

Files fixed:
- skills/execute.md:283 (OTHER_WTS)
- skills/status.md:150 (WT_DIRTY), :294 (DIRTY)
- skills/plan.md:664 (UNPLANNED count)
- skills/propose.md:611 (UNCOMMITTED)

Closes CODE_REVIEW.md issue #3 in remaining files."
```

---

## Task 2: Fix unquoted `$PROJECT_ROOT` in `guide.md` (4 remaining locations)

**Files:**
- Modify: `skills/guide.md:815, 905, 1029, 1254`

- [ ] **Step 1: Read each of the 4 lines to confirm context**

```bash
sed -n '815p;905p;1029p;1254p' skills/guide.md
```

Expected: 4 lines, each containing unquoted `$PROJECT_ROOT`.

- [ ] **Step 2: Replace line 815**

Old:
```bash
echo "❌ 目录冲突，请先清理: rm -rf $PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}"
```

New:
```bash
echo "❌ 目录冲突，请先清理: rm -rf \"$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}\""
```

- [ ] **Step 3: Replace lines 905 AND 1029 (identical content — use `replaceAll`)**

Old (appears on both lines):
```bash
echo "   cd $(pwd)/$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}"
```

New (appears on both lines):
```bash
echo "   cd $(pwd)/\"$PROJECT_ROOT/.rddf/wt/${CHANGE_NAME}\""
```

Use the `edit` tool with `replaceAll: true` so both occurrences are updated in a single call.

- [ ] **Step 5: Replace line 1254**

Old:
```bash
rm -f $PROJECT_ROOT/workflow-state.md $PROJECT_ROOT/workflow-progress.md
```

New:
```bash
rm -f "$PROJECT_ROOT/workflow-state.md" "$PROJECT_ROOT/workflow-progress.md"
```

- [ ] **Step 6: Verify no unquoted `$PROJECT_ROOT` expansions remain in guide.md**

```bash
git grep -nE '(echo|rm|cd|mkdir|cp|mv|ls) [^|"]*[^"]\$PROJECT_ROOT' skills/guide.md
```

Expected: zero matches. (If a line legitimately needs `$PROJECT_ROOT` unquoted for variable expansion in shell — e.g., assignment — that's fine, but command invocations should quote.)

- [ ] **Step 7: Verify bash syntax of modified blocks**

```bash
awk '/^```bash$/,/^```$/' skills/guide.md > /tmp/guide_blocks.sh
bash -n /tmp/guide_blocks.sh
```

Expected: no syntax error.

- [ ] **Step 8: Commit**

```bash
git add skills/guide.md
git commit -m "fix(guide): quote \$PROJECT_ROOT in path arguments (CODE_REVIEW #5)

Four command lines in guide.md passed unquoted \$PROJECT_ROOT to
echo/rm/cd, breaking when the project root path contains spaces.
Each invocation now double-quotes the path argument.

Lines fixed: 815, 905, 1029, 1254.

Closes CODE_REVIEW.md issue #5 in skills/guide.md."
```

---

## Task 3: Fix worktree listing word-splitting in `guide.md` (2 locations)

**Files:**
- Modify: `skills/guide.md:947-948, 1244-1245`

- [ ] **Step 1: Read both blocks**

```bash
sed -n '945,955p;1242,1252p' skills/guide.md
```

Expected: both blocks contain `for wt in $(git worktree list | grep "openspec/" | awk '{print $1}')`.

- [ ] **Step 2: Replace lines 947-948 (block in 上下文 section)**

Old:
```bash
for wt in $(git worktree list | grep "openspec/" | awk '{print $1}'); do
    branch=$(git worktree list | grep "$wt" | awk '{print $3}')
```

New:
```bash
mapfile -t wt_list < <(git worktree list --porcelain | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}')
for wt in "${wt_list[@]}"; do
    branch=$(git worktree list | grep -F "$wt" | awk '{print $3}')
```

The new awk reads the `--porcelain` block format: it captures the path on a `worktree` line, and prints it when the matching `branch` line starts with `refs/heads/openspec/`. (The previous draft checked the path itself for `openspec/`, which was a logic error — `openspec/` lives in the branch name, not the path.)

- [ ] **Step 3: Replace lines 1244-1245 (cleanup block)**

Old:
```bash
for wt in $(git worktree list | grep "openspec/" | awk '{print $1}'); do
    git worktree remove "$wt" 2>/dev/null || true
done
```

New:
```bash
mapfile -t wt_list < <(git worktree list --porcelain | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}')
for wt in "${wt_list[@]}"; do
    git worktree remove "$wt" 2>/dev/null || true
done
```

New:
```bash
mapfile -t wt_list < <(git worktree list --porcelain | awk '/^worktree / {path=$2} /^branch / {if (path ~ /openspec\//) print path; path=""}')
for wt in "${wt_list[@]}"; do
    branch=$(git worktree list | grep -F "$wt" | awk '{print $3}')
```

- [ ] **Step 3: Replace lines 1244-1245 (cleanup block)**

Old:
```bash
for wt in $(git worktree list | grep "openspec/" | awk '{print $1}'); do
    git worktree remove "$wt" 2>/dev/null || true
done
```

New:
```bash
mapfile -t wt_list < <(git worktree list --porcelain | awk '/^worktree / {path=$2} /^branch / {if (path ~ /openspec\//) print path; path=""}')
for wt in "${wt_list[@]}"; do
    git worktree remove "$wt" 2>/dev/null || true
done
```

- [ ] **Step 4: Verify bash syntax of modified blocks**

```bash
awk '/^```bash$/,/^```$/' skills/guide.md > /tmp/guide_blocks.sh
bash -n /tmp/guide_blocks.sh
```

Expected: no syntax error.

- [ ] **Step 5: Commit**

```bash
git add skills/guide.md
git commit -m "fix(guide): use mapfile + --porcelain for worktree paths with spaces (CODE_REVIEW #11)

Two for-loops parsed 'git worktree list' with \$(... | awk '{print \$1}'),
which word-splits on whitespace. Paths containing spaces (common on
macOS, e.g. /Users/First Last/proj) get truncated.

Switched to 'git worktree list --porcelain' with mapfile + a stateful
awk parser. Both blocks are now safe for paths with spaces.

Lines fixed: 947-948, 1244-1245.

Closes CODE_REVIEW.md issue #11 in skills/guide.md."
```

---

## Task 4: Fix `git branch -d` unmerged-commit handling in `guide.md` (2 locations)

**Files:**
- Modify: `skills/guide.md:1158, 1250`

- [ ] **Step 1: Read both lines**

```bash
sed -n '1156,1160p;1248,1252p' skills/guide.md
```

- [ ] **Step 2: Replace line 1158**

Old:
```bash
git branch -d "openspec/$CHANGE_NAME"
```

New:
```bash
if git branch -d "openspec/$CHANGE_NAME" 2>/dev/null; then
    echo "✅ Branch 已删除: openspec/$CHANGE_NAME"
else
    echo "⚠️  Branch 有未合并的提交，强制删除"
    git branch -D "openspec/$CHANGE_NAME"
fi
```

- [ ] **Step 3: Replace line 1250**

Old:
```bash
git branch -d "$branch" 2>/dev/null || true
```

New:
```bash
if git branch -d "$branch" 2>/dev/null; then
    :
else
    echo "⚠️  Branch $branch 有未合并的提交，强制删除"
    git branch -D "$branch" 2>/dev/null || true
fi
```

- [ ] **Step 4: Verify bash syntax of modified blocks**

```bash
awk '/^```bash$/,/^```$/' skills/guide.md > /tmp/guide_blocks.sh
bash -n /tmp/guide_blocks.sh
```

Expected: no syntax error.

- [ ] **Step 5: Commit**

```bash
git add skills/guide.md
git commit -m "fix(guide): handle unmerged commits in git branch -d (CODE_REVIEW #34)

Two sites ran 'git branch -d' without a fallback. The lowercase -d
fails on branches with unmerged commits, leaving stale branches
behind after archive.

Replaced with a try -d / fallback to -D pattern, matching the same
defensive pattern already used in status.md.

Lines fixed: 1158, 1250.

Closes CODE_REVIEW.md issue #34 in skills/guide.md."
```

---

## Task 5: Align guide.md merge pattern with status.md

**Files:**
- Modify: `skills/guide.md:1115-1118`

- [ ] **Step 1: Read the block**

```bash
sed -n '1110,1120p' skills/guide.md
```

Expected: 5-line block starting with `if ! git merge --ff-only "openspec/$CHANGE_NAME"`.

- [ ] **Step 2: Replace the block**

Old:
```bash
if ! git merge --ff-only "openspec/$CHANGE_NAME" 2>/dev/null; then
    echo "⚠️ ff-only merge 失败，尝试普通 merge..."
    git merge "openspec/$CHANGE_NAME" || { echo "❌ merge 失败"; exit 1; }
fi
```

New (aligned with `status.md:323-330`):
```bash
MERGE_BASE=$(git merge-base "openspec/$CHANGE_NAME" "$DEFAULT_BRANCH" 2>/dev/null)
MAIN_TIP=$(git rev-parse "$DEFAULT_BRANCH" 2>/dev/null)
if [ "$MERGE_BASE" = "$MAIN_TIP" ]; then
    git merge --ff-only "openspec/$CHANGE_NAME" || { echo "❌ merge 失败"; exit 1; }
else
    echo "⚠️ Worktree 分支已落后于 $DEFAULT_BRANCH，创建 merge commit"
    git merge --no-ff "openspec/$CHANGE_NAME" -m "merge: $CHANGE_NAME change" || { echo "❌ merge 失败"; exit 1; }
fi
```

- [ ] **Step 3: Verify bash syntax of modified blocks**

```bash
awk '/^```bash$/,/^```$/' skills/guide.md > /tmp/guide_blocks.sh
bash -n /tmp/guide_blocks.sh
```

Expected: no syntax error.

- [ ] **Step 4: Commit**

```bash
git add skills/guide.md
git commit -m "fix(guide): align merge pattern with status.md divergence check (CODE_REVIEW #32)

guide.md used 'if ! git merge --ff-only; then git merge' which
silently downgrades to a plain merge commit without -m, producing
an auto-generated default message. status.md already implements
the proper divergence-aware pattern (merge-base check → --ff-only
or --no-ff -m 'merge: ...'). Ported that pattern to guide.md.

Lines fixed: 1115-1118.

Closes CODE_REVIEW.md issue #32 in skills/guide.md."
```

---

## Task 6: Fix `mktemp /tmp/...` hardcoded /tmp

**Files:**
- Modify: `skills/execute.md:376`
- Modify: `skills/status.md:212`

- [ ] **Step 1: Read both lines**

```bash
sed -n '375,377p' skills/execute.md
echo "---"
sed -n '211,213p' skills/status.md
```

- [ ] **Step 2: Replace `execute.md:376`**

Old:
```bash
TMPFILE=$(mktemp /tmp/tasks_XXXXXX.md)
```

New:
```bash
TMPFILE=$(mktemp -t tasks_XXXXXX.md)
```

- [ ] **Step 3: Replace `status.md:212`**

Old:
```bash
TMPFILE=$(mktemp /tmp/status_tasks_XXXXXX.md)
```

New:
```bash
TMPFILE=$(mktemp -t status_tasks_XXXXXX.md)
```

- [ ] **Step 4: Verify no `mktemp /tmp/...` remains**

```bash
git grep -nE 'mktemp /tmp/' skills/ install.sh
```

Expected: zero matches.

- [ ] **Step 5: Verify bash syntax of modified blocks**

```bash
awk '/^```bash$/,/^```$/' skills/execute.md skills/status.md > /tmp/exec_status_blocks.sh
bash -n /tmp/exec_status_blocks.sh
```

Expected: no syntax error.

- [ ] **Step 6: Commit**

```bash
git add skills/execute.md skills/status.md
git commit -m "fix(execute,status): use mktemp -t for system temp dir (CODE_REVIEW #25)

Hardcoded '/tmp' in mktemp templates is less secure and may fail
on systems where /tmp is restricted or full. 'mktemp -t' uses
the system temp directory (TMPDIR or /tmp fallback) with the
same template semantics.

Files fixed: skills/execute.md:376, skills/status.md:212.

Closes CODE_REVIEW.md issue #25."
```

---

## Task 6b: Fix additional `mktemp /tmp/...` site in `execute.md` (line 392)

> **Why a separate task:** Task 6 covered only `execute.md:376` and `status.md:212`. Baseline verification (Task 0) found one more `mktemp /tmp/...` in `execute.md:392` (the batch-update path in the same file). Separate atomic commit, same rationale as Task 1b.

**Files:**
- Modify: `skills/execute.md:392`

- [ ] **Step 1: Replace `execute.md:392`**

Old:
```bash
TMPFILE=$(mktemp /tmp/tasks_XXXXXX.md)
```

New:
```bash
TMPFILE=$(mktemp -t tasks_XXXXXX.md)
```

- [ ] **Step 2: Verify no `mktemp /tmp/...` remains**

```bash
git grep -nE 'mktemp /tmp/' skills/ install.sh
```

Expected: zero matches.

- [ ] **Step 3: Verify bash syntax of modified block**

```bash
awk '/^```bash$/,/^```$/' skills/execute.md > /tmp/exec_blocks.sh
bash -n /tmp/exec_blocks.sh
```

Expected: no syntax error.

- [ ] **Step 4: Commit**

```bash
git add skills/execute.md
git commit -m "fix(execute): use mktemp -t for the batch-update TMPFILE (CODE_REVIEW #25)

The second mktemp call in execute.md (line 392, the awk batch-update
path) was missed by Task 6. Same fix: 'mktemp -t' uses the system
temp dir (TMPDIR or /tmp fallback) instead of hardcoding /tmp.

Closes CODE_REVIEW.md issue #25 in skills/execute.md:392."
```

---

## Task 7: Remove hardcoded `/workspace/project/CppHDL` fallback in `status.md`

**Files:**
- Modify: `skills/status.md:309`

- [ ] **Step 1: Read the line**

```bash
sed -n '307,311p' skills/status.md
```

- [ ] **Step 2: Replace line 309**

Old:
```bash
MAIN_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "/workspace/project/CppHDL")
```

New:
```bash
MAIN_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$MAIN_ROOT" ]; then
    echo "❌ 无法确定项目根目录（不在 git 仓库内？）"
    exit 1
fi
```

- [ ] **Step 3: Verify no hardcoded `/workspace/project/CppHDL` remains**

```bash
git grep -nE '/workspace/project/CppHDL' skills/ install.sh
```

Expected: zero matches.

- [ ] **Step 4: Verify bash syntax of modified block**

```bash
awk '/^```bash$/,/^```$/' skills/status.md > /tmp/status_blocks.sh
bash -n /tmp/status_blocks.sh
```

Expected: no syntax error.

- [ ] **Step 5: Commit**

```bash
git add skills/status.md
git commit -m "fix(status): remove hardcoded /workspace/project/CppHDL fallback (CODE_REVIEW #28)

status.md fell back to '/workspace/project/CppHDL' when 'git rev-parse
--show-toplevel' returned empty, silently using a wrong directory.
The fallback masked errors and broke for any user with a different
project path.

Replaced with explicit error and exit 1 when project root cannot
be determined.

Closes CODE_REVIEW.md issue #28 in skills/status.md."
```

---

## Task 7b: Remove hardcoded `/workspace/project/CppHDL` in `execute.md` and `guide.md` (2 more sites)

> **Why a separate task:** Task 7 covered only `status.md:309`. Baseline verification (Task 0) found two more hardcoded paths: `execute.md:271` (inside the execute script's user-facing output) and `guide.md:1014` (inside a markdown code block showing what the execute session does).

**Files:**
- Modify: `skills/execute.md:271`
- Modify: `skills/guide.md:1014`

- [ ] **Step 1: Replace `execute.md:271` (echo in user-facing output)**

Old:
```bash
echo "   cd /workspace/project/CppHDL"
```

New (use the already-defined `$PROJECT_ROOT`):
```bash
echo "   cd \"$PROJECT_ROOT\""
```

- [ ] **Step 2: Replace `guide.md:1014` (in a documentation code block)**

Old:
```bash
cd /workspace/project/CppHDL
```

New (compute the project root dynamically — works for any user, any project path):
```bash
cd "$(git rev-parse --show-toplevel)"
```

> The original hardcoded path assumed every user works at `/workspace/project/CppHDL`. The replacement resolves the project root via git, so the instruction works regardless of where the project lives.

- [ ] **Step 3: Verify no hardcoded `/workspace/project/CppHDL` remains**

```bash
git grep -nE '/workspace/project/CppHDL' skills/ install.sh
```

Expected: zero matches.

- [ ] **Step 4: Verify bash syntax of modified blocks**

```bash
for f in skills/execute.md skills/guide.md; do
    echo "=== $f ==="
    awk '/^```bash$/,/^```$/' "$f" > /tmp/check.sh
    bash -n /tmp/check.sh && echo "  OK"
done
```

Expected: every file reports "OK".

- [ ] **Step 5: Commit**

```bash
git add skills/execute.md skills/guide.md
git commit -m "fix(execute,guide): replace hardcoded /workspace/project/CppHDL path (CODE_REVIEW #28)

Two more sites had the hardcoded path that Task 7 missed:

- skills/execute.md:271 — user-facing output telling the user to
  'cd' to the project root for archiving. Now uses the in-script
  \$PROJECT_ROOT variable.
- skills/guide.md:1014 — markdown code block showing what the
  execute session does (return to project root). Now uses
  'git rev-parse --show-toplevel' to resolve the project root
  dynamically, working for any user.

Closes CODE_REVIEW.md issue #28 in remaining files."
```

---

## Task 8: Final Validation

- [ ] **Step 1: Re-run negative regression grep (after-state)**

```bash
git grep -nE 'wc -l|\$\(.*\)\s*-\s*gt 0|for wt in \$\(git worktree list' skills/ install.sh
git grep -nE 'mktemp /tmp/|/workspace/project/CppHDL' skills/ install.sh
```

Expected: zero matches across all four patterns.

- [ ] **Step 2: Verify all modified files pass `bash -n`**

```bash
for f in skills/guide.md skills/execute.md skills/status.md skills/plan.md skills/propose.md; do
    echo "=== $f ==="
    awk '/^```bash$/,/^```$/' "$f" > /tmp/check.sh
    bash -n /tmp/check.sh && echo "  OK"
done
```

Expected: every file reports "OK".

- [ ] **Step 3: Confirm 9 commits on top of the spec**

```bash
git log --oneline 50c4bbb..HEAD
```

Expected: 9 commits, each starting with `fix(`, referencing a CODE_REVIEW number.

- [ ] **Step 4: Confirm no other files were modified**

```bash
git diff --stat 50c4bbb..HEAD
```

Expected: only `skills/guide.md`, `skills/execute.md`, `skills/status.md`, `skills/plan.md`, `skills/propose.md` show changes. Total: 5 files.

- [ ] **Step 5: Show the commit log**

```bash
git log --oneline -15
```

Expected: spec commit `50c4bbb` + plan commit `d29049c` + 9 fix commits.

---

## Out-of-Scope (deliberately deferred per spec)

The following `CODE_REVIEW.md` items are **not** fixed in this plan (and were verified to be either already fixed or not in the spec scope):

- Medium #14, #16, #17, #18, #19, #20, #21, #22, #23, #24
- Low #26, #27, #30
- Logic #33, #35, #36
- Inconsistency #37, #38, #39, #40

These will be revisited in a future spec once the Critical+High pass stabilises.
