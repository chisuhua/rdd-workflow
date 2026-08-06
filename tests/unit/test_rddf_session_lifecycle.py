import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def _read_skill(name):
    path = os.path.join(ROOT, "skills", name, "SKILL.md")
    with open(path) as f:
        return f.read()


def test_guide_design_entry_hook_has_skill_root_source():
    """Phase 1 entry hook must source skill_root.sh before resolve_rdd_skill_dir."""
    content = _read_skill("guide-design")
    entry_block = content.split("rddf_session_hook_entry")[0]
    assert "skill_root.sh" in entry_block, (
        "guide-design entry hook missing skill_root.sh source - "
        "resolve_rdd_skill_dir will be undefined"
    )


def test_guide_design_close_hook_has_skill_root_source():
    """design-done close hook must source skill_root.sh before resolve_rdd_skill_dir."""
    content = _read_skill("guide-design")
    close_block = content.split("rddf_session_hook_close")[0]
    assert "skill_root.sh" in close_block, (
        "guide-design close hook missing skill_root.sh source"
    )


def test_guide_plan_and_ship_hooks_have_skill_root_source():
    """guide-plan/guide-ship entry+close hooks already source skill_root.sh."""
    for name in ("guide-plan", "guide-ship"):
        content = _read_skill(name)
        for hook in ("rddf_session_hook_entry", "rddf_session_hook_close"):
            assert hook in content, f"{name} missing {hook}"
            block = content.split(hook)[0]
            assert "skill_root.sh" in block, (
                f"{name} {hook} missing skill_root.sh source"
            )


def test_entry_hook_has_graceful_fallback():
    """Entry hook source line must include fallback paths (not single hardcode)."""
    content = _read_skill("guide-design")
    entry_block = content.split("rddf_session_hook_entry")[0]
    assert ".opencode/_lib/skill_root.sh" in entry_block
    assert "$HOME/.agents/_lib/skill_root.sh" in entry_block
