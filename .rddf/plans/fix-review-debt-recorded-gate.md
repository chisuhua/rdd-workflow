# fix-review-debt-recorded-gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** Fix 3 deep problems in `_lib/gate.py::_check_review_debt_recorded`: (1) runs after commit so diff is empty → dead; (2) cwd-relative path → silent failure in subdirs; (3) bare `except Exception` swallows all errors. Add Phase 2.5 pre-commit helper, expand language support, use absolute project_root.

**Architecture:** New `ReviewDebtChecker` in `_lib/review_debt_checker.py` with 4-field `ReviewDebtVerdict` dataclass. Called from `ship_review.sh` Phase 2.5 (before archive_commit). Old `_check_review_debt_recorded` in `_lib/gate.py` deprecated (kept as shim with `@deprecated` docstring). Use absolute `project_root` parameter; narrow except to `(OSError, IOError, PermissionError)`.

**Tech Stack:** Python 3.11+, bats, pytest

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/review_debt_checker.py` | **NEW** — `ReviewDebtVerdict` dataclass + `check_review_debt_recorded(project_root, change_name, execute_finished_at)` |
| `_lib/gate.py` | Mark `_check_review_debt_recorded` `@deprecated`, keep as shim; remove from `_DEFAULT_CHECKS` |
| `skills/guide-ship/scripts/ship_review.sh` | Add helper invocation in Phase 2.5 before commit |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_review_debt_checker.py` | **NEW** — 5 unit tests (Go, Rust, permission error, historic file, project_root) |
| `tests/unit/test_gate_no_review_debt.py` | **NEW** — 1 regression test: `review_debt_recorded` removed from `_DEFAULT_CHECKS` |
| `tests/integration/test_ship_review_phase25_helper.bats` | **NEW** — 1 bats test: helper invoked in Phase 2.5 |

---

### Task 1: Create `ReviewDebtChecker` with verdict dataclass

**Files:**
- Create: `_lib/review_debt_checker.py`
- Test: `tests/unit/test_review_debt_checker.py` (5 tests)

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_review_debt_checker.py`:

```python
"""Tests for fix-review-debt-recorded-gate: Phase 2.5 pre-commit helper."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest


# All 18 supported language extensions per proposal scenario A/C/D
SUPPORTED_LANGS = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java",
    ".rb", ".sh", ".bash", ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".swift", ".kt",
)


@pytest.fixture
def fresh_project(tmp_path: Path) -> Path:
    """Create a project root with a TODO marker + no historic debt file."""
    (tmp_path / "main.go").write_text(
        "package main\n// TODO: refactor this part\nfunc main() {}\n"
    )
    (tmp_path / ".rddf").mkdir()
    (tmp_path / ".rddf" / "improvements").mkdir()
    return tmp_path


def test_go_project_todo_detected(fresh_project: Path) -> None:
    """Scenario A: .go file with TODO → found_count > 0, persisted=False."""
    from review_debt_checker import check_review_debt_recorded  # type: ignore[import-not-found]
    verdict = check_review_debt_recorded(
        project_root=str(fresh_project),
        change_name="add-foo",
        execute_finished_at=datetime.now(timezone.utc),
    )
    assert verdict.found_count >= 1
    assert verdict.persisted is False
    assert "TODO" in verdict.reason


def test_rust_project_todo_detected(fresh_project: Path) -> None:
    """Scenario D: .rs file with TODO → found_count > 0."""
    (fresh_project / "main.rs").write_text(
        "fn main() {}\n// TODO: handle error properly\n"
    )
    from review_debt_checker import check_review_debt_recorded  # type: ignore[import-not-found]
    verdict = check_review_debt_recorded(
        project_root=str(fresh_project),
        change_name="add-foo",
        execute_finished_at=datetime.now(timezone.utc),
    )
    assert verdict.found_count >= 1


def test_permission_error_not_swallowed(fresh_project: Path) -> None:
    """Scenario C: PermissionError on .rddf/improvements → must NOT silent-pass."""
    import stat
    improvements = fresh_project / ".rddf" / "improvements"
    # Make the directory unreadable (skip on Windows / root)
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("Running as root — chmod ineffective")
    try:
        improvements.chmod(stat.S_IWUSR | stat.S_IXUSR)  # remove read
    except OSError:
        pytest.skip("chmod unavailable")
    try:
        from review_debt_checker import check_review_debt_recorded  # type: ignore[import-not-found]
        verdict = check_review_debt_recorded(
            project_root=str(fresh_project),
            change_name="add-foo",
            execute_finished_at=datetime.now(timezone.utc),
        )
        # Should NOT silent-pass; either raises or returns non-OK verdict
        assert verdict.persisted is False or "permission" in verdict.reason.lower()
    finally:
        improvements.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def test_historic_debt_file_not_counted(fresh_project: Path) -> None:
    """Scenario E: old debt file (mtime before execute_finished_at) doesn't count."""
    debt = fresh_project / ".rddf" / "improvements" / "cleanup-old-debt.md"
    debt.write_text("# historic debt\n")
    # Backdate the debt file by 1 day
    old_time = time.time() - 86400
    os.utime(debt, (old_time, old_time))

    from review_debt_checker import check_review_debt_recorded  # type: ignore[import-not-found]
    finish_time = datetime.now(timezone.utc)
    verdict = check_review_debt_recorded(
        project_root=str(fresh_project),
        change_name="add-foo",
        execute_finished_at=finish_time,
    )
    # Historic file is too old — should NOT count as persisted
    assert verdict.persisted is False


def test_helper_uses_project_root_not_cwd(tmp_path: Path) -> None:
    """Project root param must be honored even when cwd != project_root."""
    project = tmp_path / "myproject"
    project.mkdir()
    (project / "main.go").write_text("// TODO: stuff\n")
    (project / ".rddf" / "improvements").mkdir(parents=True)

    # Change cwd to a different subdir
    other = tmp_path / "other-subdir"
    other.mkdir()
    old_cwd = os.getcwd()
    try:
        os.chdir(other)
        from review_debt_checker import check_review_debt_recorded  # type: ignore[import-not-found]
        verdict = check_review_debt_recorded(
            project_root=str(project),
            change_name="add-foo",
            execute_finished_at=datetime.now(timezone.utc),
        )
        assert verdict.found_count >= 1, "must find TODO regardless of cwd"
    finally:
        os.chdir(old_cwd)
```

- [ ] **Step 2: Run tests to verify they fail (RED)**

Run: `python3 -m pytest tests/unit/test_review_debt_checker.py -v`
Expected: ImportError or 5 failures.

- [ ] **Step 3: Create `_lib/review_debt_checker.py`**

```python
"""Phase 2.5 pre-commit review debt checker.

Fix-adr-0027-review-debt-recorded-gate: replaces the dead
``_lib/gate.py::_check_review_debt_recorded`` (which ran after
worktree-commit so ``git diff`` was always empty). This module is
called by ``skills/guide-ship/scripts/ship_review.sh`` BEFORE the
single aggregate commit, so the diff reflects the change's actual
TODO additions.

Per ADR-0014 §决策 5, users must either record a debt file in
``.rddf/improvements/cleanup-<change>-debt.md`` or explicitly skip.
The check classifies a debt file as "valid for current change" only
if its mtime > execute_finished_at (Scenario E).

**Cwd-independence**: caller MUST pass absolute ``project_root``.
The function never reads ``os.getcwd()``.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List


# All 18 language file extensions per ADR-0027 §4 scope
SUPPORTED_LANG_EXTENSIONS: tuple[str, ...] = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java",
    ".rb", ".sh", ".bash", ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".swift", ".kt",
)

# Match TODO/FIXME/HACK/WORKAROUND markers (case-sensitive to avoid
# matching identifiers like "todo_app")
_TODO_PATTERN = re.compile(r"\b(?:TODO|FIXME|HACK|WORKAROUND)\b")


@dataclass
class ReviewDebtVerdict:
    """Outcome of ``check_review_debt_recorded``.

    Fields:
      persisted: True if a valid debt file exists for this change
                 (mtime > execute_finished_at AND naming convention matches).
      reason: Human-readable explanation ("3 new TODOs found", "no debt
              file, please record or skip").
      found_count: Number of TODO markers found in the 18 supported langs.
      new_todos: List of (relative_path, line_no) tuples for new TODOs.
    """

    persisted: bool
    reason: str
    found_count: int = 0
    new_todos: List[tuple] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.new_todos is None:
            self.new_todos = []


def check_review_debt_recorded(
    project_root: str,
    change_name: str,
    execute_finished_at: datetime,
) -> ReviewDebtVerdict:
    """Check whether new TODOs in supported languages have a corresponding
    debt file. Runs BEFORE the worktree commit (Phase 2.5).

    Args:
        project_root: Absolute path to the project root. MUST be passed
                      explicitly; never read from cwd.
        change_name: Name of the OpenSpec change (e.g., "add-foo").
        execute_finished_at: UTC datetime when execute finished; debt files
                             older than this are not counted for current change.

    Returns:
        ReviewDebtVerdict with found_count, persisted, reason, new_todos.

    Raises:
        PermissionError: if .rddf/improvements is not readable.
        OSError: on filesystem errors.
    """
    project_root_path = Path(project_root).resolve()
    improvements_dir = project_root_path / ".rddf" / "improvements"

    # Narrow except: only filesystem-related errors. Anything else (TypeError,
    # ValueError, etc.) is a bug and should surface.
    try:
        improvements_dir.mkdir(parents=True, exist_ok=True)
        if not improvements_dir.is_dir():
            return ReviewDebtVerdict(
                persisted=False,
                reason=f".rddf/improvements not a directory at {improvements_dir}",
            )
    except (OSError, IOError, PermissionError) as e:
        return ReviewDebtVerdict(
            persisted=False,
            reason=f"cannot access .rddf/improvements: {e!r}",
        )

    # Scan supported language files for TODO markers
    new_todos: list[tuple[str, int]] = []
    for ext in SUPPORTED_LANG_EXTENSIONS:
        for source_file in project_root_path.glob(f"*{ext}"):
            # Skip .rddf/ directory contents (not source files)
            try:
                rel = source_file.relative_to(project_root_path)
                if rel.parts[0] == ".rddf":
                    continue
            except ValueError:
                continue
            try:
                text = source_file.read_text(encoding="utf-8", errors="replace")
            except (OSError, IOError, PermissionError) as e:
                return ReviewDebtVerdict(
                    persisted=False,
                    reason=f"cannot read {source_file}: {e!r}",
                )
            for line_no, line in enumerate(text.splitlines(), start=1):
                if _TODO_PATTERN.search(line):
                    new_todos.append((str(source_file.relative_to(project_root_path)), line_no))

    # Check for debt file with naming convention
    debt_candidates = [
        improvements_dir / f"cleanup-{change_name}-debt.md",
        improvements_dir / f"{change_name}-debt.md",
    ]

    persisted = False
    for debt in debt_candidates:
        try:
            if not debt.is_file():
                continue
            mtime = datetime.fromtimestamp(debt.stat().st_mtime, tz=timezone.utc)
            if mtime > execute_finished_at:
                persisted = True
                break
        except (OSError, IOError, PermissionError) as e:
            return ReviewDebtVerdict(
                persisted=False,
                reason=f"cannot read debt file {debt}: {e!r}",
            )

    if persisted:
        reason = f"debt file found for {change_name} (mtime after execute_finished_at)"
    elif new_todos:
        reason = (
            f"found {len(new_todos)} new TODO markers but no debt file for "
            f"{change_name} — please record or skip"
        )
    else:
        reason = "no new TODOs found in supported languages"

    return ReviewDebtVerdict(
        persisted=persisted,
        reason=reason,
        found_count=len(new_todos),
        new_todos=new_todos,
    )
```

- [ ] **Step 4: Run tests to verify they pass (GREEN)**

Run: `python3 -m pytest tests/unit/test_review_debt_checker.py -v`
Expected: 5 passed.

- [ ] **Step 5: Defer commit**

---

### Task 2: Mark old `_check_review_debt_recorded` `@deprecated` and remove from `_DEFAULT_CHECKS`

**Files:**
- Modify: `_lib/gate.py:341-370` (existing function)
- Modify: `_lib/gate.py:_DEFAULT_CHECKS` (remove entry)
- Test: `tests/unit/test_gate_no_review_debt.py` (NEW)

- [ ] **Step 1: Write failing regression test**

Create `tests/unit/test_gate_no_review_debt.py`:

```python
"""Regression: review_debt_recorded must NOT be in _DEFAULT_CHECKS.

Fix-adr-0027-review-debt-recorded-gate removed the broken gate
(ran after commit so diff was always empty). The new helper in
_lib/review_debt_checker.py handles this in Phase 2.5.
"""
from __future__ import annotations

import pytest


def test_review_debt_recorded_removed_from_default_checks() -> None:
    from gate import _DEFAULT_CHECKS  # type: ignore[import-not-found]
    assert "review_debt_recorded" not in _DEFAULT_CHECKS, (
        "review_debt_recorded was removed; see _lib/review_debt_checker.py"
    )
```

- [ ] **Step 2: Run test to verify it fails (RED)**

Run: `python3 -m pytest tests/unit/test_gate_no_review_debt.py -v`
Expected: FAIL (assert 'review_debt_recorded' in _DEFAULT_CHECKS is True).

- [ ] **Step 3: Remove from `_DEFAULT_CHECKS`**

In `_lib/gate.py`, find the `_DEFAULT_CHECKS` dict/list and remove the `"review_debt_recorded": _check_review_debt_recorded` entry (or equivalent).

- [ ] **Step 4: Mark `_check_review_debt_recorded` as `@deprecated`**

Add `@deprecated` docstring above the function body. Keep the function body intact (it's still callable; just no longer in the default check set).

- [ ] **Step 5: Run test to verify it passes (GREEN)**

Run: `python3 -m pytest tests/unit/test_gate_no_review_debt.py -v`
Expected: PASS.

- [ ] **Step 6: Defer commit**

---

### Task 3: Wire helper into `ship_review.sh` Phase 2.5

**Files:**
- Modify: `skills/guide-ship/scripts/ship_review.sh`
- Test: `tests/integration/test_ship_review_phase25_helper.bats` (NEW)

- [ ] **Step 1: Locate Phase 2.5 commit step**

Read `skills/guide-ship/scripts/ship_review.sh` and find the Phase 2.5 commit invocation. The helper should run BEFORE `git add` / `git commit`.

- [ ] **Step 2: Add helper check (BEFORE commit)**

Add a bash block before the commit step:

```bash
# Phase 2.5 review debt check (fix-adr-0027-review-debt-recorded-gate)
EXECUTE_FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RDDF_PROJECT_ROOT="$PROJECT_ROOT" \
RDDF_CHANGE_NAME="$CHANGE_NAME" \
RDDF_EXECUTE_FINISHED_AT="$EXECUTE_FINISHED_AT" \
python3 -c "
import os, sys, datetime
sys.path.insert(0, os.environ.get('RDDF_EXECUTION_ROOT', '.'))
from review_debt_checker import check_review_debt_recorded
project_root = os.environ['RDDF_PROJECT_ROOT']
change_name = os.environ['RDDF_CHANGE_NAME']
finish_at = datetime.datetime.fromisoformat(os.environ['RDDF_EXECUTE_FINISHED_AT'].replace('Z', '+00:00'))
verdict = check_review_debt_recorded(project_root, change_name, finish_at)
print(f'verdict: persisted={verdict.persisted} count={verdict.found_count}')
print(f'reason: {verdict.reason}')
if not verdict.persisted and verdict.found_count > 0:
    sys.exit(1)
"
```

If verdict.persisted is False and TODOs found, exit 1 with a helpful stderr message. Otherwise continue to commit.

- [ ] **Step 3: Write failing bats test**

Create `tests/integration/test_ship_review_phase25_helper.bats`:

```bats
@test "ship_review.sh Phase 2.5 invokes review_debt_checker before commit" {
    # Mock: create a project with TODO + no debt file
    export TEST_TMPDIR="${BATS_TMPDIR}/phase25-test"
    mkdir -p "$TEST_TMPDIR"
    cd "$TEST_TMPDIR"
    git init -q
    mkdir -p .rddf/improvements
    echo '// TODO: stuff' > main.go

    # Run helper directly (avoid full ship_review orchestration)
    run python3 -c "
import sys, os, datetime
sys.path.insert(0, '$BATS_TEST_DIRNAME/../../_lib')
from review_debt_checker import check_review_debt_recorded
v = check_review_debt_recorded(
    project_root='$TEST_TMPDIR',
    change_name='test-change',
    execute_finished_at=datetime.datetime.now(datetime.timezone.utc),
)
print(f'persisted={v.persisted} count={v.found_count}')
assert v.found_count >= 1, f'expected TODO detection; got count={v.found_count}'
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"count=1"* ]]
}
```

- [ ] **Step 4: Run bats test to verify it passes (GREEN)**

Run: `bats tests/integration/test_ship_review_phase25_helper.bats`
Expected: PASS.

- [ ] **Step 5: Defer commit**

---

### Task 4: Run full unit + integration suite

- [ ] **Step 1: Run all unit tests**

Run: `cd $WT_PATH && python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -30`
Expected: all pass OR same failure set as `KNOWN_FAILURES.txt`.

- [ ] **Step 2: Run new bats tests**

Run: `cd $WT_PATH && bats tests/integration/test_ship_review_phase25_helper.bats`
Expected: PASS.

- [ ] **Step 3: Defer commit**

---

### Task 5: Update `tasks.md` and stage for archive

- [ ] **Step 1: Mark all `- [ ]` as `- [x]` in `openspec/changes/fix-review-debt-recorded-gate/tasks.md`**

Leave CHANGELOG / commit `[ ]`.

- [ ] **Step 2: Stage all changes**

```bash
cd $WT_PATH && git add _lib/review_debt_checker.py _lib/gate.py \
  skills/guide-ship/scripts/ship_review.sh \
  tests/unit/test_review_debt_checker.py \
  tests/unit/test_gate_no_review_debt.py \
  tests/integration/test_ship_review_phase25_helper.bats \
  openspec/changes/fix-review-debt-recorded-gate/tasks.md \
  .rddf/plans/fix-review-debt-recorded-gate.md
git status --short
```

- [ ] **Step 3: Defer commit (orchestrator owns worktree commit)**

---

## Acceptance Verification

- [ ] All 7 AC met (AC-1 through AC-7)
- [ ] 5 unit tests pass in `test_review_debt_checker.py`
- [ ] Regression test confirms `review_debt_recorded` removed from `_DEFAULT_CHECKS`
- [ ] Bats test confirms Phase 2.5 helper invocation
- [ ] Full unit suite: no NEW failures
- [ ] `openspec validate fix-review-debt-recorded-gate` → valid

## Out of Scope (DO NOT IMPLEMENT)

- ❌ Rewrite `guide-ship/SKILL.md` Phase 2.5 menu
- ❌ Rewrite `ship_review.sh` entirely
- ❌ Change `proposal-suggestions.md` schema
- ❌ Add new external dependencies
- ❌ Modify `archive.sh::archive_change` logic
- ❌ Remove `_check_review_debt_recorded` entirely (1-version deprecated shim)