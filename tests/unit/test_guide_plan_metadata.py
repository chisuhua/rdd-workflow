"""Tests for guide-plan.md — verifies frontmatter and sub-phase structure."""
import os
import pytest
import yaml

SKILL_PATH = os.path.join(os.path.dirname(__file__), "../../skills/guide-plan.md")

def test_guide_plan_exists():
    assert os.path.exists(SKILL_PATH)
def test_guide_plan_frontmatter():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert content.startswith("---")
    parts = content.split("---", 2)
    meta = yaml.safe_load(parts[1])
    assert meta["name"] == "guide-plan"
    assert meta["metadata"]["user-invocable"] is True
def test_guide_plan_has_required_sections():
    with open(SKILL_PATH) as f:
        content = f.read()
    required = ["scan", "propose", "deps", "plan-done"]
    for section in required:
        assert section in content, f"guide-plan.md must contain section for {section}"
def test_guide_plan_has_handoff():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert ".plan-handoff.json" in content
def test_guide_plan_propose_delegation():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert 'skill_use("propose")' in content or "skill_use(\"propose\"" in content
def test_guide_plan_deps_delegation():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert 'skill_use("deps")' in content or "skill_use(\"deps\"" in content