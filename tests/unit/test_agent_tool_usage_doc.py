import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SECTIONS = [
    "## Edit 决策树",
    "## Write 决策树",
    "## Read Offset 决策树",
]


def test_agent_tool_usage_doc_exists():
    doc = ROOT / "skills" / "_lib" / "AGENT_TOOL_USAGE.md"
    assert doc.is_file(), f"missing {doc}"


def test_agent_tool_usage_doc_has_all_decision_trees():
    doc = ROOT / "skills" / "_lib" / "AGENT_TOOL_USAGE.md"
    content = doc.read_text()
    for section in REQUIRED_SECTIONS:
        assert section in content, f"missing section {section!r}"


def test_brainstorm_skill_references_guard():
    skill = ROOT / "skills" / "rdd-workflow-brainstorm" / "SKILL.md"
    content = skill.read_text()
    assert "pre_tool_use_check.sh" in content
    assert "AGENT_TOOL_USAGE.md" in content
