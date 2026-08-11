"""Unit tests for parse_approved_proposals."""
from __future__ import annotations

from pathlib import Path

import pytest

from _lib.parse_approved import parse_approved_proposals


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "proposal-approved.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    result = parse_approved_proposals(str(tmp_path / "does-not-exist.md"))
    assert result == []


def test_empty_file_returns_empty(tmp_path: Path) -> None:
    p = _write(tmp_path, "")
    assert parse_approved_proposals(str(p)) == []


def test_only_approved_section(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "## 已批准提案\n\n"
        "| [alpha](.rddf/improvements/alpha.md) | P1 | 2026-08-01 | arch |\n"
        "| [beta](.rddf/improvements/beta.md) | P2 | 2026-08-02 | arch |\n"
        "\n## 已实施\n",
    )
    assert parse_approved_proposals(str(p)) == ["alpha", "beta"]


def test_only_implemented_section(tmp_path: Path) -> None:
    # The real-world case: everything lives in ## 已实施
    p = _write(
        tmp_path,
        "## 已批准提案\n\n## 已实施\n\n"
        "| [gamma](.rddf/improvements/gamma.md) | P0 | 2026-08-07 | arch |\n"
        "| [delta](.rddf/improvements/delta.md) | P1 | 2026-08-06 | arch |\n",
    )
    assert parse_approved_proposals(str(p)) == ["gamma", "delta"]


def test_both_sections_dedup_keep_order(tmp_path: Path) -> None:
    # gamma appears in BOTH sections; should appear once, in first-appearance order
    p = _write(
        tmp_path,
        "## 已批准提案\n\n"
        "| [alpha](.rddf/improvements/alpha.md) | P1 | 2026-08-01 | arch |\n"
        "\n## 已实施\n\n"
        "| [alpha](.rddf/improvements/alpha.md) | P1 | 2026-08-02 | arch |\n"
        "| [beta](.rddf/improvements/beta.md) | P2 | 2026-08-03 | arch |\n",
    )
    assert parse_approved_proposals(str(p)) == ["alpha", "beta"]


def test_real_repo_proposal_approved(tmp_path: Path) -> None:
    # Sanity check against the actual proposal-approved.md at repo root.
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "proposal-approved.md"
    if not target.exists():
        pytest.skip("proposal-approved.md not present in this checkout")
    names = parse_approved_proposals(str(target))
    # Must include entries that previously returned 0 (all entries were in ## 已实施)
    assert "fix-design-proposal-review-approved-parsing" in names
    # And the helper must return more than zero entries (the original bug)
    assert len(names) > 0


def test_cli_guard_prints_one_name_per_line(tmp_path: Path) -> None:
    # Run the file as a script and verify the __main__ branch.
    import subprocess
    import sys

    p = _write(
        tmp_path,
        "## 已实施\n\n"
        "| [gamma](.rddf/improvements/gamma.md) | P0 | 2026-08-07 | arch |\n"
        "| [delta](.rddf/improvements/delta.md) | P1 | 2026-08-06 | arch |\n",
    )
    repo_root = Path(__file__).resolve().parents[2]
    helper = repo_root / "_lib" / "parse_approved.py"
    out = subprocess.run(
        [sys.executable, str(helper), str(p)],
        capture_output=True, text=True, check=True,
    )
    assert out.stdout.splitlines() == ["gamma", "delta"]