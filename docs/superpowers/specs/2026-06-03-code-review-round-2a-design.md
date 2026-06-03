# CODE_REVIEW Round 2a — Mechanical Fixes

**Date:** 2026-06-03
**Status:** Approved
**Scope:** 10 mechanical fixes from `CODE_REVIEW.md` (Medium/Low/Logic only, no Inconsistency).
**Target Branch:** `master`
**Predecessor:** Round 1 spec/plan at commits `50c4bbb` / `d29049c` / `aef3279` (9 fix commits pushed).

---

## 1. Background

Round 1 landed 9 atomic commits addressing 7 real bugs in Critical+High categories. This round continues with the 10 items the user approved as "Round 2a: 10 项机械修复" — purely mechanical edits, zero API changes, no new dependencies, no Inconsistency items (those are deferred to Round 2b, which requires design decisions the user has not yet made).

## 2. Goals

1. Land 10 atomic commits, each fixing exactly one CODE_REVIEW item.
2. Zero behavioural change to the OpenSpec state machine or skill invocation API.
3. Each commit is independently revertable.
4. Pass bash syntax + negative-grep validation at the end.

## 3. Non-Goals

- No Inconsistency fixes (Round 2b — needs user decisions on skill names, PROJECT_ROOT convention, state-file format).
- No Medium items that require design judgment beyond mechanical replacement.
- No documentation rewrites beyond what each fix needs.

## 4. Files In Scope

CODE_REVIEW issue numbers below refer to `CODE_REVIEW.md`.

| File | Issues | Notes |
|---|---|---|
| `skills/guide.md` | #21 (2 sites), #22, #23, #36 | Largest file, 4 separate commits |
| `skills/status.md` | #35, #36, #21 (1 site) | 3 fixes |
| `skills/propose.md` | #36 | 1 fix |
| `skills/deps.md` | #16, #18 | 2 fixes, bash-specific patterns |
| `skills/plan.md` | #20, #21 (1 site) | 2 fixes |
| `skills/INSTALL.md` | #24 | 1 fix, security |
| `package.json` | #27 | 1 fix, structural (move git/cmake to engines) |

Total: 7 files, 10 distinct fixes (some commits bundle multiple sites of the same issue).

## 5. The 10 Fixes

**Task A1 — Medium #22:** `skills/guide.md:1012`
- Old: `cd "$WORKTREE_PATH"`
- New: `cd "$WORKTREE_PATH" || { echo "❌ 无法进入 worktree 目录"; exit 1; }`
- Rationale: avoid silent failure when worktree path is invalid.

**Task A2 — Medium #23:** `skills/guide.md:612`
- Old: `SCOPE_FILES=$(grep -E '^[ \t]*-[ \t]*('src/|file:)' "$proposal_path" 2>/dev/null | ...)`
- New: extract pattern to a variable, e.g.
  ```bash
  pattern='^[ \t]*-[ \t]*(src/|file:)'
  SCOPE_FILES=$(grep -E "$pattern" "$proposal_path" 2>/dev/null | ...)
  ```
- Rationale: avoid single-quote inside single-quoted regex (which currently silently truncates to `'^[ \t]*-[ \t]*('` and matches nothing useful).

**Task A3 — Logic #35:** `skills/status.md:314`
- Comment says "使用 subshell" but the `cd` runs in the main shell.
- New: either wrap in explicit subshell `(cd "$MAIN_ROOT" && ...)` or update the comment to clarify.
- Pragmatic fix: update the comment to match reality — the `cd` is intentional (we need to change directory in this shell), the subshell pattern was already used in earlier blocks.

**Task A4 — Logic #36:** 3 files
- `skills/guide.md:1193`: `grep -c "status: 待创建" "proposal-suggestions.md" ...`
- `skills/propose.md:657`: same pattern
- `skills/status.md:397`: same pattern
- New pattern (more robust to whitespace / `:` vs `=` separators):
  ```bash
  REMAINING=$(grep -ciE "status\s*[:=]\s*待创建" "proposal-suggestions.md" 2>/dev/null || echo "0")
  ```
- Same commit covers all 3 sites (they're the same pattern in 3 files).

**Task A5 — Medium #16:** `skills/deps.md:104`
- Old: `ADR_REFS=$(grep -oE 'ADR-[0-9]+' "$PROJECT_ROOT/..." 2>/dev/null | sort -u)`
- New: `ADR_REFS=$(grep -E 'ADR-[0-9]+' "$PROJECT_ROOT/..." 2>/dev/null | grep -o 'ADR-[0-9]*' | sort -u)`
- Rationale: `grep -oE` may behave differently on BSD grep (macOS). Two-step is portable.

**Task A6 — Medium #20:** `skills/plan.md:46`
- Old: `ls -d $PROJECT_ROOT/openspec/changes/*/ 2>/dev/null | sed 's#$PROJECT_ROOT/openspec/changes/##; s#/##'`
- New (also quote `$PROJECT_ROOT` to be safe):
  ```bash
  ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | \
      awk -F/ -v root="$PROJECT_ROOT" '{sub(root "/openspec/changes/", ""); sub(/\/$/, ""); print}'
  ```
- Rationale: `sed` substitution with unescaped `$PROJECT_ROOT` breaks if path contains `/` or `&`.

**Task A7 — Medium #21:** 4 sites of `git show HEAD:...`
- `skills/guide.md:477, 678, 800`
- `skills/plan.md:466`
- New: wrap with HEAD-exists guard:
  ```bash
  if git rev-parse --verify HEAD >/dev/null 2>&1; then
      committed=$(git show HEAD:"$path" > /dev/null 2>&1 && echo "✅" || echo "⏳")
  else
      committed="⏳"
  fi
  ```
- Same commit covers all 4 sites (same pattern).

**Task A8 — Medium #18:** `skills/deps.md:142, 145, 169, 192, 193`
- 5 sites of bash indirect expansion `${!var}`.
- New: convert to associative array (bash 4+) — single shared function for the pattern.
- Note: this is a larger refactor; the deps.md logic is the most complex in the package. If associative array proves too invasive, alternative is `eval` (carefully escaped) or temp files. Plan to use associative array.

**Task A9 — Medium #24:** `skills/INSTALL.md:175`
- Old: `curl -sL <raw-url>/install-spec-workflow.sh | bash`
- New (download then execute, with optional checksum verification):
  ```bash
  curl -sL -o /tmp/install-spec-workflow.sh <raw-url>/install-spec-workflow.sh
  # Optional: verify checksum here
  bash /tmp/install-spec-workflow.sh
  rm -f /tmp/install-spec-workflow.sh
  ```

**Task A10 — Low #27:** `package.json:12-13`
- Old: `git` and `cmake` listed under `dependencies`.
- New: move them to `engines` (system requirements, not npm packages).

## 6. Approach

1. **Per-fix commit.** Each of the 10 fixes lands as a single atomic commit.
2. **No new dependencies, no new files.** All fixes are local edits.
3. **No API change.** Skill names, command surface, file format unchanged.
4. **Backwards compatible.** Existing worktrees, branches, proposals continue to work.

## 7. Validation

Same as Round 1: bash syntax check on all modified bash blocks, negative grep for the fixed patterns, commit log review.

## 8. Risk & Rollback

- **Risk:** Low. All 10 items are mechanical replacements.
- **Rollback:** `git revert <sha>` per commit, or `git reset --hard <last-good-commit>`.

## 9. Commit Order

1. `package.json` (Task A10) — smallest, structural-only.
2. `skills/INSTALL.md` (Task A9) — security fix, isolated.
3. `skills/plan.md` (Tasks A6 + A21) — 2 fixes in same file, related.
4. `skills/deps.md` (Task A5) — grep portability.
5. `skills/deps.md` (Task A8) — bash indirect expansion (largest refactor).
6. `skills/status.md` (Task A3) — comment clarification.
7. `skills/guide.md` (Task A2) — grep quote nesting.
8. `skills/guide.md` (Task A1) — cd guard.
9. `skills/guide.md` + `skills/propose.md` + `skills/status.md` (Task A4) — 3 files, same pattern.
10. `skills/guide.md` + `skills/plan.md` (Task A7) — 2 files, same pattern.

**Note:** A3 and A6/A21 order is flexible. A8 (deps.md indirect expansion) is the riskiest and should land late so any earlier fixes don't conflict.

## 10. Out-of-Scope (Round 2b — needs user decisions)

- Inconsistency #37: skill name standardization (`spec-workflow-*` vs `openspec-workflow-*`)
- Inconsistency #38: `PROJECT_ROOT` definition (guide.md:162 uses `$(pwd)`, others use `git rev-parse ... || pwd`)
- Inconsistency #40: `workflow-state.md` format mismatch between guide.md and USAGE.md

These will be addressed in a separate spec after the user makes the design decisions.

---

**Approval:** User chose "轮 2a：10 项机械修复（推荐）" on 2026-06-03.
