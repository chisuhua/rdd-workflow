"""Tests for rdd-arch.md — Stage 3 canonical skill (per ADR-0042).

Locks frontmatter, required sections, and ownership boundaries.
"""
import os
import pytest
import yaml

SKILL_PATH = os.path.join(os.path.dirname(__file__), "../../skills/rdd-arch/SKILL.md")


def test_rdd_arch_skill_file_exists():
    assert os.path.exists(SKILL_PATH), "rdd-arch SKILL.md must exist at canonical path"


def test_rdd_arch_frontmatter_name_is_rdd_arch():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert content.startswith("---")
    parts = content.split("---", 2)
    meta = yaml.safe_load(parts[1])
    assert meta["name"] == "rdd-arch", (
        f"canonical skill name must be 'rdd-arch', got {meta['name']!r}"
    )
    assert meta["metadata"]["user-invocable"] is True


def test_rdd_arch_version_bumped_to_2_1():
    with open(SKILL_PATH) as f:
        parts = f.read().split("---", 2)
    meta = yaml.safe_load(parts[1])
    assert meta["metadata"]["version"] == "2.1.0", (
        "rdd-arch metadata.version must be 2.1.0 (Stage 3 rename bump)"
    )


def test_rdd_arch_evolved_from_documents_rename():
    with open(SKILL_PATH) as f:
        parts = f.read().split("---", 2)
    meta = yaml.safe_load(parts[1])
    assert "guide-arch" in meta["metadata"]["evolved-from"], (
        "evolved-from must reference the rename origin"
    )


def test_rdd_arch_has_required_sections():
    with open(SKILL_PATH) as f:
        content = f.read()
    required = ["setup", "adr-create", "architecture", "roadmap-define", "arch-done"]
    for section in required:
        assert section in content, f"rdd-arch.md must contain section for {section}"


def test_rdd_arch_has_handoff_path():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert ".arch-handoff.json" in content


def test_rdd_arch_role_boundaries_include_planner_feedback_not_owns():
    """per ADR-0042: rdd-arch does NOT own .planner-feedback.json."""
    with open(SKILL_PATH) as f:
        parts = f.read().split("---", 2)
    meta = yaml.safe_load(parts[1])
    not_owns = meta["role"]["boundaries"]["not_owns"]
    assert ".rddf/state/.planner-feedback.json" in not_owns, (
        "rdd-arch must explicitly NOT own .planner-feedback.json (planner owns)"
    )