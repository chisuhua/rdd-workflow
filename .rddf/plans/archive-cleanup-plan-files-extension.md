# archive-cleanup-plan-files-extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `_lib/post_archive_cleanup.sh::_WHITELIST_DELETED_PATTERNS` to also clean `openspec/changes/<name>/` residue (6 artifact types) after `openspec archive`, with defensive `openspec/changes/archive/<date>-<name>/` presence check to prevent accidental deletion of active changes. Eliminates the 6-residue noise that triggers `./test.sh --full` `D` status reports and `rdd-doctor` state warnings.

**Architecture:** Single bash extension in `_lib/post_archive_cleanup.sh` — add `openspec/changes/` to `_WHITELIST_DELETED_PATTERNS` (line 31-35), augment the `D` branch in the main loop (line 80-85) with `compgen -G` archive-presence check using `YYYY-MM-DD-<name>` glob, and add a new `--include-change-artifacts` flag to `scripts/cleanup-plan-files.sh` manual entry that lists 6-artifact directories + interactive confirmation. Idempotent (no-op when buckets empty), respects `SKIP_POST_ARCHIVE_CLEANUP=yes` (skips entirely), respects `DRY_RUN_POST_ARCHIVE_CLEANUP=yes` (echoes without running git). 8 bats unit tests + 3 e2e tests for the new behavior; 9 existing bats tests for `archive-cleanup-plan-files` must not regress.

**Tech Stack:** bash 4.0+ + bats 1.10+ + openspec CLI v1.4.1+ + git 2.25+.

**OpenSpec change artifacts** (canonical):
- `openspec/changes/archive-cleanup-plan-files-extension/{proposal,design,tasks}.md`
- `openspec/changes/archive-cleanup-plan-files-extension/specs/post-archive-cleanup-hook/spec.md` (7 MODIFIED Requirements targeting `post-archive-cleanup-hook`)
- `openspec/specs/post-archive-cleanup-hook/spec.md` (canonical, mirror of delta)

**Spec contract:** 7 MODIFIED Requirements under `## MODIFIED Requirements` — each requirement body MUST start with SHALL or MUST on the first line, and MUST contain `modifies: post-archive-cleanup-hook` within the first 5 lines of body (validator contract).

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/post_archive_cleanup.sh` | MODIFY: extend `_WHITELIST_DELETED_PATTERNS` (add `openspec/changes/`), augment `D` branch with archive-presence check |
| `scripts/cleanup-plan-files.sh` | MODIFY: add `--include-change-artifacts` flag, interactive confirmation flow |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_post_archive_cleanup_changes.bats` | NEW: 8 bats unit tests (whitelist, prefix match, archive self-skip, active blocked, idempotent, skip-env, dry-run, modified-bucket) |
| `tests/integration/test_post_archive_cleanup_changes_e2e.bats` | NEW: 3 e2e tests (worktree mode, lightweight mode, active change protection) |

### Documentation

| File | Responsibility |
|---|---|
| `openspec/specs/post-archive-cleanup-hook/spec.md` | EXISTS: 7 MODIFIED Requirements (no net change in this implementation step) |

---

## Pre-flight

- [ ] **Verify baseline tests pass before changes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_archive_cleanup_plan_files.bats
```
Expected: 9 existing tests pass (no regression in scope).

- [ ] **Confirm WHITELIST location**

```bash
grep -n "_WHITELIST_DELETED_PATTERNS" _lib/post_archive_cleanup.sh
```
Expected: line 31 array declaration.

- [ ] **Confirm `D` branch location**

```bash
grep -n "deleted_to_rm" _lib/post_archive_cleanup.sh
```
Expected: branch around line 80-85.

- [ ] **Stage current dirty state before worktree commit**

```bash
cd /workspace/project/rdd-workflow
git status --short
```
Expected: 6 `D openspec/changes/add-rdd-doctor-skill/...` files (pre-existing residue — will be cleaned by this change's helper once implemented).

---

## Task 1: Extend `_WHITELIST_DELETED_PATTERNS` (TDD)

**Files:** `_lib/post_archive_cleanup.sh`, `tests/integration/test_post_archive_cleanup_changes.bats`

- [ ] **Step 1.1: Write failing bats test for new whitelist entry**

3 tests covering line 32 of this plan:
- `test: WHITELIST contains openspec/changes/`
- `test: _matches_prefix matches openspec/changes/foo`
- `test: _matches_prefix does NOT match openspec/changes/archive/`

Write `tests/integration/test_post_archive_cleanup_changes.bats` header (load `test_helper`) and the 3 tests. The test loads `_lib/post_archive_cleanup.sh` in a temp dir and asserts the array contents.

- [ ] **Step 1.2: Verify tests fail**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_post_archive_cleanup_changes.bats
```
Expected: 3 tests fail with `expected openspec/changes/ to be in _WHITELIST_DELETED_PATTERNS`.

- [ ] **Step 1.3: Implement whitelist extension**

Edit `_lib/post_archive_cleanup.sh` line 31-35:

```bash
# Before
_WHITELIST_DELETED_PATTERNS=(
  ".rddf/plans/"
  ".rddf/state/.arch-handoff.json.tmp"
  ".rddf/state/.plan-handoff.json.tmp"
)

# After
_WHITELIST_DELETED_PATTERNS=(
  ".rddf/plans/"
  ".rddf/state/.arch-handoff.json.tmp"
  ".rddf/state/.plan-handoff.json.tmp"
  "openspec/changes/"
)
```

- [ ] **Step 1.4: Verify tests pass**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_post_archive_cleanup_changes.bats
```
Expected: 3 tests pass.

---

## Task 2: Add archive-presence defensive check (TDD)

**Files:** `_lib/post_archive_cleanup.sh`, `tests/integration/test_post_archive_cleanup_changes.bats`

- [ ] **Step 2.1: Write failing bats test for active-change protection**

Append 2 tests to the file from Task 1:
- `test: active change in openspec/changes/<name>/ is NOT cleaned when archive/ absent`
- `test: archive/ subdir is excluded from cleanup`

The tests need a temp repo with `openspec/changes/<name>` and `openspec/changes/archive/<date>-<name>/` structures (or absence thereof), then call `post_archive_cleanup` and assert `git rm` did/didn't run.

- [ ] **Step 2.2: Verify tests fail**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_post_archive_cleanup_changes.bats
```
Expected: 2 new tests fail (existing 3 pass).

- [ ] **Step 2.3: Implement archive-presence check**

Edit `_lib/post_archive_cleanup.sh` around line 80-85 (the ` D` branch):

```bash
# Before
' D')   # deleted in worktree, not staged
  if _matches_prefix "$path" "${_WHITELIST_DELETED_PATTERNS[@]}"; then
    deleted_to_rm+=("$path")
  fi
  ;;

# After
' D')   # deleted in worktree, not staged
  if _matches_prefix "$path" "${_WHITELIST_DELETED_PATTERNS[@]}"; then
    # Special case: openspec/changes/<name>/* requires archive-presence check
    # to prevent accidental deletion of active changes.
    case "$path" in
      openspec/changes/archive/*) ;;  # archive/ preserves history, skip
      openspec/changes/*)
        # Extract <name> (path component 3)
        name=$(echo "$path" | cut -d/ -f3)
        # Verify archive/<YYYY-MM-DD>-<name>/ exists
        if compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-$name" > /dev/null; then
          deleted_to_rm+=("$path")
        else
          echo "⚠️  skip $path (no archive/<date>-$name/)" >&2
        fi
        ;;
      *)
        deleted_to_rm+=("$path")
        ;;
    esac
  fi
  ;;
```

- [ ] **Step 2.4: Verify tests pass**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_post_archive_cleanup_changes.bats
```
Expected: 5 tests pass.

---

## Task 3: Add 3 idempotency / env-var / dry-run tests (TDD)

**Files:** `tests/integration/test_post_archive_cleanup_changes.bats`

- [ ] **Step 3.1: Write failing bats tests**

Append 3 tests:
- `test: idempotent — second run with clean tree is no-op`
- `test: SKIP_POST_ARCHIVE_CLEANUP=yes skips openspec/changes cleaning`
- `test: DRY_RUN_POST_ARCHIVE_CLEANUP=yes echoes but does not run git`

These tests do NOT require source modifications — they verify existing behavior is preserved when the new patterns are active.

- [ ] **Step 3.2: Verify tests pass**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_post_archive_cleanup_changes.bats
```
Expected: 8 tests pass (no implementation needed for this task).

---

## Task 4: Manual entry `--include-change-artifacts` flag (TDD)

**Files:** `scripts/cleanup-plan-files.sh`, `tests/integration/test_post_archive_cleanup_changes.bats`

- [ ] **Step 4.1: Locate existing `cleanup-plan-files.sh` script**

```bash
cd /workspace/project/rdd-workflow
find . -name "cleanup-plan-files.sh" -not -path "*/node_modules/*"
```
Expected: 1 file in `scripts/` or `_lib/`.

- [ ] **Step 4.2: Add arg parser + new section**

Edit the entry point to accept `--include-change-artifacts` and add a new section that lists each `openspec/changes/<name>/` (excluding `archive/`) with archive-presence check + 6-artifact count + interactive confirmation.

```bash
# Add to top-level arg parser
INCLUDE_CHANGES=0
case "${1:-}" in
  --include-change-artifacts) INCLUDE_CHANGES=1; shift ;;
esac

# After existing main logic, add:
if [ "$INCLUDE_CHANGES" = "1" ]; then
  echo "📋 Rescans openspec/changes/<name>/ directories (with archive-presence guard)"
  for dir in openspec/changes/*/; do
    name=$(basename "$dir")
    [ "$name" = "archive" ] && continue
    if ! compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-$name" > /dev/null; then
      echo "  ⏭️  skip $name (no archive/<date>-$name)"
      continue
    fi
    count=$(find "$dir" -maxdepth 2 -type f 2>/dev/null | wc -l)
    echo "  $name: $count files"
  done
  read -r -p "确认清理? [y/N]: " confirm
  if [ "$confirm" = "y" ]; then
    git rm -r openspec/changes/*/  # except archive/
    for d in openspec/changes/*/; do
      [ "$(basename "$d")" = "archive" ] && continue
      git rm -r "$d"
    done
  fi
fi
```

- [ ] **Step 4.3: Write 1 bats test for the new flag**

Extend `tests/integration/test_post_archive_cleanup_changes.bats` with:
- `test: --include-change-artifacts flag is accepted and lists archives`

Test invokes the script with the flag, captures stdout, asserts the archive-presence guard output appeared.

- [ ] **Step 4.4: Verify test passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_post_archive_cleanup_changes.bats
```
Expected: 9 tests pass.

---

## Task 5: E2E test — worktree mode simulation

**Files:** `tests/integration/test_post_archive_cleanup_changes_e2e.bats`

- [ ] **Step 5.1: Write e2e test**

Write `tests/integration/test_post_archive_cleanup_changes_e2e.bats` with 1 test:

```bash
@test "e2e: worktree mode archive leaves 6 residue cleaned by post_archive_cleanup"
```

The test:
1. Creates a temp repo, openspec init, openspec new change
2. Manually sets up `openspec/changes/<name>/.openspec.yaml` etc.
3. Manually creates `archive/<date>-<name>/` and stale `D` status
4. Runs `openspec archive <name> --yes`
5. Runs `post_archive_cleanup`
6. Asserts `git status --porcelain` is empty except for the 6 expected `git rm` results
7. Asserts 1 commit with subject `chore(post-archive): clean residue from <name>`

- [ ] **Step 5.2: Verify test passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_post_archive_cleanup_changes_e2e.bats
```
Expected: 1 test passes.

---

## Task 6: E2E test — lightweight mode simulation

**Files:** `tests/integration/test_post_archive_cleanup_changes_e2e.bats`

- [ ] **Step 6.1: Write e2e test**

Append 1 test:

```bash
@test "e2e: lightweight mode archive leaves 6 residue cleaned by post_archive_cleanup"
```

Similar to Task 5 but without creating a worktree (run on master branch directly).

- [ ] **Step 6.2: Verify test passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_post_archive_cleanup_changes_e2e.bats
```
Expected: 2 tests pass.

---

## Task 7: E2E test — active change protection

**Files:** `tests/integration/test_post_archive_cleanup_changes_e2e.bats`

- [ ] **Step 7.1: Write e2e test**

Append 1 test:

```bash
@test "e2e: active change in openspec/changes/<name>/ is NOT cleaned by post_archive_cleanup"
```

The test:
1. Creates temp repo with active change at `openspec/changes/<name>/` (no archive)
2. Manually `git rm` one file (creates `D` status)
3. Runs `post_archive_cleanup`
4. Asserts the file is NOT deleted (defense activated)
5. Asserts no commit was created

- [ ] **Step 7.2: Verify test passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_post_archive_cleanup_changes_e2e.bats
```
Expected: 3 tests pass.

---

## Task 8: Regression — existing 9 tests must not break

- [ ] **Step 8.1: Run existing test suite**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_archive_cleanup_plan_files.bats
```
Expected: 9 tests pass (no regression).

- [ ] **Step 8.2: Run full test suite**

```bash
cd /workspace/project/rdd-workflow
./test.sh --full --regression
```
Expected: 0 new failures beyond KNOWN_FAILURES baseline.

---

## Task 9: Worktree commit (post-execute)

- [ ] **Step 9.1: Stage and commit all changes**

```bash
cd /workspace/project/rdd-workflow/.rddf/wt/archive-cleanup-plan-files-extension
git add -A
git status --short
git commit -m "feat(post-archive-cleanup): extend scope to openspec/changes/<name>/

- _WHITELIST_DELETED_PATTERNS adds 'openspec/changes/' (line 31-35)
- ' D' branch adds archive-presence compgen check (defends against active change deletion)
- scripts/cleanup-plan-files.sh --include-change-artifacts flag (manual entry)
- 8 bats unit tests + 3 e2e tests covering the new behavior
- existing 9 archive-cleanup-plan-files tests unaffected

Skills: archive-cleanup-plan-files-extension (P2, bugfix)"
```

- [ ] **Step 9.2: Verify commit**

```bash
git log -1 --oneline
```
Expected: 1 new commit with the conventional message.

---

## Task 10: Archive (Phase 3)

- [ ] **Step 10.1: Trigger archive flow**

```bash
cd /workspace/project/rdd-workflow
bash skills/_lib/archive.sh archive_change archive-cleanup-plan-files-extension
```

Or use the skill-managed path: re-invoke `skill_use("guide-ship")` and select archive option.

- [ ] **Step 10.2: Verify archive succeeded**

```bash
cd /workspace/project/rdd-workflow
ls -la openspec/changes/archive/ | grep archive-cleanup-plan-files-extension
git log --oneline -5
```
Expected: 1 new commit `archive(archive-cleanup-plan-files-extension): archive completed`, change dir moved to archive/.

---

## Notes

- **Out of Scope (preserve):** `.rddf/plans/` cleanup, `openspec/changes/archive/` cleanup, `KNOWN_FAILURES.txt` modifications.
- **Commit policy:** Per AGENTS.md, this change ships 1 aggregated commit (not per-task). The branch must have ≥1 commit before archive.
- **Test isolation:** All bats tests use `BATS_TMPDIR` for isolation; no shared state with the production repo.
- **Defensive checks:** `compgen -G` glob pattern `[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<name>` matches `YYYY-MM-DD-<name>` format. Empty `date` slots ([0-9] won't match) ensure no false positives.
