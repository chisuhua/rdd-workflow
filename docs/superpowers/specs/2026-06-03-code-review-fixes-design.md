# Code Review Fixes — Design Spec

**Date:** 2026-06-03
**Status:** Approved
**Scope:** 15 issues (5 Critical + 10 High) from `CODE_REVIEW.md`
**Target Branch:** `master`

---

## 1. Background

`CODE_REVIEW.md` catalogues 42 quality issues across 8 skill files in this repository. The most severe items cause outright runtime failures (Python `SyntaxError`, broken shell variable interpolation, empty-path deletion risk). The user has approved fixing all **Critical (5)** and **High (10)** issues in this round. Medium/Low/Logic/Inconsistency issues are deferred to a future pass.

## 2. Goals

1. Eliminate every Critical bug that causes `SyntaxError`, broken script execution, or data-loss risk.
2. Make the skill package portable across GNU coreutils, BSD/macOS, and POSIX `sh`.
3. Preserve the existing user-facing workflow (no OpenSpec data-format changes, no API renames beyond the documented naming inconsistency).
4. Each issue is fixed in a single atomic commit referencing its `CODE_REVIEW.md` issue number.

## 3. Non-Goals

- No new external dependencies.
- No refactor of healthy code paths.
- No Medium/Low/Logic/Inconsistency fixes (deferred).
- No behavioural change to the OpenSpec state machine.

## 4. Files In Scope

Issue numbers below refer to `CODE_REVIEW.md` (e.g. "#1" = first Critical bug).

| File | Code Review Issues Addressed |
|---|---|
| `skills/propose.md` | #1 (f-string), #2 (shell-var-in-fstring) |
| `skills/execute.md` | #3 (wc -l), #5 (unquoted paths), #10 (nproc), #11 (worktree parse) |
| `skills/status.md` | #3 (wc -l), #4 (empty WT path), #5 (unquoted paths), #6 (jq arithmetic), #11 (worktree parse), #31 (branch-based detection) |
| `skills/guide.md` | #3 (wc -l), #5 (unquoted paths), #7 (grep regex injection), #11 (worktree parse), #31 (branch-based detection), #32 (merge --ff-only fallback), #34 (git branch -d) |
| `skills/plan.md` | #8 (portable stat) |
| `skills/INSTALL.md` | #9 (portable readlink) |
| `install.sh` | #12 (set -euo pipefail) |

Total: 8 files, 15 CODE_REVIEW items (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 31, 32, 34).

## 5. The 15 Fixes

### Critical (5)

**#1 — Python f-string quote nesting** — `skills/propose.md:93`
Change `print(f'  ...{', '.join(removed)}')` to `print(f"  ...{', '.join(removed)}")`. Impact: prevents `SyntaxError` when removing suggestions.

**#2 — Shell variable in Python f-string** — `skills/propose.md:81`
Replace `os.path.isdir(f'$PROJECT_ROOT/openspec/changes/{name}/')` with a shell-injected `PROJECT_ROOT` env var or string substitution. Impact: directory-existence check currently always returns `False`, causing incorrect retention of deleted suggestions.

**#3 — `wc -l` on empty input** — `execute.md:102`, `status.md:376`, `guide.md:268,310,850`
Replace `WORKTREE_COUNT=$(echo "$X" | wc -l)` with `WORKTREE_COUNT=$(printf '%s' "$X" | grep -c .)` or guard with `if [ -n "$X" ]`. Impact: `wc -l` returns 1 for empty input, breaking "any worktree exists?" checks.

**#4 — Empty `WORKTREE_PATH` validation** — `status.md:345,347`
Add explicit guard before `git worktree remove`:
```bash
if [ -n "$WORKTREE_PATH" ] && [ "$WORKTREE_PATH" != "/" ]; then
    git worktree remove "$WORKTREE_PATH"
fi
```
Impact: prevents deletion of an unintended directory if worktree list returns empty/malformed data.

**#5 — Unquoted variable expansions in path contexts** — `execute.md:94`, `guide.md:231,310`, `status.md:338`
Quote every `PROJECT_ROOT`, worktree path, and change name. Where iteration over `git worktree list` is needed, use `mapfile -t` instead of `for x in $(...)`. Impact: paths with spaces (common on macOS `/Users/First Last/`) break.

### High (10)

**#6 — `jq` output arithmetic validation** — `status.md:134`
Before `REMAINING=$((TOTAL - COMPLETE))`, validate with `[[ "$COMPLETE" =~ ^[0-9]+$ ]]`. Impact: `bash: null: syntax error` when `jq` returns "null" or empty.

**#7 — `grep` regex injection via `$PROJECT_ROOT`** — `guide.md:154`
Use `grep -qF` (fixed string) instead of `grep -q "^$PROJECT_ROOT"`. Impact: variable containing `.` is treated as regex; `project.CppHDL` matches anything.

**#8 — Portable `stat` for mtime** — `plan.md:72`
Wrap in a helper:
```bash
get_mtime() {
    stat -c %Y "$1" 2>/dev/null \
    || stat -f %m "$1" 2>/dev/null \
    || find "$1" -maxdepth 0 -printf '%T@\n' 2>/dev/null | cut -d. -f1
}
```
Impact: `stat -c` is GNU-specific; macOS uses `stat -f %m`.

**#9 — Portable `readlink -f`** — `INSTALL.md:83`
Use `realpath` if available, fall back to portable chain `(cd "$(dirname "$path")" && pwd -P)`. Impact: INSTALL skill fails on macOS.

**#10 — Portable `nproc`** — `execute.md:179,213`, `guide.md` (implied)
```bash
get_nproc() {
    command -v nproc >/dev/null 2>&1 && nproc \
    || sysctl -n hw.ncpu 2>/dev/null \
    || grep -c ^processor /proc/cpuinfo 2>/dev/null \
    || echo 4
}
```
Impact: build commands fail on macOS where `nproc` does not exist.

**#11 — `git worktree list` parsing for paths with spaces** — `execute.md:70,85,105`, `status.md:137,274`, `guide.md:692`
Switch to `git worktree list --porcelain` and parse block-format output. Impact: `awk '{print $1}'` truncates paths containing spaces.

**#12 — `set -euo pipefail`** — `install.sh:6`
Replace `set -e` with `set -euo pipefail`. Impact: missing `pipefail` silently swallows pipeline errors; missing `-u` allows unset-variable bugs.

**#13 — Branch-based worktree detection (logic)** — `guide.md:602,554`, `status.md:109`
Detect worktree by branch name (the last field) rather than path. Use `git worktree list --porcelain` + `grep "branch refs/heads/openspec/$NAME"`.

**#14 — `git merge --ff-only` fallback in guide.md** — `guide.md:833`
Port the fallback already present in `status.md:316-324`:
```bash
if [ "$(git merge-base openspec/$NAME main)" = "$(git rev-parse main)" ]; then
    git merge --ff-only "openspec/$NAME"
else
    git merge --no-ff "openspec/$NAME" -m "merge: $NAME change"
fi
```
Impact: `--ff-only` fails when main has moved forward; currently guide.md has no recovery.

**#15 — `git branch -d` unmerged-commit handling** — `guide.md:840`, `status.md:351`
Try `git branch -d` first; on failure, fall back to `git branch -D` with an explicit warning. Impact: cleanup aborts when worktree branch has unmerged commits.

## 6. Approach

1. **Per-issue commit.** Each of the 15 fixes lands as a single atomic commit with a message of the form:
   ```
   fix(<file>): <one-line summary> (CODE_REVIEW #<n>)

   <2-3 line body explaining the bug and the fix.>

   Closes CODE_REVIEW.md issue #<n>.
   ```
2. **No new dependencies.** All portability helpers use only POSIX `sh`/coreutils that ship everywhere. No `brew install`, no `apt install`.
3. **No API/format changes.** Helpers are inlined; the `openspec/` directory layout and `workflow-state.md` schema are untouched.
4. **Backwards compatible.** Existing worktrees and branches continue to work; the helpers degrade gracefully on older shells.

## 7. Validation

Before marking each commit done:

1. **Shell syntax** — `bash -n` on every modified script block (extracted via `awk`/`sed` from the markdown).
2. **Python syntax** — `python3 -c "compile(open('<file>.py').read(), '<file>', 'exec')"` on extracted Python blocks.
3. **Negative regression grep** — `git grep -nE 'wc -l|\$\(.*\)\s*-\s*gt 0|readlink -f|stat -c %Y' skills/` should return zero hits after the relevant fix.
4. **Smoke test** — run `openspec --version` then dry-load each modified skill via `skill_use` if the runtime supports it.
5. **Commit-time check** — `lsp_diagnostics` on modified files (if an LSP is configured for the language).

## 8. Risk & Rollback

- **Low risk:** each commit is atomic and the fix is local to a single file (or a few lines within a file).
- **Rollback:** `git revert <sha>` per commit, or `git reset --hard <last-good-commit>` for an all-at-once revert.
- **Skill cache:** global OpenCode skill caches may need clearing (`rm -rf ~/.cache/opencode/*` or equivalent) before the fixes take effect on the user's machine.

## 9. Commit Order

Commits are ordered to keep the tree in a runnable state after each one:

1. `install.sh` — `set -euo pipefail` (foundation for safe execution).
2. `INSTALL.md` — portable `readlink -f`.
3. `plan.md` — portable `stat`.
4. `execute.md`, `status.md`, `guide.md` — portable `nproc`.
5. `propose.md` — Python f-string + `$PROJECT_ROOT` interpolation.
6. `status.md` — `wc -l` and empty-`WORKTREE_PATH` fixes.
7. `execute.md`, `guide.md` — `wc -l` and unquoted variable fixes.
8. `status.md` — `jq` arithmetic validation.
9. `guide.md` — `grep -F` regex injection fix.
10. `execute.md`, `status.md`, `guide.md` — worktree porcelain parsing + branch detection.
11. `guide.md` — `git merge --ff-only` fallback + `git branch -d` handling.

## 10. Out-of-Scope (deferred)

The following `CODE_REVIEW.md` items are **not** addressed in this round:

- Medium-severity issues #14, #15, #16, #17, #18, #19, #20, #21, #22, #23, #24, #25.
- Low-severity issues #26, #27, #28, #29, #30.
- Logic issues #31, #33, #35, #36.
- Inconsistency issues #37 (skill naming), #38 (PROJECT_ROOT definition), #39 (set -e usage), #40 (state file format mismatch).

These will be revisited in a future spec once the Critical+High pass lands and stabilises.

---

**Approval:** User said "请修复" on 2026-06-03, accepting the proposed Critical+High scope.
