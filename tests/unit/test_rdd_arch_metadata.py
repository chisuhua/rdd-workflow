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


def test_rdd_arch_version_bumped_to_2_2():
    """Per ADR-0057 (v2.2.0): gap-analysis artifact type removed; rdd-arch
    simplified to ADR + theme-doc dual artifact model.

    Version bump rationale:
    - v2.0: original guide-arch → rdd-arch rename (per ADR-0042)
    - v2.1: frontmatter / description cleanup (Stage 3)
    - v2.2: ADR + theme-doc only; gap-analysis deleted (per ADR-0057)
    """
    with open(SKILL_PATH) as f:
        parts = f.read().split("---", 2)
    meta = yaml.safe_load(parts[1])
    assert meta["metadata"]["version"] == "2.2.0", (
        "rdd-arch metadata.version must be 2.2.0 (per ADR-0057: gap-analysis removed)"
    )


def test_rdd_arch_evolved_from_documents_rename():
    with open(SKILL_PATH) as f:
        parts = f.read().split("---", 2)
    meta = yaml.safe_load(parts[1])
    assert "guide-arch" in meta["metadata"]["evolved-from"], (
        "evolved-from must reference the rename origin"
    )


def test_rdd_arch_has_required_sections():
    """Lock the 4 actual phase headings (per ADR-0048 + ADR-0057).

    Prior version checked 5 phases including 'architecture'. Per ADR-0057
    (v2.2.0), the architecture phase was removed — gap-analysis artifact type
    deleted; rdd-arch simplified to ADR + theme-doc dual model with 4 phases.

    Uses prefix match so trailing annotations like "(Exit) (renumbered per
    ADR-0048)" pass. Guards against accidental re-addition of removed phases.
    """
    import re
    with open(SKILL_PATH) as f:
        content = f.read()
    headings = re.findall(r"^## Phase \d+: (.+)$", content, re.MULTILINE)
    required_prefixes = ["setup", "adr-create", "arch validation", "arch-done"]
    for prefix in required_prefixes:
        assert any(h.startswith(prefix) for h in headings), (
            f"rdd-arch.md must contain a Phase heading starting with {prefix!r}; "
            f"found: {headings}"
        )
    # Per ADR-0048: roadmap-define removed; guard against accidental re-add
    assert not any("roadmap-define" in h for h in headings), (
        f"roadmap-define must NOT appear as a Phase heading (ADR-0048); "
        f"found: {headings}"
    )
    # Per ADR-0057: architecture (gap-analysis) phase removed
    assert not any(h.startswith("architecture") for h in headings), (
        f"architecture phase must NOT appear (ADR-0057: gap-analysis removed); "
        f"found: {headings}"
    )


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