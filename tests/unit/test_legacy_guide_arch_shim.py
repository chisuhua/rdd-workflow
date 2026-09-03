"""Tests for legacy guide-arch shim (5-line deprecation notice).

Locks shim contract per Stage 3 plan v2 §4 Change 1:
- name == guide-arch (legacy identity preserved)
- metadata.deprecated == "use rdd-arch"
- body is a 5-line deprecation notice forwarding to rdd-arch
"""
import os
import pytest
import yaml

SHIM_PATH = os.path.join(os.path.dirname(__file__), "../../skills/guide-arch/SKILL.md")


def test_legacy_guide_arch_shim_file_exists():
    assert os.path.exists(SHIM_PATH)


def test_legacy_guide_arch_shim_name_is_guide_arch():
    with open(SHIM_PATH) as f:
        content = f.read()
    parts = content.split("---", 2)
    meta = yaml.safe_load(parts[1])
    assert meta["name"] == "guide-arch", (
        "shim must preserve legacy name 'guide-arch' for backward compat"
    )


def test_legacy_guide_arch_shim_marks_deprecated():
    with open(SHIM_PATH) as f:
        parts = f.read().split("---", 2)
    meta = yaml.safe_load(parts[1])
    assert meta["metadata"].get("deprecated") == "use rdd-arch"


def test_legacy_guide_arch_shim_body_is_short_notice():
    with open(SHIM_PATH) as f:
        content = f.read()
    body = content.split("---", 2)[2].strip()
    lines = [l for l in body.splitlines() if l.strip()]
    assert len(lines) <= 10, f"shim body must be short notice (≤10 lines), got {len(lines)}"
    assert "DEPRECATED" in body
    assert "rdd-arch" in body


def test_legacy_guide_arch_shim_evolved_from_documents_rename():
    with open(SHIM_PATH) as f:
        parts = f.read().split("---", 2)
    meta = yaml.safe_load(parts[1])
    assert "rdd-arch" in meta["metadata"]["evolved-from"]