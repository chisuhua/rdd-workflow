from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RULE_ANCHORS = [
    "Worktree Context Rule",
    "同一 worktree 内省略 cd",
    "跨 worktree 切换显式 cd",
]


def test_guide_ship_has_worktree_context_rule():
    doc = ROOT / "skills" / "guide-ship" / "SKILL.md"
    content = doc.read_text()
    for anchor in RULE_ANCHORS:
        assert anchor in content, f"guide-ship missing {anchor!r}"


def test_execute_has_worktree_context_rule():
    doc = ROOT / "skills" / "execute" / "SKILL.md"
    content = doc.read_text()
    for anchor in RULE_ANCHORS:
        assert anchor in content, f"execute missing {anchor!r}"
