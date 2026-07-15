# add-archive-auto-commit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate dirty-working-tree gap after `openspec archive` by adding `commit_archive_moves` helper, wired into both `archive_change` (worktree mode) and `guide-ship.md` Phase 3 lightweight mode. Honor `SKIP_ARCHIVE_AUTO_COMMIT=yes` opt-out; idempotent on already-committed archives.

**Architecture:** Single bash helper in `skills/_lib/archive.sh` that stages 3 archive-related paths (`openspec/changes/<name>/` deletion + `openspec/changes/archive/` + `openspec/specs/`) and produces 1 commit with the conventional message `archive(<name>): archive completed`. Helper called from 2 sites (worktree `archive_change` + lightweight `guide-ship.md` Phase 3) with `|| true` so failure tolerates. Bats integration test using `git init` + manual archive simulation. Idempotent on clean working tree.

**Tech Stack:** Bash (archive.sh helper) + bats 1.10+ (integration test) + openspec CLI v1.4.1+.

**OpenSpec change artifacts** (canonical): `openspec/changes/add-archive-auto-commit/{proposal,tasks}.md` + `specs/archive-auto-commit/spec.md` (5 ADDED Requirements).

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/archive.sh` | MODIFY: add `commit_archive_moves` helper, hook into `archive_change` |
| `skills/guide-ship.md` | MODIFY: Phase 3 lightweight mode calls helper after inline `openspec archive` |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_commit_archive_moves.bats` | NEW: 3 bats tests (normal / SKIP env / idempotent) |

### Documentation

| File | Responsibility |
|---|---|
| `AGENTS.md` | MODIFY: append `### Archive Auto-Commit (v2.0.4 新增)` paragraph under 归档流程 |

---

## Pre-flight

- [ ] **Verify baseline tests pass before changes**

```bash
cd /workspace/project/rdd-workflow
bats tests/smoke.bats
```

- [ ] **Locate archive.sh helper structure**

```bash
grep -n "^archive_change\|^mark_iteration_archived" skills/_lib/archive.sh
```

- [ ] **Identify the two inline `openspec archive` calls that need hooking**

```bash
grep -n "openspec archive" skills/_lib/archive.sh skills/guide-ship.md
```

---

### Task 1: Add `commit_archive_moves` helper (TDD)

**Files:** `skills/_lib/archive.sh`, `tests/integration/test_commit_archive_moves.bats`

- [ ] **Step 1.1: Write failing bats test** per tasks.md Task 2.1 Step 1. 3 tests:
  - `commit_archive_moves: stages 3 paths and produces 1 commit`
  - `commit_archive_moves: SKIP_ARCHIVE_AUTO_COMMIT=yes skips`
  - `commit_archive_moves: idempotent on already-committed archive`

- [ ] **Step 1.2: Verify tests fail**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_commit_archive_moves.bats
```
Expected: all fail with `commit_archive_moves: command not found`.

- [ ] **Step 1.3: Implement helper** per tasks.md Task 2.1 Step 3.

Add to `skills/_lib/archive.sh` header doc:
```
#   - commit_archive_moves <name> <main_root>
#       Stage + commit the 3 path trio created by `openspec archive
#       <name>`: the deleted active change dir, the new
#       archive/<date>-<name>/ dir, and the new main spec dir.
#       Honors SKIP_ARCHIVE_AUTO_COMMIT=yes (opt-out).
#       Idempotent: when working tree is clean (already committed),
#       exits 0 with no commit.
```

Function body (~25 LOC) per tasks.md:
- Opt-out check at top
- Idempotency check via `git status --porcelain`
- `git add` of 3 paths
- `git commit -m "archive(<name>): archive completed"`
- `git reset HEAD` on commit failure

- [ ] **Step 1.4: Verify tests pass**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_commit_archive_moves.bats
```
Expected: all 3 pass.

- [ ] **Step 1.5: Commit**

```bash
cd /workspace/project/rdd-workflow
git add skills/_lib/archive.sh tests/integration/test_commit_archive_moves.bats
git commit -m "feat(_lib): add commit_archive_moves helper with bats tests

- Auto-commits openspec archive file moves (deleted active dir + new
  archive/<date>-<name>/ + new main spec/)
- Honors SKIP_ARCHIVE_AUTO_COMMIT=yes opt-out env var
- Idempotent: clean working tree → no-op exit 0
- 3 bats tests: normal path + skip env var + idempotent"
```

---

### Task 2: Hook into `archive_change` (worktree mode)

**Files:** `skills/_lib/archive.sh`

- [ ] **Step 2.1: Add commit call after openspec archive**

Find the `archive_change` function body. Between `if ! openspec archive "$name" --yes; then ... fi` and `# 7. Cleanup worktree + branch`, insert:

```bash
# Auto-commit archive file moves (added by add-archive-auto-commit).
# Tolerates failure (does not abort the ship) — file moves remain
# in working tree for human review.
commit_archive_moves "$name" "$main_root" || true
```

- [ ] **Step 2.2: Verify smoke tests pass**

```bash
bats tests/smoke.bats
```

- [ ] **Step 2.3: Commit**

```bash
git add skills/_lib/archive.sh
git commit -m "feat(_lib): auto-commit archive moves in archive_change

- Calls commit_archive_moves after openspec archive in worktree mode
- Tolerates failure (|| true) so ship flow doesn't break
- Fixes post-archive dirty working tree (5 deletions + 2 untracked dirs)
  observed on 2026-07-15 add-spec-validation-gates ship"
```

---

### Task 3: Wire into `guide-ship.md` Phase 3 lightweight mode

**Files:** `skills/guide-ship.md`

- [ ] **Step 3.1: Locate inline `openspec archive` in lightweight path**

```bash
grep -n 'openspec archive "\$CHANGE_NAME"' skills/guide-ship.md
```
Expected: ~line 1060-1065 (after the spec-validation gate from add-spec-validation-gates).

- [ ] **Step 3.2: Add commit call after inline openspec archive**

Insert after `openspec archive "$CHANGE_NAME" --yes || { ... }` block:

```bash
        # Auto-commit archive file moves (added by add-archive-auto-commit).
        # Tolerates failure — file moves remain in working tree for human review.
        if [ -f "$PROJECT_ROOT/skills/_lib/archive.sh" ]; then
            source "$PROJECT_ROOT/skills/_lib/archive.sh"
        fi
        commit_archive_moves "$CHANGE_NAME" "$PROJECT_ROOT" || true
```

- [ ] **Step 3.3: Verify frontmatter intact**

```bash
head -5 skills/guide-ship.md && grep -c "^---" skills/guide-ship.md
```
Expected: frontmatter + closing `---`.

- [ ] **Step 3.4: Commit**

```bash
git add skills/guide-ship.md
git commit -m "feat(guide-ship): auto-commit archive moves in lightweight mode

- Calls commit_archive_moves after inline openspec archive in Phase 3
- Source archive.sh if available (no-op if already sourced)
- Tolerates failure — leaves moves in working tree for human review"
```

---

### Task 4: Document new behavior in AGENTS.md

**Files:** `AGENTS.md`

- [ ] **Step 4.1: Find 归档流程 section**

```bash
grep -n "归档流程\|archive.sh" AGENTS.md | head -10
```

- [ ] **Step 4.2: Append explanation paragraph**

After existing `archive_change 内部完成...` paragraph, add new section:
```markdown
### Archive Auto-Commit (v2.0.4 新增)

`openspec archive <name> --yes` 移动文件后,`archive.sh::commit_archive_moves <name> <main_root>` 自动 stage + commit:

- **Default ON**:每个 archive 产生 1 个新 commit `archive(<name>): archive completed`(匹配 `0d6ba45` 的 repo convention)。
- **Opt-out**:`SKIP_ARCHIVE_AUTO_COMMIT=yes` 跳过 helper(适用:用户想手工构造 commit message)。
- **Idempotent**:已 commit 后再调用,working tree 干净 → 立即 exit 0,无新 commit。
- **Coverage**:在 worktree 模式 (`archive_change`) 和 lightweight 模式 (`guide-ship.md` Phase 3) 都生效。
```

- [ ] **Step 4.3: Verify heading structure intact**

```bash
head -5 AGENTS.md && grep -c "^## " AGENTS.md
```

- [ ] **Step 4.4: Commit**

```bash
git add AGENTS.md
git commit -m "docs(AGENTS.md): document archive auto-commit behavior

- Append note under 归档流程 describing commit_archive_moves
- Documents SKIP_ARCHIVE_AUTO_COMMIT opt-out + idempotency
- Cites 0d6ba45 as convention reference"
```

---

### Task 5: Final verification

- [ ] **Step 5.1: Full pytest suite**

```bash
python3 -m pytest tests/unit/ tests/integration/ -q --tb=short
```
Expected: pass.

- [ ] **Step 5.2: bats full suite**

```bash
npm test
```
Expected: exit 0.

- [ ] **Step 5.3: End-to-end regression** — simulate the full archive flow:

```bash
mkdir -p /tmp/regression-archive/openspec/changes/test-fix/specs/test-fix
cd /tmp/regression-archive && git init -q && git config user.email t@t.t && git config user.name t
mkdir openspec/specs
echo "schema: spec-driven" > openspec/changes/test-fix/.openspec.yaml
echo "# fix" > openspec/changes/test-fix/specs/test-fix/spec.md
git add . && git commit -q -m init

# Manually simulate the archive move:
mkdir -p openspec/changes/archive/2026-07-15-test-fix
mv openspec/changes/test-fix/.openspec.yaml openspec/changes/archive/2026-07-15-test-fix/
mv openspec/changes/test-fix/specs/test-fix/spec.md openspec/changes/archive/2026-07-15-test-fix/specs/test-fix/
rmdir openspec/changes/test-fix/specs/test-fix openspec/changes/test-fix/specs openspec/changes/test-fix
# Move spec to main specs
mv openspec/changes/archive/2026-07-15-test-fix/specs/test-fix/spec.md openspec/specs/test-fix/spec.md

# Working tree should be dirty (5 deletions + 1 new). Now call helper:
source /workspace/project/rdd-workflow/skills/_lib/archive.sh
commit_archive_moves test-fix /tmp/regression-archive

git log -1 --format=%s   # Should say "archive(test-fix): archive completed"
git status              # Should be clean
```

- [ ] **Step 5.4: Update iteration.json tasks_done**

```bash
python3 -c "
import sys, os
sys.path.insert(0, '/workspace/project/rdd-workflow')
from skills._lib import iteration as it_mod
data = it_mod.load('/workspace/project/rdd-workflow')
data = it_mod.add_or_update_change(data, name='add-archive-auto-commit', status='completed')
it_mod.save('/workspace/project/rdd-workflow', data)
"
```

---

## Acceptance Criteria

- [ ] `commit_archive_moves` exported helper in `archive.sh`
- [ ] `archive_change` calls helper, produces exactly 1 new commit
- [ ] guide-ship.md Phase 3 lightweight mode also calls helper
- [ ] `SKIP_ARCHIVE_AUTO_COMMIT=yes` opt-out works (verified)
- [ ] Idempotent on clean working tree (verified)
- [ ] Commit message: `archive(<name>): archive completed`
- [ ] Helper rolls back `git add` on commit failure (`git reset HEAD`)
- [ ] bats tests pass + all existing tests still pass
- [ ] AGENTS.md documents behavior + opt-out env var

## Commit History Expected

```
4aa712c (master base) feat(openspec): add add-archive-auto-commit change (manifest, this lands first)
feat(_lib):   add commit_archive_moves helper with bats tests
feat(_lib):   auto-commit archive moves in archive_change
feat(guide-ship): auto-commit archive moves in lightweight mode
docs(AGENTS): document archive auto-commit behavior
```
