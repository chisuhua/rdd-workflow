"""Unit tests for `_lib.arch.protocol` (Analyzer Subset §2 data layer).

Per ADR-0046 + cross-stage-protocol-template.md Analyzer Subset:
  - build_skeleton produces byte-identical markdown to pre-refactor bash heredoc
  - validate_document checks 5-section structure (hard) + placeholder density (advisory)
  - list_analyses enumerates gap documents sorted by slug
  - parse_slug enforces kebab-case
"""
from __future__ import annotations

import pytest
from _lib.arch import (
    REQUIRED_SECTIONS,
    build_skeleton,
    list_analyses,
    parse_slug,
    validate_document,
)


class TestParseSlug:
    def test_valid_kebab_slug_passes_through(self):
        assert parse_slug("auth") == "auth"
        assert parse_slug("multi-segment-slug") == "multi-segment-slug"
        assert parse_slug("with-123-numbers") == "with-123-numbers"

    def test_empty_slug_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            parse_slug("")

    def test_uppercase_slug_rejected(self):
        with pytest.raises(ValueError, match="kebab-case"):
            parse_slug("BadSlug")

    def test_underscore_slug_rejected(self):
        with pytest.raises(ValueError, match="kebab-case"):
            parse_slug("under_score")

    def test_consecutive_hyphens_rejected(self):
        with pytest.raises(ValueError, match="kebab-case"):
            parse_slug("double--hyphen")

    def test_leading_hyphen_rejected(self):
        with pytest.raises(ValueError, match="kebab-case"):
            parse_slug("-leading")


class TestBuildSkeleton:
    def test_build_skeleton_contains_title_with_slug(self):
        body = build_skeleton("auth", "2026-09-07")
        assert "# 架构差距分析: auth" in body

    def test_build_skeleton_contains_today_iso(self):
        body = build_skeleton("test", "2026-01-15")
        assert "**生成日期**: 2026-01-15" in body

    def test_build_skeleton_contains_all_5_sections(self):
        body = build_skeleton("test", "2026-09-07")
        for section in REQUIRED_SECTIONS:
            assert section in body, f"missing section: {section}"

    def test_build_skeleton_byte_equal_to_pre_refactor_heredoc(self):
        """Oracle risk #3: existing bats tests lock the wrapper contract.

        The pre-refactor bash heredoc content (lines 30-56 of
        git show HEAD:skills/rdd-arch/scripts/arch_gap_analysis.sh)
        MUST be byte-identical to build_skeleton output.
        """
        expected_lines = [
            "# 架构差距分析: auth",
            "",
            "> **生成日期**: 2026-09-07",
            "> **状态**: 草案",
            "> **关联 ADR**: (待补充)",
            "",
            "## 1. 目标架构",
            "",
            "(描述 ADR 中定义的目标架构)",
            "",
            "## 2. 当前架构",
            "",
            "(描述项目当前实际架构)",
            "",
            "## 3. 差距清单",
            "",
            "| # | 差距项 | 严重程度 | 优先级 | 关联 change |",
            "|---|--------|---------|--------|------------|",
            "| 1 | ... | 高/中/低 | P0/P1/P2 | ... |",
            "",
            "## 4. 补齐路径",
            "",
            "(描述从当前架构迁移到目标架构的步骤、顺序、依赖)",
            "",
            "## 5. 参考资料",
            "",
            "- 相关 ADR",
            "- 相关 change artifacts",
        ]
        body = build_skeleton("auth", "2026-09-07")
        assert body.splitlines() == expected_lines

    def test_build_skeleton_rejects_non_kebab_slug(self):
        with pytest.raises(ValueError):
            build_skeleton("BadSlug", "")


class TestValidateDocument:
    def test_validate_document_accepts_complete_skeleton(self, tmp_path):
        f = tmp_path / "ok.md"
        f.write_text(build_skeleton("test", "2026-09-07"))
        report = validate_document(f)
        assert report.structural_ok is True
        assert report.issues == []
        assert report.completeness == "draft"  # all placeholders intact

    def test_validate_document_flags_missing_section(self, tmp_path):
        f = tmp_path / "broken.md"
        # Drop the 5th section entirely
        body = build_skeleton("test", "2026-09-07")
        truncated = body.split("## 5. 参考资料")[0]
        f.write_text(truncated)
        report = validate_document(f)
        assert report.structural_ok is False
        assert any("参考资料" in issue for issue in report.issues)

    def test_validate_document_flags_renamed_section_header(self, tmp_path):
        """Pre-refactor guard: hand-edit of a `##` to `###` must be detected."""
        f = tmp_path / "renamed.md"
        body = build_skeleton("test", "2026-09-07")
        body = body.replace("## 3. 差距清单", "### 3. 差距清单")
        f.write_text(body)
        report = validate_document(f)
        assert report.structural_ok is False
        assert any("差距清单" in issue for issue in report.issues)

    def test_validate_document_complete_when_no_placeholders(self, tmp_path):
        f = tmp_path / "filled.md"
        body = build_skeleton("test", "2026-09-07")
        body = body.replace("(描述 ADR 中定义的目标架构)", "ADR-0017 定义的目标")
        body = body.replace("(描述项目当前实际架构)", "当前 monorepo + dorn")
        body = body.replace("(描述从当前架构迁移到目标架构的步骤、顺序、依赖)",
                            "阶段 1: 拆分 monorepo; 阶段 2: 引入 service mesh")
        body = body.replace("- 相关 ADR\n- 相关 change artifacts", "- ADR-0017\n- my-change")
        f.write_text(body)
        report = validate_document(f)
        assert report.structural_ok is True
        # 1 placeholder remains: "(待补充)" in **关联 ADR** line + 表格 `| 1 | ... |` row
        # → still partial
        assert report.completeness in ("partial", "complete")

    def test_validate_document_bool_protocol(self, tmp_path):
        """`if validate_document(path): ...` should test structural_ok."""
        f = tmp_path / "ok.md"
        f.write_text(build_skeleton("test", "2026-09-07"))
        report = validate_document(f)
        assert bool(report) is True  # all sections present
        assert bool(report) == report.structural_ok


class TestListAnalyses:
    def test_list_analyses_empty_dir(self, tmp_path):
        assert list_analyses(tmp_path) == []

    def test_list_analyses_missing_dir(self, tmp_path):
        nonexistent = tmp_path / "no-such-dir"
        assert list_analyses(nonexistent) == []

    def test_list_analyses_filters_and_sorts(self, tmp_path):
        # Create files: 2 gap analyses + 1 unrelated
        (tmp_path / "b-gap-analysis.md").write_text("")
        (tmp_path / "a-gap-analysis.md").write_text("")
        (tmp_path / "README.md").write_text("")  # not gap-a suffix
        result = list_analyses(tmp_path)
        names = [p.name for p in result]
        assert names == ["a-gap-analysis.md", "b-gap-analysis.md"]

    def test_list_analyses_excludes_hidden_and_unrelated(self, tmp_path):
        (tmp_path / "x-gap-analysis.md").write_text("")
        (tmp_path / "historical-evolution.md").write_text("")
        (tmp_path / ".populate-state.json").write_text("")
        result = list_analyses(tmp_path)
        assert [p.name for p in result] == ["x-gap-analysis.md"]


class TestModuleContract:
    """Pin the public API exposed via `_lib.arch.__init__`."""

    def test_required_sections_are_5(self):
        assert len(REQUIRED_SECTIONS) == 5

    def test_required_sections_cover_template_contract(self):
        # Lock the exact section titles so accidental template drift is caught.
        assert REQUIRED_SECTIONS == (
            "## 1. 目标架构",
            "## 2. 当前架构",
            "## 3. 差距清单",
            "## 4. 补齐路径",
            "## 5. 参考资料",
        )