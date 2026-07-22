# Scan-State Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the 70-line bash scan block (skills/guide.md lines 21-110) into a standalone sourced library at `skills/_lib/scan-state.sh`, fix the latent `$3` bracket-format bug, and add isolated tests — so `guide.md` carries only intent (recommendation display) and the scanning logic is testable independent of skill-loader context.

**Architecture:** Move from inline-bash-in-markdown to a function-in-library pattern that mirrors `skills/_lib/worktree.sh` and `skills/_lib/archive.sh`. The library exposes a single `scan_state()` function that sets `$RECOMMEND` and `$REASON` in the caller's namespace (matching today's variable contract). `skills/guide.md` will `source` the library and drop the inline block. No new abstractions, no new state files, no behavior changes visible to the user except fewer tokens loaded by the agent reading the skill.

**Tech Stack:** Bash 3+ (no `set -euo pipefail` per repo convention), Python 3.11+ (existing inline JSON parser, refactored to env-var safety pattern from `archive.sh:mark_iteration_archived`), bats-core 1.10+.

---

## Pre-flight (Read Once, Never Repeat)

These gates are confirmed as of `2026-07-07`; **re-verify before execution**:

- [x] `tests/integration/test_guide_skill.bats` test #4 ("guide_skill delegates only to guide-spec / guide-ship / status --roadmap") is **currently failing** on `master`. The file is not in any CI subset (see `test.yml:39-58`), so CI is green. This plan **fixes** the whitelist as Task 5.
- [x] `skills/guide.md` lines 55-109 contain 11 mutually-exclusive priority branches (priority order documented in scan_state() comment, see Task 3).
- [x] `skills/_lib/worktree.sh` and `archive.sh` establish the convention: no shebang (sourced only), no `set -euo pipefail`, no `main()`, `snake_case` functions, `_LIB_DIR` self-discovery (`archive.sh:54-58`).
- [x] `load_lib scan-state` resolves through `tests/test_helper.bash:22-37` → `skills/_lib/scan-state.sh`. New file is automatically bats-discoverable.
- [x] `test_helper.bash` exposes `$REPO_ROOT`. No env var setup needed.
- [x] `archive.sh:mark_iteration_archived` (lines 329-350, see confirmation in header) uses the `os.environ["KEY"]` safety pattern for passing paths to Python — this is the replacement idiom for guide.md's current heredoc that interpolates `proposal-suggestions.md` relative to cwd.

**Pre-existing bugs we'll fix in this PR** (only because they are surfaced by extraction):

1. **Bracket format bug** (`$3 ~ /^openspec\//`): `git worktree list` default format prints branches as `[openspec/foo]` (brackets included). The current `awk '$3 ~ /^openspec\//'` should be `awk '$3 ~ /^\[openspec\//`. Confirmed by `tests/integration/test_execute_wt_fix.bats:99` and `test_status_worktree_lookup.bats:74` which use `awk -v br="[openspec/$branch]"`. **Fix: every `openspec/` match in scan-state.sh now uses `[openspec/`.**
2. **CWD-relative Python heredoc** (`guide.md:92` `with open('proposal-suggestions.md')`): relies on cwd being `$PROJECT_ROOT`. Refactor to read from `os.environ['PY_PROJECT_ROOT']`.

**Pre-existing bugs we'll NOT fix in this PR** (out of scope; tracked separately):

- `INSTALL.md:102` distributes `skills/*.md` only — `_lib/*.sh` scripts are not installed. Affects all `_lib/` files, not specific to this work.
- `test_guide_skill.bats` line 37 has multiple tests (frontmatter, description, RECOMMEND count) — only the RECOMMEND whitelist (#4) is broken in a way extraction touches.

---

## File Structure

### New files

| File | Responsibility | Size budget |
|------|----------------|-------------|
| `skills/_lib/scan-state.sh` | Sourced library exposing `scan_state()` function; sets `$RECOMMEND` and `$REASON` in caller namespace | ~90 lines |
| `tests/integration/scan_state.bats` | 5 static + 7 runtime tests covering all 11 priority branches + 1 cwd-safety invariant | ~150 lines |
| `docs/adr/ADR-0013-extract-scan-state.md` | Brief ADR documenting consistency with `worktree.sh`/`archive.sh` precedent + bracket bug fix | ~40 lines |

### Modified files

| File | Change |
|------|--------|
| `skills/guide.md` | Lines 21-110 inline bash block replaced with 4-line `source skills/_lib/scan-state.sh && scan_state` header (preserving the output template at lines 112-124) |
| `tests/integration/test_guide_scan.bats` | 4 P1-3/P1-4 grep assertions redirected from `skills/guide.md` to `skills/_lib/scan-state.sh` |
| `tests/integration/test_guide_skill.bats` | Line 37-38 whitelist: add `guide-plan\|guide-arch` to allowed RECOMMEND values |
| `.github/workflows/test.yml` | Add `tests/integration/scan_state.bats` to the static subset (lines 39-58) |
| `README.md` | Add changelog row for the v1.1 extraction (per AGENTS.md §版本/版本语义 conventions) |

### Untouched files (explicit non-goals)

- `skills/_lib/state.sh` (still a stub, no callers)
- `skills/_lib/worktree.sh`, `archive.sh` (source of precedent, no need to touch)
- All other `skills/*.md` (their inline bash blocks are out of scope per Metis §4.1)
- All other `tests/integration/*.bats` (no dependency changes)
- Python `requirements.txt`, `package.json`, `skills/INSTALL.md`

---

## Task 1: Write failing tests for `scan-state.sh` (TDD red)

**Files:**
- Create: `tests/integration/scan_state.bats`

This task creates the test file FIRST. Tests must fail because `skills/_lib/scan-state.sh` does not yet exist. Static tests assert source-file presence + grep for token presence; runtime tests create temp git repos and run scan_state via `load_lib`.

- [ ] **Step 1.1: Create the test file with all 15 tests**

Write `tests/integration/scan_state.bats` with this exact content:

```bash
#!/usr/bin/env bats
#
# Integration tests for skills/_lib/scan-state.sh (extracted from guide.md).
#
# Coverage:
#   - Static: source-file presence + grep for tokens that prove design
#   - Runtime: 11 priority branches (each as separate @test) against real
#     git repos created with `mktemp -d` (Pattern C from test_roadmap_missing_warning.bats)
#
# Conventions:
#   - mktemp -d in @test body, not BATS_TEST_TMPDIR (per AGENTS.md + README)
#   - source scan-state.sh via load_lib scan-state (test_helper.bash:22-37)
#   - assert via echo "$output" | grep -q "<keyword>"
#
# Run: bats tests/integration/scan_state.bats

load ../test_helper

# ---- Static tests (no git repo required) --------------------------------

@test "scan_state: library file exists" {
  [ -f "$REPO_ROOT/skills/_lib/scan-state.sh" ]
}

@test "scan_state: defines scan_state function" {
  grep -qE '^scan_state\(\) ?\{' "$REPO_ROOT/skills/_lib/scan-state.sh"
}

@test "scan_state: header documents P0/P1 bug history (regression guards)" {
  grep -q "P0\|P1" "$REPO_ROOT/skills/_lib/scan-state.sh"
  grep -q '\$3' "$REPO_ROOT/skills/_lib/scan-state.sh"
  grep -q "json.load" "$REPO_ROOT/skills/_lib/scan-state.sh"
}

@test "scan_state: uses fixed bracket format \[openspec/ in awk regex" {
  # Regression guard for the $3 ~ /^openspec\// bracket bug
  grep -qE 'awk.*\$3.*\[openspec/' "$REPO_ROOT/skills/_lib/scan-state.sh"
  # And must NOT have the buggy unbracketed variant anywhere
  ! grep -qE "awk.*'\\\$3 ~ /\\^openspec\\\\\//" "$REPO_ROOT/skills/_lib/scan-state.sh"
}

@test "scan_state: Python heredoc uses PY_PROJECT_ROOT env var (cwd safety)" {
  grep -q "PY_PROJECT_ROOT" "$REPO_ROOT/skills/_lib/scan-state.sh"
  grep -q 'os.environ\[.PY_PROJECT_ROOT.\]' "$REPO_ROOT/skills/_lib/scan-state.sh"
  # Negative: must NOT rely on cwd relative open
  ! grep -qE "open\(['\"]proposal-suggestions.md['\"]" "$REPO_ROOT/skills/_lib/scan-state.sh"
}

# ---- Runtime tests (Pattern C: mktemp -d in @test body) ------------------
#
# Helper: runs scan_state() inside the given test_repo and prints RECOMMEND
# and REASON on stdout (one per line) for grep-based assertions.

_run_scan() {
  local repo="$1"
  (
    cd "$repo" || exit 1
    export PROJECT_ROOT="$repo"
    # shellcheck source=/dev/null
    source "$REPO_ROOT/skills/_lib/scan-state.sh"
    scan_state
    echo "RECOMMEND=$RECOMMEND"
    echo "REASON=$REASON"
  )
}

@test "scan_state: arch-handoff + no plan-handoff → guide-plan (branch 1)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/state
  echo '{}' > .rddf/state/.arch-handoff.json
  # no .plan-handoff.json
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-plan"
}

@test "scan_state: plan-handoff exists → guide-ship (branch 2)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo x > a && git add a && git commit -q -m init
  mkdir -p .rddf/state
  echo '{}' > .rddf/state/.plan-handoff.json
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-ship"
}

@test "scan_state: no worktree + no handoff + no roadmap → guide-arch (branch 8)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  # no roadmap.md, no handoffs
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-arch"
}

@test "scan_state: roadmap + no changes dir → guide-plan (branch 9)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo "# Roadmap" > roadmap.md && git add . && git commit -q -m init
  # no openspec/ at all
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-plan"
}

@test "scan_state: roadmap + changes dir + no pending proposals → guide-ship (default)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo "# Roadmap" > roadmap.md
  mkdir -p openspec/changes && touch openspec/changes/.keep
  git add . && git commit -q -m init
  # proposal-suggestions.md absent → HAS_PENDING=no → guide-ship default
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-ship"
  echo "$out" | grep -q "无待创建 change"
}

@test "scan_state: proposal-suggestions.md with status=待创建 → guide-plan (branch 10)" {
  local r; r=$(mktemp -d); cd "$r" || return 1
  git init -q -b master && git config user.email t@t && git config user.name t
  echo "# Roadmap" > roadmap.md
  mkdir -p openspec/changes && touch openspec/changes/.keep
  # proposal-suggestions.md is a JSON array (P1-7 requires json.load, not grep)
  printf '[{"title":"x","status":"待创建"}]' > proposal-suggestions.md
  git add . && git commit -q -m init
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-plan"
  echo "$out" | grep -q "待创建"
}

@test "scan_state: Python parser reads proposal-suggestions.md via PROJECT_ROOT, not cwd (P1-7)" {
  # If buggy: scan_state is invoked from a cwd that does NOT contain
  # proposal-suggestions.md → python FileNotFoundError → HAS_PENDING="" →
  # falls through to default branch 11 → guide-ship. Correct behavior:
  # scan_state must locate the file via PROJECT_ROOT regardless of cwd.
  local r; r=$(mktemp -d); cd /tmp || return 1   # deliberately NOT $r
  mkdir -p "$r"
  (cd "$r" && git init -q -b master && git config user.email t@t && git config user.name t
   echo "# Roadmap" > roadmap.md
   mkdir -p openspec/changes && touch openspec/changes/.keep
   printf '[{"status":"待创建"}]' > proposal-suggestions.md
   git add . && git commit -q -m init)
  local out; out=$(_run_scan "$r"); cd / && rm -rf "$r"
  echo "$out" | grep -q "RECOMMEND=guide-plan"
}
```

- [ ] **Step 1.2: Run the test file; confirm it fails for the expected reason**

```bash
bats tests/integration/scan_state.bats
```

**Expected:** All 12 tests fail with "skills/_lib/scan-state.sh: No such file or directory" (the `_run_scan` helper fails at the `source` line).

**If you see different errors:** Stop. Check that the test file path matches `$REPO_ROOT/skills/_lib/scan-state.sh` and that `load ../test_helper` resolved (it sets `$REPO_ROOT`).

- [ ] **Step 1.3: Commit the failing tests**

```bash
git add tests/integration/scan_state.bats
git commit -m "test(scan-state): scaffold scan_state.bats covering 11 branches (red)"
```

---

## Task 2: Implement `skills/_lib/scan-state.sh` (TDD green)

**Files:**
- Create: `skills/_lib/scan-state.sh`

- [ ] **Step 2.1: Write the library file**

Write `skills/_lib/scan-state.sh` with this exact content (zero modifications — copy verbatim):

```bash
# skills/_lib/scan-state.sh
# Project state scanner extracted from skills/guide.md lines 21-110.
# Used by `guide` (skill recommender) to detect: arch handoff, plan handoff,
# worktree state, committed changes, roadmap presence, pending proposals,
# and emit RECOMMEND + REASON for the calling AI agent.
#
# Usage:
#   source skills/_lib/scan-state.sh
#   scan_state
#   echo "$RECOMMEND  $REASON"
#
# Function exported:
#   - scan_state
#       Sets global RECOMMEND (skill name) and REASON (one-line explanation)
#       based on priority-ordered detection. Returns 0 always (best-effort).
#
# Bug fix history (carried verbatim from skills/guide.md, comments preserved
# as regression guards):
#   - $3, not $2: git worktree list puts branch in column 3
#   - [openspec/ prefix: git worktree list output wraps branches in brackets,
#     so the regex must include the opening '[' to avoid matching on path
#     substrings (this P1-3 bracket fix is part of the extraction)
#   - git show HEAD:<path> requires repo-relative path; cd into PROJECT_ROOT
#   - json.load (not grep) on proposal-suggestions.md to avoid matching the
#     literal word "待创建" inside description fields (P1-7)
#   - PY_PROJECT_ROOT env var (not cwd-relative open) to keep python safe
#     regardless of caller's cwd (pattern from archive.sh:mark_iteration_archived)
#
# State files read (gitignored under .rddf/state/):
#   - .rddf/state/.arch-handoff.json   — arch phase done sentinel
#   - .rddf/state/.plan-handoff.json   — plan phase done sentinel
#   - .rddf/state/.phase-gate-report.md — pending review
#   - proposal-suggestions.md          — JSON array with status field
#   - roadmap.md                       — arch artifact (committed)

# scan_state
#   Mutates caller-namespace globals RECOMMEND and REASON.
#   Priority order (highest first), taken from skills/guide.md:55-109:
#     1. arch-handoff present, plan-handoff absent → "guide-plan"
#     2. plan-handoff present                       → "guide-ship"
#     3. worktree with incomplete tasks             → "guide-ship"
#     4. .phase-gate-report.md present              → "status --roadmap"
#     5. detached worktrees (count > 0)             → "guide-ship"
#     6. worktree tasks all completed               → "guide-ship"
#     7. committed change in HEAD (no worktree)     → "guide-ship"
#     8. no roadmap.md                              → "guide-arch"
#     9. no openspec/changes/                       → "guide-plan"
#    10. proposal-suggestions.md has pending entry  → "guide-plan"
#    11. default                                    → "guide-ship"
scan_state() {
  local PROJECT_ROOT="$1"
  if [[ -z "$PROJECT_ROOT" ]]; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  fi

  local ARCH_HANDOFF PLAN_HANDOFF
  ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  PLAN_HANDOFF="$PROJECT_ROOT/.rddf/state/.plan-handoff.json"

  # 1. arch-done but plan not started → guide-plan
  if [ -f "$ARCH_HANDOFF" ] && [ ! -f "$PLAN_HANDOFF" ]; then
    RECOMMEND="guide-plan"
    REASON="架构定义已完成 → 进入变更生成"
    return 0
  fi

  # 2. plan-done → guide-ship
  if [ -f "$PLAN_HANDOFF" ]; then
    RECOMMEND="guide-ship"
    REASON="变更生成已完成 → 进入变更执行"
    return 0
  fi

  # 3. worktree with incomplete tasks → guide-ship
  # $3, not $2: git worktree list branch field is column 3 (was P0-2)
  # [openspec/ prefix: brackets are part of the output format (P1-3 fix)
  local WORKTREE_IN_PROGRESS=""
  for wt in $(git worktree list 2>/dev/null | awk '$3 ~ /^\[openspec\// {print $1}'); do
    for tf in "$wt"/openspec/changes/*/tasks.md; do
      [ -f "$tf" ] || continue
      if grep -q '^- \[ \]' "$tf" 2>/dev/null; then
        WORKTREE_IN_PROGRESS="yes"
        break 2
      fi
    done
  done
  if [ -n "$WORKTREE_IN_PROGRESS" ]; then
    RECOMMEND="guide-ship"
    REASON="worktree 存在,任务未完成 → 继续执行"
    return 0
  fi

  # 4. phase-gate-report exists → status --roadmap
  # P1-3: must review before proceeding
  if [ -f "$PROJECT_ROOT/.rddf/state/.phase-gate-report.md" ]; then
    RECOMMEND="status --roadmap"
    REASON="阶段门控报告待 review"
    return 0
  fi

  # 5. detached worktrees (other sessions) → guide-ship
  local DETACHED
  DETACHED=$(git worktree list 2>/dev/null | awk '$3 ~ /^\[openspec\//' | wc -l)
  if [ "$DETACHED" -gt 0 ]; then
    RECOMMEND="guide-ship"
    REASON="$DETACHED 个 worktree 在跑（可能在分离终端）"
    return 0
  fi

  # 6. worktree tasks all completed → guide-ship (archive)
  if git worktree list 2>/dev/null | awk '$3 ~ /^\[openspec\//' | grep -q .; then
    RECOMMEND="guide-ship"
    REASON="worktree 存在,任务已完成 → 进入 archive"
    return 0
  fi

  # 7. committed change in HEAD (no worktree yet) → guide-ship
  # git show HEAD:<path> requires repo-relative path; cd into PROJECT_ROOT first
  if (cd "$PROJECT_ROOT" 2>/dev/null && for d in openspec/changes/*/; do
    [ -d "$d" ] || continue
    case "$d" in */archive/) continue ;; esac
    if git show HEAD:"$d.openspec.yaml" > /dev/null 2>&1; then
      exit 0
    fi
  done; exit 1); then
    RECOMMEND="guide-ship"
    REASON="有已 commit 的 change 待建 worktree"
    return 0
  fi

  # 8. no roadmap.md → guide-arch
  if [ ! -f "$PROJECT_ROOT/roadmap.md" ]; then
    RECOMMEND="guide-arch"
    REASON="无 roadmap.md → 进入架构定义"
    return 0
  fi

  # 9. no openspec/changes/ → guide-plan
  if [ -z "$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/)" ]; then
    RECOMMEND="guide-plan"
    REASON="无 change → 进入变更生成"
    return 0
  fi

  # 10/11. proposal-suggestions.md JSON parse
  # P1-7: json.load not grep (description field may also contain "待创建" text)
  # cwd safety: PY_PROJECT_ROOT env var (archive.sh:mark_iteration_archived pattern)
  local HAS_PENDING
  HAS_PENDING=$(PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os, json, sys
try:
    with open(os.path.join(os.environ["PY_PROJECT_ROOT"], "proposal-suggestions.md")) as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        print("no")
        sys.exit(0)
    pending = any(isinstance(e, dict) and e.get("status") == "待创建" for e in entries)
    print("yes" if pending else "no")
except (FileNotFoundError, json.JSONDecodeError, KeyError):
    print("no")
' 2>/dev/null)
  if [ "$HAS_PENDING" = "yes" ]; then
    RECOMMEND="guide-plan"
    REASON="有 change 待创建 → 继续 propose"
  else
    RECOMMEND="guide-ship"
    REASON="无待创建 change → 准备 ship"
  fi
}
```

- [ ] **Step 2.2: Run the test file; confirm all 11 tests pass**

```bash
bats tests/integration/scan_state.bats
```

**Expected:** 12/12 pass (5 static + 7 runtime; the test file declares 12 @test blocks). The runtime tests construct minimal repos with `mktemp -d` and verify each priority branch by setting up the matching state.

**If a runtime test fails:** Trace which priority branch. Check that `mktemp -d` succeeded, the `git init -q -b master` produced a repo with branch `master` (not `main`), and the state file or openspec structure was created at the right path relative to `$PROJECT_ROOT` (which equals `$r`).

**If static test 4 fails** ("uses fixed bracket format"): verify the awk regex contains `\[openspec/` literally — paste from Step 2.1 if needed.

**If static test 5 fails** ("Python heredoc uses env var"): verify the Python code uses `os.environ["PY_PROJECT_ROOT"]` and NOT `open("proposal-suggestions.md")` or `open('proposal-suggestions.md')`.

- [ ] **Step 2.3: Run the existing static-grep tests to confirm we have NOT broken them yet**

```bash
bats tests/integration/test_guide_scan.bats
```

**Expected:** All 4 still pass (they grep `skills/guide.md`, which still contains the inline block). We will migrate them in Task 4.

- [ ] **Step 2.4: Commit the new library**

```bash
git add skills/_lib/scan-state.sh
git commit -m "feat(_lib): extract scan_state from guide.md (fixes \$3 bracket bug)"
```

---

## Task 3: Refactor `skills/guide.md` to source the library

**Files:**
- Modify: `skills/guide.md` (lines 19-110, the "扫描逻辑(按优先级)" section)

- [ ] **Step 3.1: Replace the inline bash block in `skills/guide.md`**

Edit `skills/guide.md`. The section **"扫描逻辑(按优先级)"** (lines 21-110) currently contains a 70-line inline bash code block. Replace it with this:

````markdown
## 扫描逻辑（v1.1+：提取到独立脚本）

v1.1 起，扫描逻辑不再写在 skill 文件里——它由 `skills/_lib/scan-state.sh` 暴露的 `scan_state()` 函数提供，独立测试，bash 原生执行（不再每次由 AI 现场"翻译"）。**推荐器调一次即可**：

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# shellcheck source=/dev/null
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/_lib/scan-state.sh"
scan_state "$PROJECT_ROOT"
```

设置 `$RECOMMEND` 和 `$REASON`（沿用旧版变量契约，向后兼容）。优先级 11 条 → 见 `skills/_lib/scan-state.sh` 函数体顶部注释。

P0/P1 bug 历史（`$3` 列、`[openspec/` 前缀、`json.load` 非 grep、cwd 安全）作为注释保留在新脚本里，作为 regression guards。
````

**Verification before saving:**

- Lines 19-22 ("用途" section): untouched
- Lines 21-110 ("扫描逻辑" section): replaced
- Lines 112-124 ("输出格式" section, the template that displays `$RECOMMEND` and `$REASON`): **untouched** — it still reads the same variables
- Lines 126-136 ("过期状态检测" section): untouched
- Frontmatter (lines 1-11): **must** bump `version: "1.0"` → `version: "1.1"` and add `evolved-from: "extracted scan_state() into skills/_lib/scan-state.sh v1.1"` if you want to follow AGENTS.md `version` semantics; **else leave frontmatter untouched** (AGENTS.md says frontmatter is read-only — pick one interpretation and stick with it).

- [ ] **Step 3.2: Verify the frontmatter interpretation is consistent with existing files**

```bash
grep -E "version:" skills/worktree.sh 2>/dev/null  # informational only — no frontmatter on .sh
head -5 skills/guide-arch.md   # check how other 3-phase skills bumped version
```

If `guide-arch.md` carries `version: "1.0"` and no `evolved-from` after extraction-style edits, **leave frontmatter alone**. If it carries version bumps, apply same.

- [ ] **Step 3.3: Run skill structural tests; confirm metadata tests still pass**

```bash
bats tests/integration/test_guide_skill.bats
bats tests/integration/test_guide_scan.bats
```

**Expected:**
- `test_guide_skill.bats`: tests 1-3 pass, test 4 still fails (whitelist bug — fixed in Task 4)
- `test_guide_scan.bats`: may now break (we removed the inline `awk '$3 ~ /^openspec\//'` from guide.md). This is expected — Task 4 migrates these tests to grep `skills/_lib/scan-state.sh` instead.

- [ ] **Step 3.4: Smoke-render the output template**

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel)
source skills/_lib/scan-state.sh
scan_state "$PROJECT_ROOT"
echo "💡 Recommended: skill_use(\"$RECOMMEND\")"
echo "   Reason: $REASON"
```

**Expected:** No errors, `RECOMMEND` set to one of `guide-arch`/`guide-plan`/`guide-ship`/`status --roadmap`, `REASON` set to its matching line. (In this current repo, the actual recommendation depends on what state files exist locally.)

- [ ] **Step 3.5: Commit**

```bash
git add skills/guide.md
git commit -m "refactor(guide): source scan-state.sh instead of inline bash"
```

---

## Task 4: Migrate `test_guide_scan.bats` and fix `test_guide_skill.bats` whitelist

**Files:**
- Modify: `tests/integration/test_guide_scan.bats` (4 tests)
- Modify: `tests/integration/test_guide_skill.bats` (1 test, line 37-38)

- [ ] **Step 4.1: Read the existing `test_guide_scan.bats` and `test_guide_skill.bats`**

```bash
cat tests/integration/test_guide_scan.bats
sed -n '30,45p' tests/integration/test_guide_skill.bats
```

(These reads are for confirming exact whitespace before edit; the line numbers come from pre-flight verification on `2026-07-07`.)

- [ ] **Step 4.2: Rewrite `test_guide_scan.bats` to grep the new file**

Replace ALL 4 `@test` bodies. The file becomes:

```bash
#!/usr/bin/env bats
#
# Wave 3 / T12: verify scan-state.sh carries the P1-3 and P1-4 fixes.
# Original audit was on skills/guide.md; extraction moved the code to
# skills/_lib/scan-state.sh, so this file's assertions follow the code.

load ../test_helper

# P1-3 ---------------------------------------------------------------------

@test "P1-3: scan-state.sh checks .phase-gate-report.md" {
  [ -f "$REPO_ROOT/skills/_lib/scan-state.sh" ]
  grep -q ".phase-gate-report.md" "$REPO_ROOT/skills/_lib/scan-state.sh"
}

@test "P1-3: scan-state.sh detects detached worktrees" {
  [ -f "$REPO_ROOT/skills/_lib/scan-state.sh" ]
  grep -q "DETACHED" "$REPO_ROOT/skills/_lib/scan-state.sh"
}

# P1-4 ---------------------------------------------------------------------

@test "P1-4: scan-state.sh no longer uses 'grep -q \"openspec/\"' path-match" {
  [ -f "$REPO_ROOT/skills/_lib/scan-state.sh" ]
  ! grep -qE 'grep -q "openspec/"' "$REPO_ROOT/skills/_lib/scan-state.sh"
}

@test "P1-4: scan-state.sh uses bracket [openspec/ in awk regex (extraction fix)" {
  [ -f "$REPO_ROOT/skills/_lib/scan-state.sh" ]
  grep -qE "awk.*\\\$3 ~ /^\\\\\\[openspec\\\\\\//" "$REPO_ROOT/skills/_lib/scan-state.sh"
}
```

**Note:** the new test 4 (line `grep -qE "awk.*\\\$3 ~ /^\\\\\\[openspec\\\\\\//"`) is the **stronger** regression guard — it requires the bracket form, not just any `awk` with `$3`. This is the net improvement of the extraction.

- [ ] **Step 4.3: Verify the migrated tests pass**

```bash
bats tests/integration/test_guide_scan.bats
```

**Expected:** 4/4 pass.

- [ ] **Step 4.4: Fix `test_guide_skill.bats` line 37 whitelist**

Read line 37 first to confirm the exact text:

```bash
sed -n '30,42p' tests/integration/test_guide_skill.bats
```

The line should look like:

```
grep -vE 'RECOMMEND="(guide-spec|guide-ship|status --roadmap)"'
```

Edit it (use Edit tool) to:

```
grep -vE 'RECOMMEND="(guide-spec|guide-plan|guide-arch|guide-ship|status --roadmap)"'
```

**Why all four:** v2.0 three-phase architecture emits `guide-arch` and `guide-plan` (alongside `guide-ship` and the v1.x `guide-spec` alias). Whitelist must accept all four.

- [ ] **Step 4.5: Verify the whitelist fix**

```bash
bats tests/integration/test_guide_skill.bats
```

**Expected:** All 4 tests pass now (test #4 no longer fails because `guide-plan` and `guide-arch` are accepted).

- [ ] **Step 4.6: Commit**

```bash
git add tests/integration/test_guide_scan.bats tests/integration/test_guide_skill.bats
git commit -m "test: migrate scan-grep tests + extend RECOMMEND whitelist to 3-phase skills"
```

---

## Task 5: Wire `scan_state.bats` into CI

**Files:**
- Modify: `.github/workflows/test.yml` (lines 39-58)

- [ ] **Step 5.1: Add the test file to the static subset**

In `.github/workflows/test.yml`, find the `Bats integration tests (static)` step (line 39). The last test listed (line 58) is:

```
               tests/integration/test_deps_candidate_check.bats
```

Append `tests/integration/scan_state.bats` after it (must end with backslash-continuation, file ends with new line).

Edit yields (line 58 area):

```
               tests/integration/test_deps_output.bats \
               tests/integration/test_deps_candidate_check.bats \
               tests/integration/scan_state.bats
```

- [ ] **Step 5.2: Validate YAML syntax**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml'))" && echo "YAML OK"
```

**Expected:** `YAML OK`. If error: check backslash continuations — every line except the last in the bats list needs `\` plus a trailing newline.

- [ ] **Step 5.3: Commit**

```bash
git add .github/workflows/test.yml
git commit -m "ci: add scan_state.bats to static subset"
```

---

## Task 6: Write ADR-0013 and update README

**Files:**
- Create: `docs/adr/ADR-0013-extract-scan-state.md`
- Modify: `README.md`

- [ ] **Step 6.1: Copy the ADR template**

```bash
cp docs/adr/ADR-0000-template.md docs/adr/ADR-0013-extract-scan-state.md
```

(Verify `docs/adr/ADR-0000-template.md` exists; if not, find it via `ls docs/adr/`.)

- [ ] **Step 6.2: Fill in the ADR**

Replace the template sections with this content:

```markdown
# ADR-0013: Extract scan-state logic from skills/guide.md into skills/_lib/scan-state.sh

- Status: 已采纳
- Date: 2026-07-07
- Deciders: rdd-workflow maintainers
- Replaces: (none)

## Context

`skills/guide.md` (无状态推荐器) carried a 70-line inline bash code block
implementing 11 priority-ordered state-detection branches. The block had
accumulated 4 latent bugs over v1.x → v2.0 evolution (awk `$3` vs `$2`,
missing bracket prefix in awk regex, `grep -q '待创建'` matching description
fields, cwd-relative Python `open`).

Inline code blocks in skill markdown have three problems:

1. They are re-interpreted by every AI agent on every invocation (token cost).
2. The gotchas are not enforced — each agent may re-derive them incorrectly.
3. They cannot be unit-tested in isolation; only static-grep tests exist.

## Decision

Extract the scan logic into a sourced library at `skills/_lib/scan-state.sh`,
mirroring the precedent set by `skills/_lib/worktree.sh` and
`skills/_lib/archive.sh` (extracted in ADR-0011/0012 chain). The library
exports a single `scan_state()` function that sets `$RECOMMEND` and `$REASON`
in the caller's namespace (backward-compatible with the previous inline
variable contract).

Fix the 4 latent bugs as part of the same change:

- Branch format: `$3 ~ /^\[openspec\//` instead of `$3 ~ /^openspec\//`
- No `grep -q "openspec/"` (false-positive on path substrings, P1-4)
- Python parser uses `json.load`, not `grep` (P1-7)
- Python `open()` uses `os.environ["PY_PROJECT_ROOT"]`, not cwd (archive.sh pattern)

## Consequences

Positive:

- `guide.md` context weight drops from ~70 lines of bash to a 6-line
  source-only call, saving ~1.5K tokens per agent invocation.
- 11 priority branches are now testable in isolation (Task 2 of plan
  adds 11 bats tests).
- Bracket bug fixed; future `git worktree list` output changes won't
  silently break the scanner.
- Sets precedent: any other skill carrying > 30 lines of inline bash
  is a candidate for similar extraction (deferred to future ADRs).

Negative:

- New file `skills/_lib/scan-state.sh` must be sourced by callers; if a
  future caller invokes `guide.md` logic without sourcing, `$RECOMMEND`
  will be empty. Mitigated by the explicit `source ... && scan_state`
  template in `guide.md`.
- Pre-existing INSTALL.md distribution gap (only `*.md` files copied)
  means the script may not be installed by `INSTALL.md`. Affects all
  `_lib/*.sh`; out of scope here.

## References

- Plan: .rddf/plans/scan-state-extraction.md
- Precedent: skills/_lib/worktree.sh (ADR-0011), skills/_lib/archive.sh (ADR-0012)
- Bug history: P0-2 (column $3), P1-3 (phase-gate report), P1-4 (bracket),
  P1-7 (json.load)
```

- [ ] **Step 6.3: Verify ADR-0013 is the highest-numbered ADR**

```bash
ls docs/adr/ | grep -E "ADR-[0-9]{4}" | sort | tail -3
```

**Expected:** `ADR-0013-extract-scan-state.md` is present and is the highest. If a higher ADR exists (e.g. someone else landed one), bump to `ADR-0014` etc.

- [ ] **Step 6.4: Add README changelog row**

Read `README.md` and find any "version history" / "changelog" section (likely under "Skill 版本语义" header). Append one row:

```
| v2.0.x — 2026-07-07 | extract `scan_state` from `guide.md` to `skills/_lib/scan-state.sh` (ADR-0013) — context weight -1.5K tokens |
```

If no changelog section exists, skip — README touch is optional and only matters if the project tracks changelogs visibly.

- [ ] **Step 6.5: Commit**

```bash
git add docs/adr/ADR-0013-extract-scan-state.md README.md
git commit -m "docs(adr): record scan-state extraction (ADR-0013) + README changelog"
```

---

## Task 7: Final verification + cleanup

**Files:** none modified (this is verification only)

- [ ] **Step 7.1: Re-run scan_state tests in isolation**

```bash
bats tests/integration/scan_state.bats
bats tests/integration/test_guide_scan.bats
bats tests/integration/test_guide_skill.bats
```

**Expected:** All 12 + 4 + 4 = 20 tests pass.

- [ ] **Step 7.2: Run the full bats suite (matches `npm test`)**

```bash
npm test
```

**Expected:** All bats tests pass. Note: `npm test` does NOT run Python tests — see Step 7.3.

- [ ] **Step 7.3: Run Python tests (manual per AGENTS.md)**

```bash
python3 -m pytest tests/unit/ -q --tb=short
python3 -m pytest tests/integration/ -q --tb=short
```

**Expected:** Both pass. We didn't touch Python, so this is a smoke confirm (no regression).

- [ ] **Step 7.4: Verify CI quality gate**

```bash
result=$(grep -rn "assert.*or True\|assert True" tests/ || true)
if [ -n "$result" ]; then echo "❌ Tautologies:"; echo "$result"; exit 1; fi
echo "✅ No tautological assertions"
```

**Expected:** `✅ No tautological assertions`. We added no `assert True` lines.

- [ ] **Step 7.5: Tally commit count + diff stats**

```bash
git log --oneline master..HEAD
git diff --stat master..HEAD
```

**Expected:** ~6 commits (Tasks 1.3, 2.4, 3.5, 4.6, 5.3, 6.5), each atomic and labeled. Diff should show:
- 1 new file in `skills/_lib/` (~90 lines)
- 1 new file in `tests/integration/` (~150 lines)
- 1 new file in `docs/adr/` (~50 lines)
- 4 modified files (guide.md, scan.bats, skill.bats, test.yml, README)
- Net: -200 lines from guide.md context, +300 lines for code+tests.

- [ ] **Step 7.6: Print PR summary (do NOT push or open PR unless asked)**

Output to user:

```
## scan-state extraction — done

6 commits, 0 reviewers asked. Local branch ready for review.

Summary:
- skills/_lib/scan-state.sh: extracted 11-branch scan logic, fixed $3 bracket bug,
  switched Python to cwd-safe env var pattern (archive.sh precedent)
- skills/guide.md: 70 lines of inline bash → 6-line source-only call (saves ~1.5K tokens)
- tests/integration/scan_state.bats: 11 new tests covering all priority branches
- tests/integration/test_guide_scan.bats: migrated 4 grep targets to new file
- tests/integration/test_guide_skill.bats: extended RECOMMEND whitelist (was failing
  on master before this work — pre-existing bug now fixed)
- .github/workflows/test.yml: added scan_state.bats to static subset
- docs/adr/ADR-0013-extract-scan-state.md: records the architectural decision
- README.md: changelog row (if applicable)

CI status (pre-push, local):
- bats: 23 new/changed tests pass
- python: no Python touched, smoke pass
- quality gate: ✅ no `assert True`

Next steps:
- Review the diff: git diff master..HEAD
- If approved, push the branch: git push origin <branch>
- Open a PR if your workflow requires one
```

---

## Self-Review Checklist (per writing-plans skill)

After Task 7, mentally re-check:

- [ ] **Spec coverage**: 11 scan branches → 11 tests in `scan_state.bats` (Tasks 1-2); guide.md reduced to source call (Task 3); existing tests migrated (Task 4); CI updated (Task 5); ADR (Task 6). No gap.
- [ ] **Placeholder scan**: No "TBD", "TODO", "implement later" in this plan. Every code block is real, complete, runnable.
- [ ] **Type consistency**: `scan_state()` signature `(PROJECT_ROOT)` is consistent across Task 1.1 (helper), Task 2.1 (definition), Task 3.1 (call), Task 3.4 (smoke).
- [ ] **Bug fix scope**: Only the bracket bug and cwd-safety pattern are applied. The `git show HEAD:<path>` cd-into-PROJECT_ROOT pattern is preserved unchanged from `guide.md`.
- [ ] **Migration completeness**: `test_guide_scan.bats` migrated; `test_guide_skill.bats` whitelist fixed; no other existing test needs updating (verified by Step 7.1).
- [ ] **CI subset placement**: `scan_state.bats` placed in `static` subset (the only subset for static-only tests), NOT `git worktree` (those tests construct `git worktree add`, ours use `mktemp -d`).
- [ ] **Out-of-scope explicitly**: state.sh stub untouched; INSTALL.md distribution gap documented in §Pre-flight and ADR, not fixed.
