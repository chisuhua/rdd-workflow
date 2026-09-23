"""Verify each rdd-* SKILL.md declares Stage 1 Hook entry/close (AC-6~10)."""
from pathlib import Path

SKILLS = [
    ("skills/rdd-arch/SKILL.md", "AC-6"),
    ("skills/rdd-planner/SKILL.md", "AC-7"),
    ("skills/rdd-builder/SKILL.md", "AC-8"),
    ("skills/rdd-verifier/SKILL.md", "AC-9"),
    ("skills/rdd-quick/SKILL.md", "AC-10"),
]


def test_skill_md_has_mandatory_hook_section():
    for path, ac in SKILLS:
        content = Path(path).read_text()
        assert "rddf_session_hook_entry" in content, f"{ac}: {path} missing hook_entry"
        assert "rddf_session_hook_close" in content, f"{ac}: {path} missing hook_close"
        # Mandatory keyword (中文/英文都可)
        assert ("强制" in content or "mandatory" in content.lower() or \
                "must" in content.lower()), \
            f"{ac}: {path} hook not declared as mandatory"