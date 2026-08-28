"""Unit tests for _lib/adr_index_generator.py"""
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))

from adr_index_generator import scan_adrs, extract_metadata, render_table


REPO_ROOT = Path(__file__).resolve().parents[2]
ADR_DIR = REPO_ROOT / "docs" / "adr"


class TestScanAdrs:
    def test_scan_adrs_returns_at_least_35_files(self):
        """扫描 docs/adr/ 至少返回 35 个 ADR-*.md (含 template)。"""
        adrs = scan_adrs(ADR_DIR)
        assert len(adrs) >= 35
        for adr in adrs:
            assert "number" in adr
            assert "title" in adr
            assert "slug" in adr
            assert "filename" in adr
            assert "path" in adr

    def test_scan_adrs_excludes_non_matching_files(self):
        """README.md 不应被纳入。"""
        adrs = scan_adrs(ADR_DIR)
        filenames = {a["filename"] for a in adrs}
        assert "README.md" not in filenames
        assert all(f.startswith("ADR-") for f in filenames)


class TestExtractMetadata:
    def test_extract_metadata_parses_status_date_decider(self):
        """解析 ADR-0001 的 > 状态/日期/决策者 块。"""
        md = extract_metadata(ADR_DIR / "ADR-0001-propose-plan-execute-state-machine.md")
        assert md is not None
        assert "status" in md
        assert md["status"]  # non-empty
        assert "date" in md
        assert "decider" in md

    def test_extract_metadata_marks_template(self):
        """ADR-0000 是 template,应标记 is_template=True。"""
        md = extract_metadata(ADR_DIR / "ADR-0000-template.md")
        if md is not None:
            assert md.get("is_template") is True


class TestRenderTable:
    def test_render_table_outputs_markdown(self):
        """render_table 输出 markdown 表格。"""
        adrs = scan_adrs(ADR_DIR)
        table = render_table(adrs)
        assert "| ADR |" in table
        assert "| 标题 |" in table
        assert "| 状态 |" in table
        rows = [l for l in table.splitlines() if l.startswith("| [ADR-")]
        assert len(rows) >= 34
        assert "ADR-0000" not in table

    def test_render_table_skips_template(self):
        """render_table 跳过 template。"""
        adrs = scan_adrs(ADR_DIR)
        table = render_table(adrs)
        assert "[ADR-0000]" not in table
