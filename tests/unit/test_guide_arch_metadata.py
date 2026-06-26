"""Tests for guide-arch.md — verifies frontmatter and sub-phase structure."""
import os
import pytest
import yaml

SKILL_PATH = os.path.join(os.path.dirname(__file__), "../../skills/guide-arch.md")

def test_guide_arch_exists():
    assert os.path.exists(SKILL_PATH)
def test_guide_arch_frontmatter():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert content.startswith("---")
    parts = content.split("---", 2)
    meta = yaml.safe_load(parts[1])
    assert meta["name"] == "guide-arch"
    assert meta["metadata"]["user-invocable"] is True
def test_guide_arch_has_required_sections():
    with open(SKILL_PATH) as f:
        content = f.read()
    required = ["setup", "adr-create", "architecture", "roadmap-define", "arch-done"]
    for section in required:
        assert section in content, f"guide-arch.md must contain section for {section}"
def test_guide_arch_has_handoff():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert ".arch-handoff.json" in content