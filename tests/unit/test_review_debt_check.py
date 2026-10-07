"""Unit tests for skills/rdd-doctor/scripts/checks/review_debt_check.py."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from checks.review_debt_check import run  # noqa: E402


def _make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = tmp_path
    for rel, body in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return repo


def test_review_debt_ticketed_markers_clean(tmp_path: Path):
    """All TODO markers carry ticket ids (e.g. TODO(RDDF-123)) → no findings."""
    repo = _make_repo(tmp_path, {
        "src/foo.py": "x = 1  # TODO(RDDF-123) do thing\n",
    })
    findings = run(project_root=repo)
    assert findings == [], f"expected clean, got: {findings}"


def test_review_debt_bare_marker_warns(tmp_path: Path):
    """Bare TODO (no ticket id) → WARNING."""
    repo = _make_repo(tmp_path, {
        "src/foo.py": "x = 1  # TODO fix this later\n",
    })
    findings = run(project_root=repo)
    bare = [f for f in findings if f.severity == Severity.WARNING and "TODO" in f.snippet]
    assert len(bare) >= 1, f"expected WARNING for bare TODO, got: {findings}"


def test_review_debt_multi_marker_multi_findings(tmp_path: Path):
    """Multiple bare markers across files → multiple findings."""
    repo = _make_repo(tmp_path, {
        "src/foo.py": "# TODO later\n# FIXME too\n",
        "src/bar.py": "# HACK hacky\n",
    })
    findings = run(project_root=repo)
    bare = [f for f in findings if f.severity == Severity.WARNING]
    assert len(bare) >= 3, f"expected ≥3 WARNING, got {len(bare)}: {bare}"


def test_review_debt_skips_rddf_and_no_source_files(tmp_path: Path):
    """No source files or all under .rddf/ → no findings (degraded)."""
    repo = _make_repo(tmp_path, {
        ".rddf/notes.md": "# TODO bare in rddf should be ignored\n",
    })
    findings = run(project_root=repo)
    assert findings == [], f"expected clean (rddf ignored), got: {findings}"