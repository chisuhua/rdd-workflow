"""Unit tests for ac_verifier module."""
from pathlib import Path
import pytest
from skills.ac_verifier.scripts.ac_verifier import parse_acs


def test_parse_acs_empty_section(tmp_path: Path):
    """Section header present but no bullets → empty list."""
    p = tmp_path / "proposal.md"
    p.write_text("# T\n\n## 验收标准\n\n## Other\n", encoding="utf-8")
    assert parse_acs(p) == []


def test_parse_acs_single_checkbox(tmp_path: Path):
    """Single `- [ ]` bullet becomes AC-1."""
    p = tmp_path / "proposal.md"
    p.write_text(
        "# T\n\n## 验收标准\n\n- [ ] First AC\n\n## Other\n",
        encoding="utf-8",
    )
    result = parse_acs(p)
    assert len(result) == 1
    assert result[0]["ac_id"] == "AC-1"
    assert result[0]["description"] == "First AC"
    assert result[0]["has_checkbox"] is True


def test_parse_acs_multiple_prose_bullets(tmp_path: Path):
    """Prose bullets (no checkbox) are also ACs."""
    p = tmp_path / "proposal.md"
    p.write_text(
        "# T\n\n## 验收标准\n\n- First AC\n- Second AC\n- Third AC\n",
        encoding="utf-8",
    )
    result = parse_acs(p)
    assert [r["ac_id"] for r in result] == ["AC-1", "AC-2", "AC-3"]
    assert all(r["has_checkbox"] is False for r in result)


def test_parse_acs_mixed(tmp_path: Path):
    """Mix of checkbox and prose bullets."""
    p = tmp_path / "proposal.md"
    p.write_text(
        "# T\n\n## 验收标准\n\n- [ ] First\n- Second\n- [x] Done\n",
        encoding="utf-8",
    )
    result = parse_acs(p)
    assert len(result) == 3
    assert result[0]["has_checkbox"] is True
    assert result[1]["has_checkbox"] is False
    assert result[2]["has_checkbox"] is True


def test_parse_acs_missing_section(tmp_path: Path):
    """No `## 验收标准` section → empty list."""
    p = tmp_path / "proposal.md"
    p.write_text("# T\n\n## Acceptance\n- something\n", encoding="utf-8")
    assert parse_acs(p) == []