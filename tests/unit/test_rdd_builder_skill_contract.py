"""`skills/rdd-builder/SKILL.md` 的 **delta 契约段**（AC11）。

三个锚点缺一即红（禁「存在即通过」的假判据）：
① 载体（**粗体头行**）② MODIFIED **保留既有 Scenario** ③ 版本口径（1.7.0 分流）
"""
from __future__ import annotations

import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SKILL = _ROOT / "skills" / "rdd-builder" / "SKILL.md"


def test_skill_documents_delta_contract() -> None:
    text = _SKILL.read_text(encoding="utf-8")
    assert "粗体头行" in text, "缺锚点①载体（delta/语义要求 用粗体头行承载）"
    assert "既有 Scenario" in text, "缺锚点②MODIFIED 必须保留既有 Scenario"
    assert "1.7.0" in text, "缺锚点③版本口径（≥1.7.0 复用原生检查 / <1.7.0 自实现）"


def test_skill_documents_delta_target_directory() -> None:
    text = _SKILL.read_text(encoding="utf-8")
    assert "specs/<capability>/" in text, "缺 delta 落点目录语义（design D-3）"
