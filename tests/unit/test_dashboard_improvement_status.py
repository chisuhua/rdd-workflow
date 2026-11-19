"""Unit tests for the improvement lifecycle classification and the Pending section.

Covers three layers that used to disagree with each other:

- ``_lib.dashboard.improvement_status.classify_improvement_status`` — the pure
  classifier (delivered vs still-open + a short display label).
- ``_lib.state_reader.read_improvement_entries`` — YAML front matter parsing
  (the format the ``add-improve`` skill emits) plus the legacy inline meta.
- ``collect()`` — the Pending section must EXCLUDE delivered improvements and
  must show the real status / priority / phase instead of hardcoded values.

Regression context: the section used to label every improvement "待讨论"
(status was hardcoded) and to read no metadata at all (the parser only
understood the pre-2026 ``**key**: value`` inline format), so every
doc-only improvement that never produced an OpenSpec change showed up as
"pending" forever.
"""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
SKILLS_ROOT = "/home/ubuntu/.agents/skills"


def _load():
    """Import the modules under test (paths are injected, never chdir'd)."""
    for path in (PROJECT_ROOT, SKILLS_ROOT):
        if path not in sys.path:
            sys.path.insert(0, path)
    from _lib.dashboard import collect
    from _lib.dashboard.improvement_status import classify_improvement_status
    from _lib.state_reader import read_improvement_entries
    return collect, classify_improvement_status, read_improvement_entries


def _make_project(tmp_path, improvements):
    """Create a minimal project tree with the given improvement files."""
    imp_dir = tmp_path / ".rddf" / "improvements"
    imp_dir.mkdir(parents=True, exist_ok=True)
    for name, text in improvements.items():
        (imp_dir / f"{name}.md").write_text(text, encoding="utf-8")
    # parse_approved_proposals_detailed reads this file; without it the whole
    # Pending section is skipped by the collect() error guard.
    (tmp_path / "improvement-approved.md").write_text(
        "| header |\n|--|\n", encoding="utf-8"
    )
    return str(tmp_path)


# --------------------------------------------------------------------------
# classifier
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected_label",
    [
        ("✅ **已归档**(2026-11-13 · per 台账 Entry #405)", "已归档"),
        ("✅ **已完成并归档**（2026-11-19 立项 #487 → 归档 #492）", "已归档"),
        ("✅ **已完成**(2026-11-02)—— 队列 #12", "已完成"),
        ("✅ **已实施**(2026-11-05 实施 / 2026-11-06 回填 per Entry #250)", "已实施"),
        ("🟢 已实施并验收(2026-11-12 起草 → 实施 → 验收)", "已完成"),
        ("Archived", "已归档"),
    ],
)
def test_delivered_markers_are_terminal(raw, expected_label):
    _, classify, _ = _load()
    terminal, label = classify(raw)
    assert terminal is True
    assert label == expected_label


@pytest.mark.parametrize(
    "raw,expected_label",
    [
        ("📋 **Draft**（2026-11-19 立项；未创建 OpenSpec change）", "Draft"),
        ("🟡 **已立项**(2026-11-16 · 台账 Entry #448)", "已立项"),
        ("🔴 **未立项(backlog)**", "未立项"),
        ("🟡 **待立项**(2026-11-18 起草)", "待立项"),
    ],
)
def test_open_markers_are_not_terminal(raw, expected_label):
    _, classify, _ = _load()
    terminal, label = classify(raw)
    assert terminal is False
    assert label == expected_label


def test_partially_closed_stays_visible():
    """A part-closed item still owes a human decision ⇒ must stay listed."""
    _, classify, _ = _load()
    raw = (
        "🟢 **C++ 侧已闭合(2026-11-19)** —— change x 的 T4.4 已删 "
        "`validate_module_params`;⛔ **Python 生成期诉求仍未闭合**"
    )
    terminal, label = classify(raw)
    assert terminal is False
    assert label == "部分闭合"


def test_trailing_prose_does_not_flip_a_delivered_marker():
    """Prose after the leading marker may mention residual work — it must not
    turn a delivered item back into a pending one."""
    _, classify, _ = _load()
    raw = "✅ **已归档**(2026-11-12)—— 唯一未达成项 = D-1 待裁(verifier + 用户)"
    terminal, _label = classify(raw)
    assert terminal is True


def test_empty_status_falls_back_to_pending_label():
    _, classify, _ = _load()
    assert classify("") == (False, "待讨论")
    assert classify("   ") == (False, "待讨论")


# --------------------------------------------------------------------------
# state_reader
# --------------------------------------------------------------------------

def test_read_improvement_entries_parses_yaml_front_matter(tmp_path):
    _, _, read_entries = _load()
    project = _make_project(
        tmp_path,
        {
            "yaml-imp": (
                "---\n"
                "name: yaml-imp\n"
                "priority: P1\n"
                "phase: phase-3\n"
                "category: bugfix\n"
                "type: bug\n"
                "状态: ✅ **已归档**(2026-11-19)\n"
                "created: 2026-11-19\n"
                "---\n\n"
                "# improvement: yaml-imp\n"
            )
        },
    )
    entries = read_entries(project)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["name"] == "yaml-imp"
    assert entry["priority"] == "P1"
    assert entry["phase"] == "phase-3"
    assert entry["category"] == "bugfix"
    assert entry["status"] == "✅ **已归档**(2026-11-19)"


def test_read_improvement_entries_supports_chinese_aliases(tmp_path):
    _, _, read_entries = _load()
    project = _make_project(
        tmp_path,
        {
            "cn-imp": (
                "---\n"
                "name: cn-imp\n"
                "优先级: P2\n"
                "阶段: phase-1\n"
                "状态: 📋 **Draft**\n"
                "---\n\n"
                "# improvement: cn-imp\n"
            )
        },
    )
    entry = read_entries(project)[0]
    assert entry["priority"] == "P2"
    assert entry["phase"] == "phase-1"
    assert entry["status"] == "📋 **Draft**"


def test_read_improvement_entries_keeps_legacy_inline_meta(tmp_path):
    """Pre-2026 files carry ``**key**: value`` pairs on the 3rd line."""
    _, _, read_entries = _load()
    project = _make_project(
        tmp_path,
        {
            "legacy-imp": (
                "# legacy-imp\n"
                "\n"
                "**优先级**: P1 | **阶段**: phase-2\n"
                "\n"
                "body\n"
            )
        },
    )
    entry = read_entries(project)[0]
    assert entry["name"] == "legacy-imp"
    assert entry["priority"] == "P1"
    assert entry["phase"] == "phase-2"


def test_read_improvement_entries_without_metadata(tmp_path):
    _, _, read_entries = _load()
    project = _make_project(tmp_path, {"bare": "# bare\n"})
    entry = read_entries(project)[0]
    assert entry["name"] == "bare"
    assert entry["status"] == ""
    assert entry["priority"] == ""


# --------------------------------------------------------------------------
# dashboard Pending section
# --------------------------------------------------------------------------

def test_pending_excludes_delivered_improvement(tmp_path):
    """A delivered improvement must NOT be listed as pending."""
    collect, _, _ = _load()
    project = _make_project(
        tmp_path,
        {
            "done-imp": (
                "---\n"
                "name: done-imp\n"
                "priority: P1\n"
                "状态: ✅ **已归档**(2026-11-19)\n"
                "---\n\n"
                "# done-imp\n"
            )
        },
    )
    data = collect(project)
    assert "done-imp" not in [s.name for s in data.suggestions]
    assert data.pending_suggestions == 0


def test_pending_shows_real_status_and_metadata(tmp_path):
    """The row must carry the file's own status / priority / phase."""
    collect, _, _ = _load()
    project = _make_project(
        tmp_path,
        {
            "open-imp": (
                "---\n"
                "name: open-imp\n"
                "priority: P2\n"
                "phase: phase-10\n"
                "category: bugfix\n"
                "状态: 📋 **Draft**（2026-11-19 立项）\n"
                "---\n\n"
                "# open-imp\n"
            )
        },
    )
    data = collect(project)
    assert data.pending_suggestions == 1
    row = data.suggestions[0]
    assert row.name == "open-imp"
    assert row.status == "Draft"
    assert row.priority == "P2"
    assert row.phase == "phase-10"
    assert row.category == "bugfix"


def test_pending_keeps_improvement_without_status(tmp_path):
    """No 状态 at all ⇒ legacy behaviour (listed as 待讨论)."""
    collect, _, _ = _load()
    project = _make_project(tmp_path, {"bare": "# bare\n"})
    data = collect(project)
    assert "bare" in [s.name for s in data.suggestions]
    assert data.suggestions[0].status == "待讨论"
