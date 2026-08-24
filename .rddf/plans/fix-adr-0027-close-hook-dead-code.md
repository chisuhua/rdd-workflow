# fix-adr-0027-close-hook-dead-code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revive the dead `close_issues_for_change_hook` per ADR-0027 §6. Two bugs: (1) `_load_issue_refs` reads PRE-archive path while hook runs POST-archive; (2) `_update_local_issue_files` matches by `dedup_hash` (always 8-hex) against issue numbers (always integer) — never matches.

**Architecture:** Add archive-fallback to `_load_issue_refs` (try active path first, then `archive/<date>-<name>/roadmap-meta.yaml`). Fix matching to scan submitted_url field for `/issues/<n>`. Keep public API signatures unchanged.

**Tech Stack:** Python 3.11+, pytest, bats

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/close_issues.py` | Fix `_load_issue_refs` (path fallback) and `_update_local_issue_files` (match by submitted_url) |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_close_issues_post_archive.py` | **NEW** — 3 tests: archive fallback, submitted_url matching, no-refs early return |
| `tests/integration/test_archive_close_dual_mode.bats` | **MODIFY** — delete line 26 wrong assertion + add round-trip test for real post-archive path |

---

### Task 1: Fix `_load_issue_refs` with archive fallback

**Files:**
- Modify: `_lib/close_issues.py:129-144` (`_load_issue_refs` function)
- Test: `tests/unit/test_close_issues_post_archive.py` (NEW)

- [ ] **Step 1: Write failing test in `tests/unit/test_close_issues_post_archive.py`**

Create the file with the first test:

```python
"""Tests for fix-adr-0027-close-hook-dead-code: archive path fallback + submitted_url matching."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest


def test_load_issue_refs_archive_fallback(tmp_path: Path) -> None:
    """After openspec archive, the change dir is moved to archive/<date>-<name>/.

    The hook must find the roadmap-meta.yaml in either the active path
    OR the post-archive path. This test simulates the post-archive layout
    (only archive/<date>-<name>/roadmap-meta.yaml exists).
    """
    from close_issues import _load_issue_refs  # type: ignore[import-not-found]

    archive_dir = tmp_path / "openspec" / "changes" / "archive" / "2026-08-24-add-foo"
    archive_dir.mkdir(parents=True)
    (archive_dir / "roadmap-meta.yaml").write_text(dedent("""\
        name: add-foo
        issue_refs:
          - 42
          - 123
        gh_repo: my-org/my-repo
    """), encoding="utf-8")

    refs, gh_repo = _load_issue_refs("add-foo", str(tmp_path))
    assert refs == [42, 123], f"expected [42, 123], got {refs}"
    assert gh_repo == "my-org/my-repo", f"expected my-org/my-repo, got {gh_repo}"
```

- [ ] **Step 2: Run test to verify it fails (RED)**

Run: `python3 -m pytest tests/unit/test_close_issues_post_archive.py -v`
Expected: FAIL with `assert [] == [42, 123]` (current code returns empty because active path doesn't exist).

- [ ] **Step 3: Add archive-path fallback to `_load_issue_refs`**

Replace the body of `_load_issue_refs` (lines 129-144) with:

```python
def _load_issue_refs(change_name: str, project_root: str) -> tuple:
    """Read ``roadmap-meta.yaml`` for ``issue_refs`` + ``gh_repo``.

    **ADR-0027 §6 / fix-adr-0027-close-hook-dead-code**: try the active
    path first (pre-archive layout: ``openspec/changes/<name>/``). If
    not found, fall back to the post-archive layout. ``openspec
    archive`` moves files to ``archive/<YYYY-MM-DD>-<name>/`` where
    the date is the archive day. We glob the archive dir for any
    ``<date>-<name>`` entry — the change_name suffix is the stable
    identifier since dates are dynamic.

    Returns ``([], "chisuhua/rdd-workflow")`` when neither path exists
    (safe no-op for changes without a roadmap-meta.yaml).
    """
    if yaml is None:
        return [], "chisuhua/rdd-workflow"
    base = Path(project_root) / "openspec" / "changes"

    # Candidate paths in priority order: active > post-archive (date-prefixed)
    candidates = [
        base / change_name / "roadmap-meta.yaml",
    ]
    # Find any archive/<date>-<name>/roadmap-meta.yaml whose suffix matches
    archive_base = base / "archive"
    if archive_base.is_dir():
        for child in archive_base.iterdir():
            if child.is_dir() and child.name.endswith(f"-{change_name}"):
                candidates.append(child / "roadmap-meta.yaml")

    for meta_path in candidates:
        if not meta_path.is_file():
            continue
        try:
            data = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        refs = data.get("issue_refs") or []
        if not isinstance(refs, list):
            refs = []
        gh_repo = data.get("gh_repo") or "chisuhua/rdd-workflow"
        return [int(r) for r in refs if str(r).isdigit()], gh_repo

    return [], "chisuhua/rdd-workflow"
```

- [ ] **Step 4: Run test to verify it passes (GREEN)**

Run: `python3 -m pytest tests/unit/test_close_issues_post_archive.py::test_load_issue_refs_archive_fallback -v`
Expected: PASS.

- [ ] **Step 5: Defer commit**

---

### Task 2: Fix `_update_local_issue_files` to match by `submitted_url`

**Files:**
- Modify: `_lib/close_issues.py:195-212` (`_update_local_issue_files` function)
- Test: `tests/unit/test_close_issues_post_archive.py` (append second test)

- [ ] **Step 1: Append failing test**

Append to `tests/unit/test_close_issues_post_archive.py`:

```python
def test_update_local_issue_files_matches_by_submitted_url(tmp_path: Path) -> None:
    """closed_at must be written when local issue file's submitted_url contains /issues/<n>.

    Pre-fix bug: code matched on dedup_hash (always 8-hex from stack
    normalization) against issue_number (always integer) — never
    matched. Fix matches on submitted_url like 'github.com/.../issues/42'.
    """
    from close_issues import _update_local_issue_files, CloseResult  # type: ignore[import-not-found]

    issues_dir = tmp_path / ".rddf" / "issues"
    issues_dir.mkdir(parents=True)
    issue_file = issues_dir / "flow-bug-aabbccdd.md"
    issue_file.write_text(dedent("""\
        ---
        category: "flow-bug"
        submitted: true
        submitted_url: "https://github.com/chisuhua/rdd-workflow/issues/42"
        dedup_hash: "aabbccdd"
        ---
        ## Description

        some bug
    """), encoding="utf-8")

    result = CloseResult(closed=[42], skipped=[], manual_links=[], errors=[])
    _update_local_issue_files([42], str(tmp_path), result)

    text = issue_file.read_text(encoding="utf-8")
    assert "closed_at:" in text, f"closed_at not written: {text}"
    assert "closed_ref: 42" in text, f"closed_ref not written: {text}"
```

- [ ] **Step 2: Run test to verify it fails (RED)**

Run: `python3 -m pytest tests/unit/test_close_issues_post_archive.py::test_update_local_issue_files_matches_by_submitted_url -v`
Expected: FAIL with `assert 'closed_at:' in text` (current dedup_hash match fails).

- [ ] **Step 3: Replace `_update_local_issue_files` matching logic**

Replace the function `_update_local_issue_files` (lines 195-212) with:

```python
def _update_local_issue_files(refs: List[int], project_root: str, result: CloseResult) -> None:
    """Mark the corresponding local issue files with the close outcome.

    **fix-adr-0027-close-hook-dead-code**: matches a local issue file
    to ``refs`` by scanning its ``submitted_url`` for ``/issues/<n>``
    (not by ``dedup_hash``, which is 8-hex and never collides with the
    integer issue number).
    """
    issues_dir = Path(project_root) / ".rddf" / "issues"
    if not issues_dir.is_dir():
        return
    closed_set = set(result.closed)
    skipped_set = set(result.skipped)
    for path in issues_dir.glob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for ref in refs:
            # Match by submitted_url containing /issues/<n>
            if f"/issues/{ref}" not in text:
                continue
            if ref in closed_set or ref in skipped_set:
                _append_close_marker(path, text, ref)
            break
```

- [ ] **Step 4: Run test to verify it passes (GREEN)**

Run: `python3 -m pytest tests/unit/test_close_issues_post_archive.py::test_update_local_issue_files_matches_by_submitted_url -v`
Expected: PASS.

- [ ] **Step 5: Defer commit**

---

### Task 3: Add early-return test for empty `issue_refs`

**Files:**
- Test: `tests/unit/test_close_issues_post_archive.py` (append third test)

- [ ] **Step 1: Append failing test**

Append to `tests/unit/test_close_issues_post_archive.py`:

```python
def test_close_issues_early_return_when_no_refs(tmp_path: Path, monkeypatch) -> None:
    """When issue_refs is empty, hook must early-return without touching local files."""
    from close_issues import close_issues_for_change, _load_issue_refs  # type: ignore[import-not-found]

    # Arrange: change with empty issue_refs (active path)
    change_dir = tmp_path / "openspec" / "changes" / "empty-refs"
    change_dir.mkdir(parents=True)
    (change_dir / "roadmap-meta.yaml").write_text(
        "name: empty-refs\nissue_refs: []\n", encoding="utf-8"
    )

    # Arrange: local issue file that must NOT be modified
    issues_dir = tmp_path / ".rddf" / "issues"
    issues_dir.mkdir(parents=True)
    issue_file = issues_dir / "flow-bug-deadbeef.md"
    original_text = 'submitted: true\nsubmitted_url: "https://github.com/x/y/issues/7"\n'
    issue_file.write_text(original_text, encoding="utf-8")

    # Act
    refs, _ = _load_issue_refs("empty-refs", str(tmp_path))
    assert refs == [], f"_load_issue_refs should return [], got {refs}"

    result = close_issues_for_change("empty-refs", str(tmp_path))
    assert result.closed == []
    assert result.skipped == []
    assert result.errors == []
    assert result.manual_links == []

    # Local file untouched
    assert issue_file.read_text(encoding="utf-8") == original_text
```

- [ ] **Step 2: Run test to verify it passes (GREEN, no code change needed)**

Run: `python3 -m pytest tests/unit/test_close_issues_post_archive.py::test_close_issues_early_return_when_no_refs -v`
Expected: PASS (this codifies existing behavior; the bug is in the OTHER path).

- [ ] **Step 3: Defer commit**

---

### Task 4: Update bats integration test (`test_archive_close_dual_mode.bats`)

**Files:**
- Modify: `tests/integration/test_archive_close_dual_mode.bats:26` (delete wrong assertion)
- Modify: `tests/integration/test_archive_close_dual_mode.bats` (add round-trip test)

- [ ] **Step 1: Read the existing bats test**

Run: `cat tests/integration/test_archive_close_dual_mode.bats`

- [ ] **Step 2: Delete line 26 assertion that hardcodes "hook 必须在 openspec archive 之后"**

The line contains a shell assertion that hardcodes the line number sequence "openspec archive … then close hook". Replace it with a comment that documents the new invariant: "hook runs after archive, BUT must work whether archive succeeded or failed (via path fallback)".

Concretely: locate the `@test` block that has the line-26 assertion. If it appears at line 26 within a `@test` body, edit that test to:
- Remove the assertion checking line order
- Add a new assertion that verifies the hook finds the issue_refs when the file is at `archive/<date>-<name>/`

If the existing bats test already covers round-trip behavior, just delete the line-26 assertion and leave a `# FIX: line-order check was enforcing an implementation detail; see PR-2 fix-tasks-md-archive-residue`.

- [ ] **Step 3: Add a new `@test` block for real post-archive path**

Append a new test:

```bats
@test "close hook finds issue_refs in archive/<date>-<name>/roadmap-meta.yaml (post-archive path)" {
    # Simulate the post-archive layout: change dir is GONE from
    # openspec/changes/<name>/, present only in archive/<date>-<name>/
    archive_dir="${TEST_TMPDIR}/openspec/changes/archive/2026-08-24-fake-change"
    mkdir -p "$archive_dir"
    cat > "$archive_dir/roadmap-meta.yaml" <<EOF
name: fake-change
issue_refs:
  - 42
gh_repo: test-owner/test-repo
EOF

    # Run the Python loader directly
    run python3 -c "
import sys
sys.path.insert(0, '${TEST_TMPDIR}')
from close_issues import _load_issue_refs
refs, gh_repo = _load_issue_refs('fake-change', '${TEST_TMPDIR}')
assert refs == [42], f'refs={refs}'
assert gh_repo == 'test-owner/test-repo', f'gh_repo={gh_repo}'
print('OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK"* ]]
}
```

- [ ] **Step 4: Run bats test**

Run: `bats tests/integration/test_archive_close_dual_mode.bats`
Expected: all tests pass (existing + new). Existing tests should still pass since we only delete a wrong assertion, not add a behavior change.

- [ ] **Step 5: Defer commit**

---

### Task 5: Run full unit test suite

- [ ] **Step 1: Run all unit tests**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -30`
Expected: all pass OR same failure set as `tests/KNOWN_FAILURES.txt` (no NEW failures).

- [ ] **Step 2: If new failures appear, fix them**

For each new failure NOT in baseline: investigate root cause, fix minimally, re-run.

- [ ] **Step 3: Defer commit**

---

### Task 6: Update `openspec/changes/fix-adr-0027-close-hook-dead-code/tasks.md`

**Files:**
- Modify: `openspec/changes/fix-adr-0027-close-hook-dead-code/tasks.md` (in master repo)

- [ ] **Step 1: Mark each completed task as `[x]`**

In `openspec/changes/fix-adr-0027-close-hook-dead-code/tasks.md`:
- [x] Read `proposal.md` fully...
- [x] Identify all `**不**` items...
- [x] Write failing test(s)...
- [x] Verify tests fail (red)...
- [x] Task 1 (G1: hook 顺序) — DELETED
- [x] Task 2 (G1: 回归测试) — DONE
- [x] Task 3 (G1: path fallback)
- [x] Task 4 (G1: 为什么双路径)
- [x] Task 5 (G2: closed_at matching)
- [x] Task 6 (G2: early-return)
- [x] Task 7 (G2: 本地不变)
- [x] Task 8 (no items specified)
- [x] Verify all new tests pass (green)
- [x] Run full unit test suite
- [x] Run integration tests
- [x] Verify no regressions
- [x] Update relevant docstrings/inline comments
- [ ] Update CHANGELOG if user-facing behavior changed (deferred)
- [x] Verify `openspec validate <change>` passes
- [ ] Commit changes with conventional commit message (deferred)

- [ ] **Step 2: Defer commit**

---

### Task 7: Stage changes for archive

- [ ] **Step 1: Verify all changes in worktree**

Run: `cd $WT_PATH && git status --short`
Expected: list of modified + new files.

- [ ] **Step 2: Stage relevant files**

```bash
cd $WT_PATH && git add _lib/close_issues.py \
  tests/unit/test_close_issues_post_archive.py \
  tests/integration/test_archive_close_dual_mode.bats \
  openspec/changes/fix-adr-0027-close-hook-dead-code/tasks.md \
  .rddf/plans/fix-adr-0027-close-hook-dead-code.md
git status --short
```

- [ ] **Step 3: Defer commit (worktree commit at Phase 2.7)**

---

## Acceptance Verification

After all tasks complete:

- [ ] `python3 -m pytest tests/unit/test_close_issues_post_archive.py -v` — 3 passed
- [ ] `python3 -m pytest tests/unit/ -q --tb=short` — no NEW failures
- [ ] `bats tests/integration/test_archive_close_dual_mode.bats` — all pass (existing + new)
- [ ] `openspec validate fix-adr-0027-close-hook-dead-code` → valid

## Out of Scope (DO NOT IMPLEMENT)

- ❌ Changes to `_lib/archive.sh:428` or `skills/guide-ship/scripts/ship_archive.sh:239` call sites
- ❌ Adding retry mechanism
- ❌ Changing retention strategy (30-day default)
- ❌ Refactor of `close_issues_for_change` body — only fix the 2 specific bugs
- ❌ New external dependencies
- ❌ Changes to `openspec archive` CLI behavior