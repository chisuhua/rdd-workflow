"""Tests for migration_residue_check (cat-6).

Detects stale references that ``rddf migrate-improvements --include-docs``
is designed to fix:
- ``](improvements/X)`` markdown links (legacy pre-migration)
- ``](.rddf/.rddf/improvements/X)`` double-prefix bug

The fix_hint field reports the exact command to run.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from checks.migration_residue_check import run as run_check  # noqa: E402


def _write_doc(tmp_path: Path, relpath: str, content: str) -> Path:
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_no_findings_when_repo_clean(tmp_path: Path):
    """No AGENTS.md / format docs / double-prefix → no findings."""
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_agents_md_legacy_link_reports_warning(tmp_path: Path):
    """`](improvements/X)` in AGENTS.md → WARNING with command preview."""
    _write_doc(tmp_path, "AGENTS.md",
        "See [`add-foo`](improvements/add-foo.md) for details.\n")

    findings = run_check(project_root=tmp_path)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == Severity.WARNING
    assert f.category == "migration-residue"
    assert "AGENTS.md" in f.file
    assert "improvements/add-foo.md" in f.snippet
    # fix_hint must include the command preview
    assert "rddf migrate-improvements" in f.fix_hint
    assert "--include-docs" in f.fix_hint


def test_double_prefix_in_format_docs_reports_warning(tmp_path: Path):
    """`](.rddf/.rddf/improvements/X)` in format docs → WARNING."""
    _write_doc(tmp_path, "docs/proposal-suggestions-format.md",
        "| [foo](.rddf/.rddf/improvements/foo.md) | P1 |\n")

    findings = run_check(project_root=tmp_path)
    assert any(
        f.severity == Severity.WARNING
        and "double-prefix" in f.snippet
        and "rddf migrate-improvements" in f.fix_hint
        for f in findings
    )


def test_fix_hint_includes_allow_source_repo_for_source_repo(tmp_path: Path):
    """When the repo has skills/INSTALL.md (rdd-workflow source repo), the fix_hint
    should include --allow-source-repo."""
    _write_doc(tmp_path, "skills/INSTALL.md", "# install\n")
    _write_doc(tmp_path, ".rddf/improvements/exists.md", "# exists\n")
    _write_doc(tmp_path, "AGENTS.md", "Legacy [link](improvements/x.md)\n")

    findings = run_check(project_root=tmp_path)
    assert any(
        "--allow-source-repo" in f.fix_hint
        for f in findings
    )


def test_fix_hint_omits_allow_source_repo_for_third_party(tmp_path: Path):
    """When the repo has NO skills/INSTALL.md (third-party project), the fix_hint
    should NOT include --allow-source-repo."""
    _write_doc(tmp_path, "AGENTS.md", "Legacy [link](improvements/x.md)\n")

    findings = run_check(project_root=tmp_path)
    assert all(
        "--allow-source-repo" not in f.fix_hint
        for f in findings
    )


def test_multiple_stale_refs_one_finding_per_file(tmp_path: Path):
    """Each file with stale refs produces ONE finding (with count in snippet)."""
    _write_doc(tmp_path, "AGENTS.md",
        "[foo](improvements/foo.md) and [bar](improvements/bar.md)\n"
    )

    findings = run_check(project_root=tmp_path)
    assert len(findings) == 1
    assert "2 stale link" in findings[0].snippet


def test_double_prefix_in_agents_md_detected(tmp_path: Path):
    """Double-prefix bug is detected in AGENTS.md too."""
    _write_doc(tmp_path, "AGENTS.md",
        "[bug](.rddf/.rddf/improvements/bug.md)\n"
    )

    findings = run_check(project_root=tmp_path)
    assert any(
        "double-prefix" in f.snippet for f in findings
    )


def test_format_docs_detected(tmp_path: Path):
    """Both format docs are scanned."""
    _write_doc(tmp_path, "docs/proposal-approved-format.md",
        "[foo](improvements/foo.md)\n"
    )
    _write_doc(tmp_path, "docs/proposal-suggestions-format.md",
        "[bar](improvements/bar.md)\n"
    )

    findings = run_check(project_root=tmp_path)
    assert len(findings) == 2
    files = {f.file for f in findings}
    assert any("proposal-approved-format.md" in f for f in files)
    assert any("proposal-suggestions-format.md" in f for f in files)


def test_no_findings_when_legitimate_prose_only(tmp_path: Path):
    """Prose mentions like '索引到 improvements/*.md' are NOT flagged
    (only markdown links are)."""
    _write_doc(tmp_path, "AGENTS.md",
        "格式为 **Markdown 表格** (索引到 improvements/*.md). 详见其他文档。\n"
    )

    findings = run_check(project_root=tmp_path)
    assert findings == []