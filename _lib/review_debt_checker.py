"""Phase 2.5 pre-commit review debt checker.

Fix-adr-0027-review-debt-recorded-gate: replaces the dead
``_lib/gate.py::_check_review_debt_recorded`` (which ran after
worktree-commit so ``git diff`` was always empty). This module is
called by ``skills/guide-ship/scripts/ship_review.sh`` BEFORE the
single aggregate commit, so the diff reflects the change's actual
TODO additions.

Per ADR-0014, users must either record a debt file in
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


# All 18 language file extensions per ADR-0027 scope
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
      reason: Human-readable explanation.
      found_count: Number of TODO markers found in supported langs.
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

    # Narrow except: only filesystem-related errors.
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
            # Skip .rddf/ directory contents
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
            f"{change_name} - please record or skip"
        )
    else:
        reason = "no new TODOs found in supported languages"

    return ReviewDebtVerdict(
        persisted=persisted,
        reason=reason,
        found_count=len(new_todos),
        new_todos=new_todos,
    )