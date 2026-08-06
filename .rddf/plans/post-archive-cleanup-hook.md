# post-archive-cleanup-hook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a unified post-archive cleanup hook (`_lib/post_archive_cleanup.sh`) that idempotently clears working-tree residue (deleted tracked files, modified critical files) after `openspec archive`, eliminating the recurring "关键文件未提交" warning at next `guide` invocation.

**Architecture:** Single bash function `post_archive_cleanup <project_root> <change_name>` invoked from both `_lib/archive.sh::archive_change` (worktree mode) and `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode` (lightweight mode). Idempotent `git status --porcelain` scan + whitelist-driven `git rm`/`git add` + auto-commit (rm bucket only). Idempotent no-op when no residue.

**Tech Stack:** bash 4+, git, bats-core 1.10+ (existing project test runner)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/post_archive_cleanup.sh` | New — exported `post_archive_cleanup()` function: classify + apply + commit |
| `_lib/archive.sh` | Modify — call hook in `archive_change` after `cleanup_plan_file` (around line 340) |
| `skills/guide-ship/scripts/ship_archive.sh` | Modify — call hook in `archive_change_for_mode` after `cleanup_plan_file` (around line 248) |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_post_archive_cleanup_hook.bats` | New — 8 scenarios covering all GIVEN/WHEN/THEN from proposal + edge cases |

---

## Task 1: Test scaffolding — write all 8 bats scenarios FIRST

**Files:**
- Create: `tests/integration/test_post_archive_cleanup_hook.bats`

- [ ] **Step 1.1: Test file header + helper setup**

```bash
#!/usr/bin/env bats
# tests/integration/test_post_archive_cleanup_hook.bats
# Tests for _lib/post_archive_cleanup.sh
load test_helper

setup() {
  TEST_TMPDIR="$(mktemp -d)"
  export PROJECT_ROOT="$TEST_TMPDIR/fake-repo"
  mkdir -p "$PROJECT_ROOT"/{_lib,openspec/changes,openspec/specs,.rddf/state}
  cd "$PROJECT_ROOT"
  git init -q -b master
  git config user.email "test@example.com"
  git config user.name "Test"
  git commit --allow-empty -m "init" -q
  # Source the hook under test
  source "$BATS_TEST_DIRNAME/../../_lib/post_archive_cleanup.sh"
}
teardown() { rm -rf "$TEST_TMPDIR"; }

# helper: create a "deleted" file (tracked then deleted)
make_deleted() {
  local p="$1"
  mkdir -p "$(dirname "$p")"
  echo "x" > "$p"
  git add "$p"
  git commit -q -m "add"
  rm "$p"
}

# helper: create a modified file
make_modified() {
  local p="$1"
  mkdir -p "$(dirname "$p")"
  echo "x" > "$p"
  git add "$p"
  git commit -q -m "add"
  echo "y" >> "$p"
}
```

- [ ] **Step 1.2: Scenario 1 (basic deleted .rddf/plans/<n>.md)**

```bash
@test "hook: deletes-tracked .rddf/plans/<name>.md" {
  make_deleted ".rddf/plans/foo.md"
  run post_archive_cleanup "$PROJECT_ROOT" "foo"
  [ "$status" -eq 0 ]
  # Now git rm-ed; commit lands
  run git log --oneline
  [[ "$output" == *"chore(post-archive): clean residue from foo"* ]]
  run git status --porcelain
  [ -z "$output" ]
}
```

- [ ] **Step 1.3: Scenario 2 (idempotent re-run)**

```bash
@test "hook: idempotent — second run produces no extra commit" {
  make_deleted ".rddf/plans/foo.md"
  post_archive_cleanup "$PROJECT_ROOT" "foo"
  local commit_count_after_first
  commit_count_after_first=$(git rev-list --count HEAD)
  post_archive_cleanup "$PROJECT_ROOT" "foo"
  local commit_count_after_second
  commit_count_after_second=$(git rev-list --count HEAD)
  [ "$commit_count_after_second" -eq "$commit_count_after_first" ]
}
```

- [ ] **Step 1.4: Scenario 3 (dry-run mode)**

```bash
@test "hook: DRY_RUN=yes echoes but does not mutate" {
  make_deleted ".rddf/plans/foo.md"
  DRY_RUN_POST_ARCHIVE_CLEANUP=yes run post_archive_cleanup "$PROJECT_ROOT" "foo"
  # Echo present
  [[ "$output" == *"would git rm"* ]]
  # File still deleted-from-disk but untracked in git
  run git status --porcelain
  [[ "$output" == *" D .rddf/plans/foo.md"* ]]
  # No chore commit added
  run git log --oneline
  [[ "$output" != *"chore(post-archive)"* ]]
}
```

- [ ] **Step 1.5: Scenario 4 (skip escape)**

```bash
@test "hook: SKIP_POST_ARCHIVE_CLEANUP=yes early-returns 0" {
  make_deleted ".rddf/plans/foo.md"
  SKIP_POST_ARCHIVE_CLEANUP=yes run post_archive_cleanup "$PROJECT_ROOT" "foo"
  [ "$status" -eq 0 ]
  # Nothing changed
  run git status --porcelain
  [[ "$output" == *" D .rddf/plans/foo.md"* ]]
}
```

- [ ] **Step 1.6: Scenario 5 (whitelist boundary — tasks.md untouched)**

```bash
@test "hook: dirty tasks.md is NOT auto-committed" {
  make_modified "openspec/changes/foo/tasks.md"
  make_deleted ".rddf/plans/foo.md"
  post_archive_cleanup "$PROJECT_ROOT" "foo"
  # tasks.md still shows as modified (not staged, not committed by us)
  run git status --porcelain
  [[ "$output" == *" M openspec/changes/foo/tasks.md"* ]]
  # chore commit only contains the plan-file delete
  local head_commit_files
  head_commit_files=$(git show --name-only --pretty="" HEAD)
  [[ "$head_commit_files" == *".rddf/plans/foo.md"* ]]
  [[ "$head_commit_files" != *"tasks.md"* ]]
}
```

- [ ] **Step 1.7: Scenario 6 (modified proposal-approved.md is git-added, not committed)**

```bash
@test "hook: modified proposal-approved.md is staged but not auto-committed" {
  make_modified "proposal-approved.md"
  post_archive_cleanup "$PROJECT_ROOT" "foo"
  run git status --porcelain
  # 'M ' (second col space) means: index staged, worktree unchanged
  [[ "$output" == *"M  proposal-approved.md"* ]]
  # No chore commit at all (rm bucket empty)
  run git log --oneline
  [[ "$output" != *"chore(post-archive)"* ]]
}
```

- [ ] **Step 1.8: Scenario 7 (worktree mode smoke)**

```bash
@test "hook: works inside worktree (no main-repo state pollution)" {
  git worktree add .rddf/wt/foo -b foo openspec/foo 2>/dev/null || \
    git worktree add .rddf/wt/foo -b foo
  cd .rddf/wt/foo
  make_deleted ".rddf/plans/foo.md"
  post_archive_cleanup "$(pwd)" "foo"
  run git status --porcelain
  [ -z "$output" ]
  git worktree remove .rddf/wt/foo --force
}
```

- [ ] **Step 1.9: Scenario 8 (dual-mode replay — fix the real residue)**

```bash
@test "hook: cleans real-world residue (.rddf/plans/<existing>)" {
  # Simulates the bug from commit 9f31a68: archive left dangling plan file
  make_deleted ".rddf/plans/fix-rddf-init-broken-layout.md"
  run post_archive_cleanup "$PROJECT_ROOT" "fix-rddf-init-broken-layout"
  [ "$status" -eq 0 ]
  run git log --oneline
  [[ "$output" == *"chore(post-archive): clean residue from fix-rddf-init-broken-layout"* ]]
  run git status --porcelain
  [ -z "$output" ]
}
```

- [ ] **Step 1.10: Verify all tests fail**

Run: `bats tests/integration/test_post_archive_cleanup_hook.bats`
Expected: 8 failed (function `post_archive_cleanup` not defined → `"command not found"` exit 4 or similar)

---

## Task 2: Implement `_lib/post_archive_cleanup.sh`

**Files:**
- Create: `_lib/post_archive_cleanup.sh`

- [ ] **Step 2.1: Header + public function shell**

```bash
#!/usr/bin/env bash
# _lib/post_archive_cleanup.sh
#
# post_archive_cleanup <project_root> <change_name>
#
# Idempotent post-archive cleanup. After openspec archive <change_name>
# finishes moving files, this hook:
#   1. Scans `git status --porcelain` for residue
#   2. Classifies into 3 buckets: deleted-tracked (whitelist), modified-critical (whitelist),
#      other (untouched)
#   3. git rm -f deleted-tracked items
#   4. git add modified-critical items (does NOT auto-commit them)
#   5. Auto-commit only the rm bucket (commit subject: chore(post-archive): clean
#      residue from <change_name>); idempotent no-op when buckets empty
#
# Env vars:
#   SKIP_POST_ARCHIVE_CLEANUP=yes        — early-return 0 (escape hatch)
#   DRY_RUN_POST_ARCHIVE_CLEANUP=yes     — echo actions instead of running git
#
# Exit codes:
#   0 — always (idempotent / non-blocking)

set -uo pipefail

# Whitelist: deleted-tracked paths to git rm
_WHITELIST_DELETED_PATTERNS=(
  ".rddf/plans/"
  ".rddf/state/.arch-handoff.json.tmp"
  ".rddf/state/.plan-handoff.json.tmp"
)

# Whitelist: modified-critical paths to git add (staged, not committed)
_WHITELIST_MODIFIED_PATTERNS=(
  "proposal-approved.md"
  "proposal-suggestions.md"
  "roadmap.md"
)

# Check if a relative path matches any glob-style prefix in patterns.
_matches_prefix() {
  local path="$1"; shift
  for pat in "$@"; do
    case "$path" in
      ${pat}*) return 0 ;;
    esac
  done
  return 1
}

post_archive_cleanup() {
  local project_root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local change_name="${2:-}"
  local dry_run="${DRY_RUN_POST_ARCHIVE_CLEANUP:-no}"
  local skip="${SKIP_POST_ARCHIVE_CLEANUP:-no}"

  if [ "$skip" = "yes" ]; then
    echo "⏭️  post_archive_cleanup: SKIPPED (SKIP_POST_ARCHIVE_CLEANUP=yes)"
    return 0
  fi

  cd "$project_root" || { echo "❌ post_archive_cleanup: cannot cd to $project_root" >&2; return 1; }

  # Build maps of basename → paths matching each bucket
  local modified_to_add=()
  local deleted_to_rm=()

  while IFS= read -r line; do
    # porcelain v1 format: XY <path>
    # X = index status, Y = worktree status
    local x="${line:0:1}" y="${line:1:1}"
    local path="${line:3}"
    [ -z "$path" ] && continue

    # Strip leading "renamed: " / "copied: " etc. prefix if any (defensive)
    case "$x$y" in
      ' D')   # deleted in worktree, not staged
        if _matches_prefix "$path" "${_WHITELIST_DELETED_PATTERNS[@]}"; then
          deleted_to_rm+=("$path")
        fi
        ;;
      'M '|'A ')  # modified/added in index, worktree unchanged
        if _matches_prefix "$path" "${_WHITELIST_MODIFIED_PATTERNS[@]}"; then
          modified_to_add+=("$path")
        fi
        ;;
      'MM'|'AM'|' MD'|'MA')  # also modified in worktree
        if _matches_prefix "$path" "${_WHITELIST_MODIFIED_PATTERNS[@]}"; then
          modified_to_add+=("$path")
        fi
        ;;
    esac
  done < <(git status --porcelain)

  # Apply: git rm deleted bucket
  if [ "${#deleted_to_rm[@]}" -gt 0 ]; then
    if [ "$dry_run" = "yes" ]; then
      printf '   would git rm -f %s\n' "${deleted_to_rm[@]}"
    else
      git rm -f "${deleted_to_rm[@]}" 1>/dev/null
      printf '🧹 cleaned: %s\n' "${deleted_to_rm[@]}"
    fi
  fi

  # Apply: git add modified bucket (only staged, not committed)
  if [ "${#modified_to_add[@]}" -gt 0 ]; then
    if [ "$dry_run" = "yes" ]; then
      printf '   would git add %s\n' "${modified_to_add[@]}"
    else
      git add "${modified_to_add[@]}" 1>/dev/null
      printf '🧹 staged: %s\n' "${modified_to_add[@]}"
    fi
  fi

  # Commit only the rm bucket (not the modified — those stay for user commit)
  if [ "${#deleted_to_rm[@]}" -gt 0 ] && [ "$dry_run" != "yes" ]; then
    git commit -q -m "chore(post-archive): clean residue from ${change_name:-unknown}"
    echo "✅ committed chore(post-archive) for ${change_name:-unknown}"
  fi

  return 0
}
```

- [ ] **Step 2.2: Run all 8 bats tests**

Run: `bats tests/integration/test_post_archive_cleanup_hook.bats`
Expected: 8 passed (ALL green)

- [ ] **Step 2.3: Defer commit** — execute phase does not commit per change; archive aggregates

---

## Task 3: Wire into `_lib/archive.sh::archive_change`

**Files:**
- Modify: `_lib/archive.sh` (after the existing `cleanup_plan_file` call site; check `git diff` to find current location)

- [ ] **Step 3.1: Locate insertion point**

Run: `grep -n "cleanup_plan_file\|cleanup_plan_handoff\|commit_archive_moves" _lib/archive.sh`
Expected: see line numbers around 340-345

- [ ] **Step 3.2: Source the hook file at top of script**

Near the top of `_lib/archive.sh`, add (after other sourced libs):
```bash
# Source post-archive cleanup hook (post-archive-cleanup-hook)
if [ -f "$_PARENT_DIR/post_archive_cleanup.sh" ]; then
  source "$_PARENT_DIR/post_archive_cleanup.sh"
fi
```

- [ ] **Step 3.3: Call the hook after cleanup_plan_file**

Insert immediately after the existing `cleanup_plan_file` call (or in a similar cleanup-complete position):
```bash
post_archive_cleanup "$main_root" "$name" || true
```

- [ ] **Step 3.4: Defer commit**

---

## Task 4: Wire into `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode`

**Files:**
- Modify: `skills/guide-ship/scripts/ship_archive.sh` (after line 248 `cleanup_plan_file`)

- [ ] **Step 4.1: Source the hook file**

After the existing `cleanup_plan_file` source section, add:
```bash
# Source post-archive cleanup hook
_HL_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$_HL_SCRIPT_DIR/../../../_lib/post_archive_cleanup.sh" ]; then
  source "$_HL_SCRIPT_DIR/../../../_lib/post_archive_cleanup.sh"
fi
```

- [ ] **Step 4.2: Call hook after cleanup_plan_file**

Insert immediately after line 248 (`cleanup_plan_file "$project_root" "$change_name" || true`):
```bash
post_archive_cleanup "$project_root" "$change_name" || true
```

- [ ] **Step 4.3: Defer commit**

---

## Task 5: Document in AGENTS.md

**Files:**
- Modify: `AGENTS.md` (under "Worktree Commit Flow")

- [ ] **Step 5.1: Add hook call diagram**

Insert in the "Worktree Commit Flow" section, immediately after Step 2 (`git commit`) and before Phase 3 archive:

```markdown
2.5. **Post-archive cleanup hook (post-archive-cleanup-hook)** — 在 worktree 合并回 master 之前,自动 idempotent 清扫残留(deleted tracked `.rddf/plans/<name>.md` 等 + modified critical `proposal-approved.md`)。详见 `_lib/post_archive_cleanup.sh` 与 improvements/post-archive-cleanup-hook.md。SKIP via `SKIP_POST_ARCHIVE_CLEANUP=yes`;debug via `DRY_RUN_POST_ARCHIVE_CLEANUP=yes`。
```

- [ ] **Step 5.2: Defer commit**

---

## Task 6: Worktree commit (Phase 2.7)

**Files:**
- All above

- [ ] **Step 6.1: Aggregate commit**

Run (in worktree root):
```bash
git add -A
git commit -m "feat(archive): post-archive cleanup hook unifies working-tree hygiene

Implements improvements/post-archive-cleanup-hook.md. Adds
_lib/post_archive_cleanup.sh and wires it into both archive
modes (worktree + lightweight). Hook auto-runs after the
existing cleanup chain (cleanup_plan_file, commit_archive_moves)
to fix the 3-bug chain that left .rddf/plans/<name>.md
residues in working tree after archive.

8 bats tests cover idempotency, dry-run, skip escape,
whitelist boundary (tasks.md/ADR docs untouched), modified-only,
worktree mode, lightweight mode, and real-world residue
replay (the bug from commit 9f31a68).

Escape: SKIP_POST_ARCHIVE_CLEANUP=yes / DRY_RUN_POST_ARCHIVE_CLEANUP=yes."
```

- [ ] **Step 6.2: Verify commit**

Run: `git log -1 --oneline`
Expected: single feat(archive) commit listing all new/modified files

---

## Self-Review Checklist (pre-archive)

- [ ] All 8 bats scenarios pass
- [ ] No regressions: `bats tests/integration/test_ship_*.bats` 全绿
- [ ] No regressions: `pytest tests/unit/ tests/integration/` 全绿
- [ ] Both `_lib/archive.sh` and `ship_archive.sh` call the hook
- [ ] AGENTS.md "Worktree Commit Flow" updated
- [ ] Single aggregate commit on this branch

---

## Out of Scope

- `specs/<capability>/spec.md` for openspec validate — non-fatal warning,留 follow-up
- Generic "untracked build dir" cleanup — 留 follow-up
- Replacing `_lib/state.sh::check_dirty_key_files` sentinel — intentional保留 (warning layer)
