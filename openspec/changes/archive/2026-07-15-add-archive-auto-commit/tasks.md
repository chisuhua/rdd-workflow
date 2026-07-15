---
SCOPE: shared
STATUS: PROPOSED
---

# Tasks: add-archive-auto-commit

> **Goal**: Eliminate dirty-working-tree gap after `openspec archive` by adding `commit_archive_moves` helper, wired into both `archive_change` (worktree) and `guide-ship.md` Phase 3 (lightweight). Honor `SKIP_ARCHIVE_AUTO_COMMIT=yes` opt-out; idempotent on already-committed archives.
> **Risk**: low (additive, idempotent, single-commit granularity).
> **Estimated effort**: 0.5-1 d.

## 1. Pre-flight

- [ ] 1.1 Verify baseline tests pass before changes

```bash
cd /workspace/project/rdd-workflow
bats tests/smoke.bats
```

Expected: all existing smoke cases green.

- [ ] 1.2 Locate archive.sh helper structure

```bash
grep -n "^archive_change\|^mark_iteration_archived\|^cleanup_worktree" skills/_lib/archive.sh
```

Expected: see archive_change (250-) calls mark_iteration_archived near end.

- [ ] 1.3 Identify the two inline `openspec archive` calls that need hooking

```bash
grep -n "openspec archive" skills/_lib/archive.sh skills/guide-ship.md
```

Expected: 2 hits — one in archive.sh:archive_change, one in guide-ship.md lightweight path.

## 2. Apply change

### Task 2.1: Add `commit_archive_moves` helper to archive.sh (TDD)

**Files:**
- Modify: `skills/_lib/archive.sh`
- Create: `tests/integration/test_commit_archive_moves.bats`

- [ ] **Step 1: Write the failing test (bats)**

Create `tests/integration/test_commit_archive_moves.bats`:

```bash
#!/usr/bin/env bats

# test_commit_archive_moves.bats — verify archive auto-commit helper

load 'tests/test_helper'

@test "commit_archive_moves: stages 3 paths and produces 1 commit" {
    # Set up a clean git repo
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
    git config --local init.defaultBranch master
    git checkout -b master 2>/dev/null || true

    # Simulate openspec archive effect: create moves
    mkdir -p openspec/changes/my-change/specs/my-cap
    mkdir -p openspec/specs/my-cap
    echo "original" > openspec/changes/my-change/.openspec.yaml
    echo "spec" > openspec/changes/my-change/specs/my-cap/spec.md
    git add openspec/
    git commit -q -m "add my-change skeleton"

    # Apply archive manually (delete + move)
    mkdir -p openspec/changes/archive/2026-07-15-my-change
    mv openspec/changes/my-change/.openspec.yaml openspec/changes/archive/2026-07-15-my-change/
    mv openspec/changes/my-change/specs/my-cap/spec.md openspec/changes/archive/2026-07-15-my-change/specs/my-cap/
    rmdir openspec/changes/my-change/specs/my-cap
    rmdir openspec/changes/my-change/specs
    rmdir openspec/changes/my-change
    mv openspec/specs/my-cap/spec.md openspec/changes/archive/2026-07-15-my-change/specs/my-cap/

    # Re-create main spec (simulating openspec archive step)
    echo "main spec content" > openspec/specs/my-cap/spec.md

    # Source helper + call
    source "$(git rev-parse --show-toplevel)/skills/_lib/archive.sh"
    commit_archive_moves "my-change" "$(pwd)"

    # Verify: exactly 1 new commit
    NEW_COMMITS=$(git log --oneline | wc -l)
    [ "$NEW_COMMITS" -eq 2 ]
    [[ "$(git log -1 --format=%s)" == "archive(my-change): archive completed" ]]
}

@test "commit_archive_moves: SKIP_ARCHIVE_AUTO_COMMIT=yes skips" {
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
    mkdir -p openspec/changes/my-change
    echo "x" > openspec/changes/my-change/.openspec.yaml
    git add openspec/
    git commit -q -m "init"

    SKIP_ARCHIVE_AUTO_COMMIT=yes source "$(git rev-parse --show-toplevel)/skills/_lib/archive.sh"
    # Note: when calling the function via the bash subshell, env var must be exported
    export SKIP_ARCHIVE_AUTO_COMMIT=yes
    commit_archive_moves "my-change" "$(pwd)" || true

    # No new commit
    [ "$(git log --oneline | wc -l)" -eq 1 ]
}

@test "commit_archive_moves: idempotent on already-committed archive" {
    cd "$BATS_TEST_TMPDIR"
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"

    # Pre-commit an archive-like state (clean working tree)
    mkdir -p openspec/changes/archive/2026-07-15-done
    echo "x" > openspec/changes/archive/2026-07-15-done/.openspec.yaml
    git add openspec/
    git commit -q -m "init"

    source "$(git rev-parse --show-toplevel)/skills/_lib/archive.sh"
    commit_archive_moves "done" "$(pwd)"

    # Still just 1 commit
    [ "$(git log --oneline | wc -l)" -eq 1 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_commit_archive_moves.bats
```

Expected: all 3 tests fail (`commit_archive_moves: command not found`).

- [ ] **Step 3: Write minimal implementation**

Add to `skills/_lib/archive.sh` (after `mark_iteration_archived`, before EOF), plus update header comment block:

```bash
#
#   - commit_archive_moves <name> <main_root>
#       Stage + commit the 3 path trio created by `openspec archive
#       <name>`: the deleted active change dir, the new
#       archive/<date>-<name>/ dir, and the new main spec dir.
#       Honors SKIP_ARCHIVE_AUTO_COMMIT=yes (opt-out).
#       Idempotent: when working tree is clean (already committed),
#       exits 0 with no commit.
#       Returns 0 on success or skipped, 1 on commit failure.
#
#   - mark_iteration_archived <name> <main_root>
#       Update .rddf/state/iteration.json to mark <name> as archived.
#       ... (existing doc)
```

Then the function body:

```bash
# commit_archive_moves <name> <main_root>
# Auto-commit archive file moves. See header doc.
commit_archive_moves() {
    local name="${1:-}" main_root="${2:-}"
    [[ -z "$name" || -z "$main_root" ]] && { echo "❌ commit_archive_moves 需要 name 和 main_root"; return 1; }

    # Opt-out
    if [ "${SKIP_ARCHIVE_AUTO_COMMIT:-no}" = "yes" ]; then
        echo "ℹ️  commit_archive_moves: SKIPPED (SKIP_ARCHIVE_AUTO_COMMIT=yes)"
        return 0
    fi

    # Idempotent: clean working tree means nothing to commit
    if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
        return 0
    fi

    # Only stage the 3 archive-related paths (strict scope)
    cd "$main_root" || return 1
    git add \
        "openspec/changes/${name}/" \
        "openspec/changes/archive/" \
        "openspec/specs/" || {
        git reset HEAD >/dev/null 2>&1 || true
        echo "❌ commit_archive_moves: git add failed"
        return 1
    }

    # Commit with repo-conventional message
    if ! git commit -m "archive(${name}): archive completed"; then
        git reset HEAD >/dev/null 2>&1 || true
        echo "❌ commit_archive_moves: git commit failed"
        return 1
    fi

    echo "✅ commit_archive_moves: produced archive(${name}) commit"
    return 0
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_commit_archive_moves.bats
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/archive.sh tests/integration/test_commit_archive_moves.bats
git commit -m "feat(_lib): add commit_archive_moves helper with bats tests

- Auto-commits openspec archive file moves (deleted active dir + new
  archive/<date>-<name>/ + new main spec/)
- Honors SKIP_ARCHIVE_AUTO_COMMIT=yes opt-out env var
- Idempotent: clean working tree → no-op exit 0
- 3 bats tests: normal path + skip env var + idempotent"
```

### Task 2.2: Hook helper into `archive_change` (worktree mode)

**Files:**
- Modify: `skills/_lib/archive.sh`

- [ ] **Step 1: Add commit call after openspec archive**

Find the `archive_change` function body, locate the line after `openspec archive "$name" --yes`. Add:

```bash
  # Auto-commit archive file moves (added by add-archive-auto-commit).
  # Tolerates failure (does not abort the ship) — file moves are still
  # in working tree for human review.
  commit_archive_moves "$name" "$main_root" || true
```

Place: between `if ! openspec archive "$name" --yes; then ... fi` and `# 7. Cleanup worktree + branch`.

- [ ] **Step 2: Verify smoke test still passes**

Run: `bats tests/smoke.bats`
Expected: green.

- [ ] **Step 3: Commit**

```bash
git add skills/_lib/archive.sh
git commit -m "feat(_lib): auto-commit archive moves in archive_change

- Calls commit_archive_moves after openspec archive in worktree mode
- Tolerates failure (no-op with stderr warn) so ship flow doesn't break
- Fixes post-archive dirty working tree (5 deletions + 2 untracked dirs)"
```

### Task 2.3: Wire helper into `guide-ship.md` Phase 3 lightweight mode

**Files:**
- Modify: `skills/guide-ship.md`

- [ ] **Step 1: Locate inline openspec archive in lightweight path**

Run: `grep -n 'openspec archive "$CHANGE_NAME"' skills/guide-ship.md`
Expected: ~line 1060-1065 (after the spec-validation gate from add-spec-validation-gates).

- [ ] **Step 2: Add commit call after inline openspec archive**

Insert just after the `openspec archive "$CHANGE_NAME" --yes || { ... }` block:

```bash
        # Auto-commit archive file moves (added by add-archive-auto-commit).
        # Tolerates failure — file moves remain in working tree for human review.
        if [ -f "$PROJECT_ROOT/skills/_lib/archive.sh" ]; then
            source "$PROJECT_ROOT/skills/_lib/archive.sh"
        fi
        commit_archive_moves "$CHANGE_NAME" "$PROJECT_ROOT" || true
```

- [ ] **Step 3: Verify guide-ship.md frontmatter intact**

Run: `head -5 skills/guide-ship.md && grep -c "^---" skills/guide-ship.md`
Expected: frontmatter + closing `---`.

- [ ] **Step 4: Commit**

```bash
git add skills/guide-ship.md
git commit -m "feat(guide-ship): auto-commit archive moves in lightweight mode

- Calls commit_archive_moves after inline openspec archive in Phase 3
- Source archive.sh if available (no-op in interactive shells)
- Tolerates failure — leaves moves in working tree for human review"
```

### Task 2.4: Document new behavior in AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Find 归档流程 section**

Run: `grep -n "归档流程\|archive.sh" AGENTS.md | head -10`
Expected: locate `\`archive_change\` 内部完成: pre-merge check → ...` block.

- [ ] **Step 2: Append explanation paragraph**

After the existing `\`archive_change\` 内部完成...` paragraph, add:

```markdown
### Archive Auto-Commit (v2.0.4 新增)

`openspec archive <name> --yes` 移动文件后,`archive.sh::commit_archive_moves <name> <main_root>` 自动 stage + commit:

- **Default ON**:每个 archive 产生 1 个新 commit `archive(<name>): archive completed`(匹配 `0d6ba45` 的 repo convention)。
- **Opt-out**:`SKIP_ARCHIVE_AUTO_COMMIT=yes` 跳过 helper(适用:用户想手工构造 commit message、或要分多个 archive 一起 commit)。
- **Idempotent**:已 commit 后再调用,working tree 干净 → 立即 exit 0,无新 commit。
- **Coverage**:在 worktree 模式 (`archive_change`) 和 lightweight 模式 (`guide-ship.md` Phase 3) 都生效。

无需手工 `git add openspec/...` + 手工 commit message 了。
```

- [ ] **Step 3: Verify AGENTS.md renders**

Run: `head -5 AGENTS.md && grep -c "^## " AGENTS.md`
Expected: heading structure intact.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "docs(AGENTS.md): document archive auto-commit behavior

- Append note under 归档流程: archive_change/commit_archive_moves
- Documents opt-out env var + idempotency + commit message convention"
```

### Task 2.5: Final verification

- [ ] **2.5.1: Full pytest suite**

Run: `python3 -m pytest tests/unit/ tests/integration/ -q --tb=short`
Expected: all pass (551 + 76).

- [ ] **2.5.2: bats smoke**

Run: `bats tests/smoke.bats`
Expected: green.

- [ ] **2.5.3: full bats suite**

Run: `npm test`
Expected: green (smoke + 1 new test + existing integration).

- [ ] **2.5.4: End-to-end archive auto-commit regression test**

Manually verify by running archive flow on a fresh test change:

```bash
mkdir -p /tmp/test-archive-flow/openspec/changes/regression-test/specs/regression-cap
cd /tmp/test-archive-flow && git init -q && git config user.email t@t.t && git config user.name t
# Create minimal openspec/
mkdir openspec/specs
echo "schema: spec-driven" > openspec/changes/regression-test/.openspec.yaml
echo "# x" > openspec/changes/regression-test/proposal.md
echo "# x" > openspec/changes/regression-test/specs/regression-cap/spec.md
git add openspec/ && git commit -q -m init

# Now simulate the archive call (without --yes; with our helper)
# This step requires openspec CLI to be installed and the archive helper invoked
```

Expected: archive commit message + clean working tree.

- [ ] **2.5.5: Update iteration.json tasks_done**

After all commits land, mark change as completed in iteration.json:

```bash
python3 -c "
import sys, os
sys.path.insert(0, '/workspace/project/rdd-workflow')
from skills._lib import iteration as it_mod
data = it_mod.load('/workspace/project/rdd-workflow')
data = it_mod.add_or_update_change(data, name='add-archive-auto-commit', status='completed')
it_mod.save('/workspace/project/rdd-workflow', data)
print('✅ iteration.json: add-archive-auto-commit → completed')
"
```

## Acceptance Criteria

- [ ] `commit_archive_moves` documented exported helper in `archive.sh`
- [ ] `archive_change` calls helper, produces exactly 1 new commit
- [ ] guide-ship.md Phase 3 lightweight also calls helper
- [ ] `SKIP_ARCHIVE_AUTO_COMMIT=yes` opt-out works (tested)
- [ ] Idempotent on clean working tree (tested)
- [ ] Commit message: `archive(<name>): archive completed` (matches repo convention)
- [ ] Helper rolls back `git add` on commit failure (`git reset HEAD`)
- [ ] bats tests pass + all existing tests still pass
- [ ] AGENTS.md documents behavior + opt-out env var
- [ ] Master clean after archive

## Commit History Expected

```
<latest master> (incoming)
docs(openspec): add add-archive-auto-commit change manifest (this commit lands first)
feat(_lib):  add commit_archive_moves helper with bats tests
feat(_lib):  auto-commit archive moves in archive_change
feat(guide-ship): auto-commit archive moves in lightweight mode
docs(AGENTS): document archive auto-commit behavior
```
