# harden-archive-iteration-sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add on-disk reconciliation fallback to archive flow so iteration.json sync failures no longer leave stale `📋 planned` entries for already-archived changes.

**Architecture:** Add a `reconcile_iteration_from_disk` Python helper (called from bash) that scans `openspec/changes/archive/` and force-syncs iteration.json entries. Wire it into `archive_change_for_mode` as a fallback after `mark_iteration_archived`. Also expose a manual `reconcile` subcommand in `archive.sh` for one-shot remediation of historical drift.

**Tech Stack:** bash (archive.sh / ship_archive.sh), Python 3.11+ (skills/_lib/iteration), bats-core 1.10+ (integration tests)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/iteration/repair.py` (NEW) | Pure-Python reconciliation logic: scan archive dir, force-set iteration.json entry to archived |
| `skills/guide-ship/scripts/ship_archive.sh` (MODIFY) | Call `reconcile_iteration_from_disk` after `mark_iteration_archived` in `archive_change_for_mode` |
| `skills/_lib/archive.sh` (MODIFY) | Add `reconcile` subcommand for manual one-shot remediation |
| `docs/operations/archive-state-recovery.md` (NEW) | User-facing recovery guide |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_archive_iteration_sync_resilience.bats` (NEW) | 3 cases: normal flow, sync-fail, manual reconcile |

---

### Task 1: Implement reconcile_iteration_from_disk Python helper

**Files:**
- Create: `skills/_lib/iteration/repair.py`
- Test: `tests/unit/test_iteration_repair.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_iteration_repair.py` with the following test that exercises the reconciliation helper:

```python
"""Tests for skills._lib.iteration.repair module."""
import json
from pathlib import Path

from skills._lib.iteration import repair


def test_force_mark_archived_writes_iteration(tmp_path: Path) -> None:
    """force_mark_archived writes status=archived + archived_at to iteration.json."""
    # Setup: project root with archive dir + iteration.json
    project_root = tmp_path
    rddf = project_root / ".rddf" / "state"
    rddf.mkdir(parents=True)
    iter_file = rddf / "iteration.json"
    iter_file.write_text(json.dumps({
        "version": 7,
        "changes": [
            {"name": "test-change", "status": "planned", "added_at": "2026-01-01T00:00:00Z"}
        ]
    }))
    archive_dir = project_root / "openspec" / "changes" / "archive" / "2026-08-16-test-change"
    archive_dir.mkdir(parents=True)
    (archive_dir / "proposal.md").write_text("# test")

    # Exercise
    repair.force_mark_archived(str(project_root), "test-change")

    # Verify
    data = json.loads(iter_file.read_text())
    entry = next(c for c in data["changes"] if c["name"] == "test-change")
    assert entry["status"] == "archived"
    assert "archived_at" in entry


def test_force_mark_archived_skips_when_no_archive_dir(tmp_path: Path) -> None:
    """force_mark_archived is a no-op when archive dir doesn't exist."""
    project_root = tmp_path
    rddf = project_root / ".rddf" / "state"
    rddf.mkdir(parents=True)
    iter_file = rddf / "iteration.json"
    iter_file.write_text(json.dumps({
        "version": 7,
        "changes": [{"name": "ghost", "status": "planned", "added_at": "2026-01-01T00:00:00Z"}]
    }))

    repair.force_mark_archived(str(project_root), "ghost")

    data = json.loads(iter_file.read_text())
    entry = data["changes"][0]
    assert entry["status"] == "planned"  # unchanged
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/workspace/project/rdd-workflow python3 -m pytest tests/unit/test_iteration_repair.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skills._lib.iteration.repair'`

- [ ] **Step 3: Write minimal implementation**

Create `skills/_lib/iteration/repair.py`:

```python
"""On-disk reconciliation helpers for iteration.json after archive.

When `mark_iteration_archived` (bash wrapper around sync_iteration_after_archive)
fails to update iteration.json — typically due to a transient exception in the
Python helper — this module provides a deterministic fallback: scan the
on-disk archive directory and force-set the iteration entry.
"""
from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _find_archive_dir(project_root: str, change_name: str) -> Optional[str]:
    """Locate the archive directory for a change.

    Returns the path of `openspec/changes/archive/<date>-<change_name>/` if it
    exists, otherwise None.
    """
    pattern = os.path.join(
        project_root, "openspec", "changes", "archive", f"*-{change_name}"
    )
    matches = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    return matches[0] if matches else None


def force_mark_archived(
    project_root: str,
    change_name: str,
    archive_commit_sha: Optional[str] = None,
) -> bool:
    """Force-mark a change as archived in iteration.json from on-disk truth.

    Returns True if iteration.json was modified, False if no-op.

    Idempotent: if the entry already has `archived_at`, only forces status
    to 'archived' (preserves the original timestamp).
    """
    archive_dir = _find_archive_dir(project_root, change_name)
    if archive_dir is None:
        return False

    iter_file = Path(project_root) / ".rddf" / "state" / "iteration.json"
    if not iter_file.is_file():
        return False

    try:
        data = json.loads(iter_file.read_text())
    except (json.JSONDecodeError, OSError):
        return False

    changes = data.get("changes", [])
    existing = None
    for c in changes:
        if c.get("name") == change_name:
            existing = c
            break
    if existing is None:
        # Create a synthetic entry so future lookups don't fail
        existing = {"name": change_name, "added_at": datetime.now(timezone.utc).isoformat()}
        changes.append(existing)

    fields: = {}
    if existing.get("status") != "archived":
        fields["status"] = "archived"
    if "archived_at" not in existing:
        fields["archived_at"] = datetime.now(timezone.utc).isoformat()
    if archive_commit_sha and "archive_commit_sha" not in existing:
        fields["archive_commit_sha"] = archive_commit_sha

    if not fields:
        return False

    existing.update(fields)
    data["changes"] = changes

    iter_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/workspace/project/rdd-workflow python3 -m pytest tests/unit/test_iteration_repair.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Defer commit**

按仓库约定,execute 阶段不逐任务 commit;所有变更将在 archive 阶段统一提交。

---

### Task 2: Add bash wrapper `reconcile_iteration_from_disk` and wire into archive_change_for_mode

**Files:**
- Modify: `skills/guide-ship/scripts/ship_archive.sh` (add helper + insert call)
- Modify: `skills/_lib/archive.sh` (add `reconcile` subcommand)

- [ ] **Step 1: Write the failing bats test**

Create `tests/integration/test_archive_iteration_sync_resilience.bats`:

```bash
#!/usr/bin/env bats

load test_helper

setup() {
    TEST_PROJECT_ROOT="$(mktemp -d)"
    cd "$TEST_PROJECT_ROOT" || exit 1
    git init -q .
    mkdir -p .rddf/state openspec/changes/archive/2026-08-16-test-change
    echo '{"version": 7, "changes": [{"name": "test-change", "status": "planned", "added_at": "2026-08-16T00:00:00Z"}]}' > .rddf/state/iteration.json
    touch openspec/changes/archive/2026-08-16-test-change/proposal.md
}

teardown() {
    cd /
    rm -rf "$TEST_PROJECT_ROOT"
}

@test "force_mark_archived writes status=archived to iteration.json" {
    SKILLS_PARENT="/workspace/project/rdd-workflow" \
    MAIN_ROOT="$TEST_PROJECT_ROOT" \
    CHANGE_NAME="test-change" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib.iteration.repair import force_mark_archived
result = force_mark_archived(os.environ['MAIN_ROOT'], os.environ['CHANGE_NAME'])
assert result, 'force_mark_archived should return True'
"

    grep -q '"status": "archived"' .rddf/state/iteration.json
}

@test "force_mark_archived no-op when archive dir missing" {
    rm -rf openspec/changes/archive/2026-08-16-test-change

    SKILLS_PARENT="/workspace/project/rdd-workflow" \
    MAIN_ROOT="$TEST_PROJECT_ROOT" \
    CHANGE_NAME="test-change" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib.iteration.repair import force_mark_archived
result = force_mark_archived(os.environ['MAIN_ROOT'], os.environ['CHANGE_NAME'])
assert not result, 'force_mark_archived should return False when no archive dir'
"
}

@test "force_mark_archived idempotent (second call is no-op)" {
    SKILLS_PARENT="/workspace/project/rdd-workflow" \
    MAIN_ROOT="$TEST_PROJECT_ROOT" \
    CHANGE_NAME="test-change" \
        python3 -c "
import os, sys
sys.path.insert(0, os.environ['SKILLS_PARENT'])
from skills._lib.iteration.repair import force_mark_archived
r1 = force_mark_archived(os.environ['MAIN_ROOT'], os.environ['CHANGE_NAME'])
r2 = force_mark_archived(os.environ['MAIN_ROOT'], os.environ['CHANGE_NAME'])
assert r1 and not r2, f'expected r1=True, r2=False, got r1={r1}, r2={r2}'
"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_archive_iteration_sync_resilience.bats`
Expected: FAIL (file not found)

- [ ] **Step 3: Write minimal implementation**

Modify `skills/guide-ship/scripts/ship_archive.sh`. Find the `archive_change_for_mode` function, locate the existing `mark_iteration_archived` call (around line 247), and add the reconciliation call immediately after:

```bash
# After the existing:
#   mark_iteration_archived "$change_name" "$project_root" "$archive_commit_sha"

# Insert:
if [ "${FORCE_ITERATION_BACKFILL:-yes}" = "yes" ]; then
    SKILLS_PARENT="${HOME}/.agents/skills" \
    MAIN_ROOT="$project_root" \
    CHANGE_NAME="$change_name" \
    ARCHIVE_COMMIT_SHA="$archive_commit_sha" \
        python3 -c '
import os, sys
sys.path.insert(0, os.environ["SKILLS_PARENT"])
try:
    from skills._lib.iteration.repair import force_mark_archived
except ImportError as e:
    print(f"⚠️  repair module unavailable: {e}", file=sys.stderr)
    sys.exit(0)
try:
    main_root = os.environ["MAIN_ROOT"]
    change_name = os.environ["CHANGE_NAME"]
    sha = os.environ.get("ARCHIVE_COMMIT_SHA") or None
    modified = force_mark_archived(main_root, change_name, archive_commit_sha=sha)
    if modified:
        print(f"⚠️ iteration.json sync failed — auto-recovered via on-disk scan for {change_name}", file=sys.stderr)
except Exception as e:
    print(f"⚠️ on-disk reconciliation failed: {e}", file=sys.stderr)
' || true
fi
```

Then append a `reconcile` subcommand to `skills/_lib/archive.sh`. Open the file and find the trailing section. Add:

```bash
# reconcile [project_root]
#   Manual on-disk backfill: scan archive/ for entries missing iteration.json
#   archived_at, force-set them. Idempotent.
reconcile() {
  local project_root="${1:-$PWD}"
  local archive_dir="$project_root/openspec/changes/archive"
  [ -d "$archive_dir" ] || { echo "❌ No archive dir at $archive_dir"; return 1; }

  echo "🔍 Scanning $archive_dir for stale iteration.json entries..."

  local skills_parent
  skills_parent="$(cd "$_LIB_DIR/../.." 2>/dev/null && pwd)"

  local fixed=0 skipped=0
  for d in "$archive_dir"/*/; do
    [ -d "$d" ] || continue
    local dir_name
    dir_name=$(basename "$d")
    # Extract change name from <date>-<change-name> pattern
    local change_name="${dir_name#*-}"
    [ -z "$change_name" ] && continue

    local result
    result=$(SKILLS_PARENT="$skills_parent" \
             MAIN_ROOT="$project_root" \
             CHANGE_NAME="$change_name" \
             python3 -c '
import os, sys
sys.path.insert(0, os.environ["SKILLS_PARENT"])
try:
    from skills._lib.iteration.repair import force_mark_archived
except ImportError:
    print("error:module")
    sys.exit(0)
modified = force_mark_archived(os.environ["MAIN_ROOT"], os.environ["CHANGE_NAME"])
print("fixed" if modified else "skipped")
' 2>/dev/null)
    case "$result" in
      fixed)   echo "  ✅ $change_name: fixed"; fixed=$((fixed+1)) ;;
      skipped) echo "  ⏭️  $change_name: already synced"; skipped=$((skipped+1)) ;;
      *)       echo "  ⚠️  $change_name: $result" ;;
    esac
  done

  echo ""
  echo "Summary: $fixed fixed, $skipped skipped"
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_archive_iteration_sync_resilience.bats`
Expected: PASS (3 cases)

- [ ] **Step 5: Defer commit**

按仓库约定,execute 阶段不逐任务 commit;所有变更将在 archive 阶段统一提交。

---

### Task 3: Document manual recovery workflow

**Files:**
- Create: `docs/operations/archive-state-recovery.md`

- [ ] **Step 1: Write the failing test**

N/A — documentation task; verification is manual review of file existence.

- [ ] **Step 2: Run test to verify it fails**

Run: `test -f docs/operations/archive-state-recovery.md`
Expected: FAIL with "No such file or directory"

- [ ] **Step 3: Write minimal implementation**

Create `docs/operations/archive-state-recovery.md`:

```markdown
# Archive State Recovery Guide

## 症状

当 `iteration.json` 与 `openspec/changes/archive/` 实际状态不一致时,`rddf status` 会显示不一致的视图:

```bash
$ rddf status
📋 planned  harden-archive-iteration-sync   # 但 openspec/changes/archive/2026-08-16-harden-archive-iteration-sync/ 已存在
```

## 手动修复 (3 步)

1. **运行 reconcile**:
   ```bash
   bash skills/_lib/archive.sh reconcile .
   ```

2. **验证**:
   ```bash
   rddf status | grep harden-archive-iteration-sync
   # 应显示 📦 archived
   ```

3. **如果 iteration.json 被修改,提交**:
   ```bash
   git add .rddf/state/iteration.json
   git commit -m "fix(iteration): reconcile stale archive entries"
   ```

## Opt-out

设置 `FORCE_ITERATION_BACKFILL=no` 关闭 archive 主流程的自动 reconciliation:

```bash
FORCE_ITERATION_BACKFILL=no bash skills/guide-ship/scripts/ship_archive.sh
```

## 快速验证

```bash
# 一行命令: 检测 stale planned + 已存在 archive dir 的 change
comm -12 \
  <(rddf status --json | jq -r '.changes[] | select(.status=="planned") | .name' | sort) \
  <(ls openspec/changes/archive/ | sed 's/^[0-9-]*//' | sort -u) | \
  while read -r name; do [ -d "openspec/changes/archive"/*-"$name" ] && echo "STALE: $name"; done
```

如输出任何 STALE 行,运行 reconcile。
```

- [ ] **Step 4: Run test to verify it passes**

Run: `test -f docs/operations/archive-state-recovery.md && echo OK`
Expected: `OK`

- [ ] **Step 5: Defer commit**

按仓库约定,execute 阶段不逐任务 commit;所有变更将在 archive 阶段统一提交。

---

### Task 4: Run regression test suite

**Files:** N/A (verification only)

- [ ] **Step 1: Run unit tests**

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: PASS (no regressions in existing unit tests)

- [ ] **Step 2: Run new bats tests**

Run: `bats tests/integration/test_archive_iteration_sync_resilience.bats`
Expected: PASS (3/3 cases)

- [ ] **Step 3: Run smoke tests**

Run: `bats tests/smoke.bats`
Expected: PASS (no regressions)

- [ ] **Step 4: Run openspec validate**

Run: `openspec validate harden-archive-iteration-sync`
Expected: PASS

- [ ] **Step 5: Defer commit**

按仓库约定,execute 阶段不逐任务 commit;所有变更将在 archive 阶段统一提交。

---

## Self-Review Checklist

- [x] Spec coverage: all 4 requirements have at least one task (Task 1 implements core helper, Task 2 wires it + exposes subcommand, Task 3 documents)
- [x] No placeholders: every step has concrete code/file paths
- [x] Type consistency: `force_mark_archived(project_root, change_name, archive_commit_sha=None)` signature consistent across Tasks 1, 2, and bats tests
- [x] Files match: production code in `skills/_lib/iteration/repair.py`, tests in `tests/unit/test_iteration_repair.py` + `tests/integration/test_archive_iteration_sync_resilience.bats`