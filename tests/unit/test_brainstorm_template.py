"""Verify rdd-workflow-brainstorm 5-section template includes **主题** field.

Tests cover:
- Template metadata includes **主题** line
- Field documentation mentions '不适用' as default for free mode
- Field is placed after 类型 line (logical ordering: 优先级/阶段/类型/主题)
"""
import sys
from pathlib import Path

SKILL_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "rdd-workflow-brainstorm"
    / "SKILL.md"
)


def test_template_includes_subject_field():
    """The 5-section markdown template includes a **主题**: line."""
    content = SKILL_PATH.read_text(encoding="utf-8")
    assert "**主题**:" in content, (
        "Expected **主题**: field in brainstorm template"
    )


def test_subject_field_after_type_line():
    """The 主题 field is positioned after the 类型 field (logical metadata order)."""
    content = SKILL_PATH.read_text(encoding="utf-8")
    type_pos = content.find("**类型**:")
    subject_pos = content.find("**主题**:")
    assert type_pos != -1, "**类型**: field must exist"
    assert subject_pos != -1, "**主题**: field must exist"
    assert subject_pos > type_pos, "**主题**: must come after **类型**:"


def test_subject_field_documents_default():
    """Field documentation mentions 不适用 as valid value."""
    content = SKILL_PATH.read_text(encoding="utf-8")
    assert "不适用" in content, (
        "Field documentation must mention 不适用 as valid value"
    )


def test_subject_field_documents_semantics():
    """Field documentation explains coverage matching purpose."""
    content = SKILL_PATH.read_text(encoding="utf-8")
    assert "覆盖率" in content or "精确字符串匹配" in content, (
        "Field documentation must explain coverage matching semantics"
    )


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))