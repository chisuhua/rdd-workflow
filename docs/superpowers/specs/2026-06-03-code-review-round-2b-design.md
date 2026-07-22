# CODE_REVIEW Round 2b — Inconsistency Alignment

**Date:** 2026-06-03
**Status:** Approved (user decisions captured 2026-06-03)
**Scope:** 3 Inconsistency items from `CODE_REVIEW.md` (`#37`, `#38`, `#40`).
**Predecessor:** Round 1 + Round 2a already pushed to origin/master.

---

## 1. User Decisions

| # | Question | Decision |
|---|---|---|
| 37 | Skill name standardization | **Unify to `rdd-workflow-*`** (matches package name, npx install path) |
| 38 | `PROJECT_ROOT` definition | **Standard pattern**: `git rev-parse --show-toplevel 2>/dev/null \|\| pwd` (9 mainstream sites) |
| 40 | `workflow-state.md` format | **guide.md is authoritative** (more detailed; has "阶段完成情况" phase table) |

## 2. Goals

1. Land 3 atomic commits, one per inconsistency item.
2. Zero behavioural change to the OpenSpec state machine.
3. After Round 2b, a `git grep` for the now-deprecated patterns returns zero matches in skills/ and USAGE.md.

## 3. Files In Scope

| File | Issues | Notes |
|---|---|---|
| `USAGE.md` | #37, #40 | 10 `openrdd-workflow-*` refs to rename; 1 state format section to rewrite |
| `skills/guide.md` | #38 | 1 `PROJECT_ROOT=$(pwd)` outlier (line 162) |
| `skills/INSTALL.md` | #38 | 1 `PROJECT_ROOT=$(pwd)` in fallback block (line 60) |

Total: 3 files, 3 atomic commits.

## 4. The 3 Fixes

### Task B1 — Inconsistency #37: Unify skill names to `rdd-workflow-*`

**Scope:** `USAGE.md` lines 41, 175, 339, 353, 363, 372, 443, 444, 445, 446, 447.

The 10 references in USAGE.md use the deprecated `openrdd-workflow-*` prefix. All actual skill code in `skills/*.md` already uses `rdd-workflow-*`. The fix is a global text replace in USAGE.md only.

**Risk:** Documentation-only. No code change. Any user with custom scripts calling `skill_use("openrdd-workflow-...")` will need to update their calls, but USAGE.md is the source of truth for the canonical names.

### Task B2 — Inconsistency #38: Unify `PROJECT_ROOT` to the standard pattern

**Scope:** `skills/guide.md:162`, `skills/INSTALL.md:60`.

Two sites use bare `PROJECT_ROOT=$(pwd)` while the other 9 sites use `git rev-parse --show-toplevel 2>/dev/null || pwd`.

- `guide.md:162` is a clear outlier — same intent as the other sites, just different implementation.
- `INSTALL.md:60` is inside a conditional block that handles the "not a git repo" case. Replacing with the standard pattern is a no-op semantically (git rev-parse will fail again, pwd still wins), but makes the codebase consistent.

**Risk:** Low. The change in INSTALL.md is a no-op; the change in guide.md matches the 9-site pattern exactly.

### Task B3 — Inconsistency #40: Align `workflow-state.md` format to guide.md

**Scope:** `USAGE.md` lines ~380-420 (the "状态文件格式" section).

Current divergence:
- `guide.md` (authoritative): uses "工作流进度" + "阶段完成情况" table (phases: setup / propose / plan / execute / status_archive / cleanup)
- `USAGE.md` (to be updated): uses "当前状态" + "Changes（支持多 change 并行）" table (individual change tracking)

The `USAGE.md` "Changes" table contains information that IS useful (per-change worktree + progress), but it doesn't match the canonical schema. Per user decision, USAGE.md is rewritten to match guide.md's schema exactly. The per-change tracking is documented in `status.md` (Mode A) and doesn't need to be in the state-file format spec.

**Risk:** Documentation-only. State files written by the skill will continue to work (the format is loose — the skill writes the file structure it currently does, and consumers parse what they need).

## 5. Approach

1. **Per-fix commit.** Each of the 3 fixes lands as a single atomic commit.
2. **Mechanical text replacement** for #37 and #38; **schema rewrite** for #40.
3. **No new files.** USAGE.md is edited in place.
4. **No code change in skills/.** Only the 2 outlier `PROJECT_ROOT` lines in skills/ change, and the change is a no-op for INSTALL.md.

## 6. Validation

- `git grep "openrdd-workflow-"` → zero matches in `skills/` and `USAGE.md` (after B1)
- `git grep "PROJECT_ROOT=$(pwd)"` → zero matches (after B2)
- `git grep "状态文件格式"` → USAGE.md still has it but content matches guide.md's schema (after B3)
- `bash -n` on all modified files (USAGE.md has no bash blocks, so trivially OK)
- Commit log shows 3 new commits, each starting with `fix(scope):`

## 7. Commit Order

1. **B1** (USAGE.md rename) — mechanical, no risk, do first
2. **B2** (PROJECT_ROOT in skills/) — 2 sites in 2 files
3. **B3** (USAGE.md state format) — larger doc edit, do last

## 8. Out-of-Scope (deferred)

All other Medium/Low/Logic items from CODE_REVIEW.md that were not in Round 2a or Round 2b are either already fixed or deferred to a future round.

---

**Approval:** User chose:
- #37: "统一为 rdd-workflow-*（推荐）"
- #38: "git rev-parse ... || pwd（9 处主流，推荐）"
- #40: "以 guide.md 为准（更详尽）"
