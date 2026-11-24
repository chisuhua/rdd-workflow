"""Unit tests for _lib/adr_index_generator.py"""
import re
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

# ---------- status_class / status_raw (fix-adr-shape-debt-convergence T4) ----------
# Status 行是自由文本（本仓有十几种写法），机器消费不了。分类在**生成器侧**完成，
# **不改任何 ADR 的 Status 行**。

STATUS_CLASSES = {"draft", "proposed", "accepted", "amended", "superseded", "rejected"}


def _meta_for(tmp_path, status_line):
    path = tmp_path / "ADR-0100-probe.md"
    path.write_text(f"# ADR-0100: probe\n\n> **状态**: {status_line}\n\n## Context\n", encoding="utf-8")
    return extract_metadata(path)


class TestStatusClassification:
    def test_status_raw_is_the_verbatim_value(self):
        """status_raw 与 Status 行原文逐字符相等（分类不得丢信息）。"""
        path = ADR_DIR / "ADR-0060-adr-shape-contract-and-gate-demotion.md"
        text = path.read_text(encoding="utf-8")
        raw = re.search(r"^>\s*\*\*状态\*\*:\s*(.+?)\s*$", text, re.M).group(1)
        md = extract_metadata(path)
        assert md["status_raw"] == raw
        assert md["status"] == md["status_raw"]  # 旧键语义不变（下游 render 不破）

    @pytest.mark.parametrize("line,expected", [
        ("已替代为 ADR-0063", "superseded"),
        ("已被取代", "superseded"),
        ("已采纳。**Superseded by ADR-0063（2026-11-19）**", "superseded"),
        ("已拒绝", "rejected"),
        ("已采纳 + AMENDED (2026-11-17)", "amended"),
        ("已采纳 + DOUBLE-AMENDED", "amended"),
        ("已采纳 + 已实施（v4.1 release）", "accepted"),
        ("✅ 已采纳", "accepted"),
        ("待采纳", "proposed"),
        ("待定", "draft"),
    ])
    def test_status_class_precedence(self, tmp_path, line, expected):
        """优先级：superseded > rejected > amended > accepted > proposed > draft。"""
        assert _meta_for(tmp_path, line)["status_class"] == expected

    def test_status_class_covers_whole_corpus_within_six_values(self):
        """全语料分类后取值集 ≤ 6，且真覆盖到实际存在的形态（不是全落 fallback）。"""
        classes = {}
        for path in ADR_DIR.glob("ADR-*.md"):
            if "template" in path.name.lower():
                continue
            md = extract_metadata(path)
            assert md is not None, path.name
            assert md.get("status_class") in STATUS_CLASSES, f"{path.name}: {md.get('status_class')}"
            classes[path.name] = md["status_class"]
        assert set(classes.values()) <= STATUS_CLASSES
        assert {"accepted", "superseded", "amended", "proposed", "draft"} <= set(classes.values())
