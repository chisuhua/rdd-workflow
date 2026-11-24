"""Unit tests for the doctor `improvement-frontmatter-consistency` checker.

Two independent defects are covered:

1. **Missing delimiters** — the original check (first line must be ``---``).
2. **Unparseable YAML** — a front matter block whose scalar contains ``: ``
   (or ends with ``:``) is rejected by PyYAML. The consumer
   (``_lib/state_reader.py::_parse_improvement_meta``) then loses the whole
   metadata set, so the file silently renders as "待讨论" with "-" in every
   column. The delimiter check cannot see this, so the checker must parse.

Severity contract: WARNING only — this category is advisory and must never
turn a third-party project red.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-doctor" / "scripts"))

import checks.improvement_frontmatter_check as fm_check  # noqa: E402
from doctor_render import Severity  # noqa: E402


def _write(root: Path, name: str, body: str) -> None:
    imp = root / ".rddf" / "improvements"
    imp.mkdir(parents=True, exist_ok=True)
    (imp / f"{name}.md").write_text(body, encoding="utf-8")


def test_missing_frontmatter_delimiters_is_reported(tmp_path):
    _write(tmp_path, "legacy", "# legacy\n\n**优先级**: P1\n")
    findings = fm_check.run(project_root=tmp_path)
    assert findings, "缺 front matter 分隔符必须报出"
    assert any("missing frontmatter delimiters" in f.snippet for f in findings)
    for f in findings:
        assert f.severity is Severity.WARNING


def test_invalid_yaml_frontmatter_is_reported(tmp_path):
    """A scalar containing ': ' breaks the parse ⇒ must be reported."""
    _write(
        tmp_path,
        "broken",
        "---\n"
        "优先级: P2\n"
        "来源: 多次审计 (commit ab5ded7)\n"
        "  入口未正式文档化。新 skill 作者不知道:\n"
        "  - 有哪些模块可用\n"
        "阶段: v4.1 follow-up\n"
        "---\n\n"
        "# broken\n",
    )
    findings = fm_check.run(project_root=tmp_path)
    assert findings, "无效 YAML front matter 必须报出"
    assert any("not valid YAML" in f.snippet for f in findings)
    for f in findings:
        assert f.severity is Severity.WARNING


def test_valid_frontmatter_produces_no_finding(tmp_path):
    _write(
        tmp_path,
        "good",
        "---\n"
        "优先级: P1\n"
        "阶段: phase-2\n"
        "状态: draft\n"
        "---\n\n"
        "# good\n",
    )
    assert fm_check.run(project_root=tmp_path) == []


def test_folded_block_scalar_is_accepted(tmp_path):
    """The repaired form (folded block scalar) must pass."""
    _write(
        tmp_path,
        "folded",
        "---\n"
        "优先级: P2\n"
        "来源: >-\n"
        "  多行文本，第一行\n"
        "  第二行结尾有冒号:\n"
        "  - 列表项\n"
        "阶段: v4.1 follow-up\n"
        "---\n\n"
        "# folded\n",
    )
    assert fm_check.run(project_root=tmp_path) == []


def test_missing_improvements_dir_is_silent(tmp_path):
    assert fm_check.run(project_root=tmp_path) == []
