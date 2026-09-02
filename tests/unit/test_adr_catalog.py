r"""Tests for skills/_lib/adr_catalog.py (shared ADR catalog layer, Task A).

Covers:
- scan_adr_catalog returns dict[str, AdrMeta] with sha256 file_hash
- empty / missing dir returns empty dict
- non-matching filenames are skipped (ADR_PATTERN: ^ADR-(\d{4})-.*\.md$)
"""
from pathlib import Path

from skills._lib.adr_catalog import AdrMeta, scan_adr_catalog


def _make_adr_dir(root: Path) -> Path:
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    return adr_dir


def test_scan_adr_catalog_returns_dict_of_adrmeta(tmp_path):
    adr_dir = _make_adr_dir(tmp_path)
    (adr_dir / "ADR-0001-foo.md").write_text(
        "---\nstatus: 已采纳\ntitle: Foo\nphase: phase-1\n---\n# Foo\n",
        encoding="utf-8",
    )
    (adr_dir / "ADR-0002-bar.md").write_text(
        "---\nstatus: 待定\ntitle: Bar\n---\n# Bar\n",
        encoding="utf-8",
    )

    result = scan_adr_catalog(tmp_path)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"ADR-0001", "ADR-0002"}
    assert isinstance(result["ADR-0001"], AdrMeta)
    assert result["ADR-0001"].title == "Foo"
    assert result["ADR-0001"].status == "已采纳"
    assert result["ADR-0001"].phase == "phase-1"
    assert result["ADR-0002"].status == "待定"
    assert result["ADR-0002"].phase is None
    assert len(result["ADR-0001"].file_hash) == 64  # sha256 hex
    assert result["ADR-0001"].file_path.name == "ADR-0001-foo.md"


def test_scan_adr_catalog_empty_dir_returns_empty_dict(tmp_path):
    _make_adr_dir(tmp_path)
    assert scan_adr_catalog(tmp_path) == {}
    # missing dir entirely also returns empty dict
    assert scan_adr_catalog(tmp_path, adr_dir="docs/nonexistent") == {}


def test_scan_adr_catalog_skips_nonmatching_files(tmp_path):
    adr_dir = _make_adr_dir(tmp_path)
    (adr_dir / "ADR-0001-foo.md").write_text(
        "---\nstatus: 已采纳\ntitle: Foo\n---\n# Foo\n",
        encoding="utf-8",
    )
    (adr_dir / "README.md").write_text("# ADR index\n", encoding="utf-8")
    (adr_dir / "ADR-0000-template.md").write_text(
        "---\nstatus: template\ntitle: Template\n---\n# Template\n",
        encoding="utf-8",
    )
    (adr_dir / "notes.txt").write_text("not an ADR\n", encoding="utf-8")
    (adr_dir / "ADR-draft.md").write_text("no digits\n", encoding="utf-8")

    result = scan_adr_catalog(tmp_path)

    assert set(result.keys()) == {"ADR-0000", "ADR-0001"}


def test_scan_adr_catalog_three_digit_pattern(tmp_path):
    """Three-digit ADR pattern (ChipForge case) via adr_pattern override."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)

    (adr_dir / "ADR-040-three-digit.md").write_text(
        "---\ntitle: Three digit test\n---\n# Three digit\n"
    )
    (adr_dir / "ADR-041-three-digit.md").write_text(
        "---\ntitle: Another three digit\n---\n# Three digit\n"
    )
    (adr_dir / "ADR-0000-template.md").write_text(
        "---\nstatus: template\n---\n# Template\n"
    )

    result = scan_adr_catalog(
        tmp_path, adr_pattern=r"^ADR-(\d{3})-.*\.md$"
    )

    assert set(result.keys()) == {"ADR-040", "ADR-041"}
    assert "ADR-0000" not in result


def test_scan_adr_catalog_pattern_override_backward_compat(tmp_path):
    """No adr_pattern → default 4-digit behavior preserved."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)

    (adr_dir / "ADR-0040-backward.md").write_text(
        "---\ntitle: Backward compat\n---\n# Backward\n"
    )

    result = scan_adr_catalog(tmp_path)

    assert set(result.keys()) == {"ADR-0040"}
