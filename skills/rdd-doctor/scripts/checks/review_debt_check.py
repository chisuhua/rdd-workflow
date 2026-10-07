"""rdd-doctor category: review-debt (per add-rdd-doctor-coverage-completion).

Scans `.py / .sh / .bats` source files for un-ticketed TODO/FIXME/HACK
markers and emits WARNING Findings. Ticket-referenced markers
(`TODO(RDDF-123)`) are treated as resolved and silent.

Does NOT wrap `_lib.review_debt_checker.check_review_debt_recorded` —
that function is phase-2.5-specific (requires change_name +
execute_finished_at parameters for debt-file mtime check) and not a
generic diagnostic. Re-uses `_TODO_PATTERN` constant instead.

Severity: WARNING (action: add ticket id or remove marker).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity
from _lib.review_debt_checker import _TODO_PATTERN  # noqa: E402


_TICKETED_PATTERN = re.compile(
    r"\b(?:TODO|FIXME|HACK|WORKAROUND)\s*\(\s*[a-zA-Z][\w-]*-\d+\s*\)"
)
_SCAN_EXTENSIONS = (".py", ".sh", ".bats")
_SKIP_TOP_DIRS = (".rddf", "node_modules", "__pycache__", ".git")


def _is_ticketed(line: str) -> bool:
    return bool(_TICKETED_PATTERN.search(line))


def _scan_repo(project_root: Path) -> List[tuple[str, int, str]]:
    """Return (rel_path, line_no, marker_name) for each un-ticketed marker."""
    findings: List[tuple[str, int, str]] = []
    for ext in _SCAN_EXTENSIONS:
        for source_file in project_root.rglob(f"*{ext}"):
            rel = source_file.relative_to(project_root)
            if rel.parts[0] in _SKIP_TOP_DIRS:
                continue
            try:
                text = source_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                if not _TODO_PATTERN.search(line):
                    continue
                if _is_ticketed(line):
                    continue
                m = _TODO_PATTERN.search(line)
                marker = m.group(0) if m else "TODO"
                findings.append((str(rel), line_no, marker))
    return findings


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        import os
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))

    results = _scan_repo(project_root)
    findings: List[Finding] = []
    for rel_path, line_no, marker in results:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="review-debt.unticketed-marker",
            file=rel_path,
            line=line_no,
            snippet=f"new {marker} marker at line {line_no} (no ticket id)",
            fix_hint=f"add ticket id (e.g. {marker}(RDDF-1234)) or remove marker",
        ))
    return findings