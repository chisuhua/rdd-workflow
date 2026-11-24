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
# English terminal markers (the 2026-11-17/18 batch writes `状态: implemented`)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected_label",
    [
        ("implemented (2026-11-17)", "已实施"),
        ("Implemented (2026-11-17)", "已实施"),
        ("implemented", "已实施"),
        (
            "implemented (2026-11-17 首轮 → 2026-11-18 architect 复核后补完 5 条 AC，复验通过)",
            "已实施",
        ),
        ("completed", "已完成"),
        ("Completed (2026-11-17)", "已完成"),
    ],
)
def test_english_delivered_markers_are_terminal(raw, expected_label):
    """The English vocabulary is the same contract as the Chinese one.

    Without it a delivered item stayed in the Pending pool with a truncated
    label ("implemented (202").
    """
    _, classify, _ = _load()
    terminal, label = classify(raw)
    assert terminal is True
    assert label == expected_label


@pytest.mark.parametrize(
    "raw,expected_label",
    [
        ("待审查", "待审查"),
        ("已推迟 (2026-08-14)", "已推迟"),
    ],
)
def test_review_and_deferred_markers_are_open(raw, expected_label):
    """「待审查」/「已推迟」 are pending — but they are not 「待讨论」."""
    _, classify, _ = _load()
    terminal, label = classify(raw)
    assert terminal is False
    assert label == expected_label


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


def test_read_improvement_entries_recovers_broken_yaml_front_matter(tmp_path):
    """A front matter that does not PARSE must not cost the whole metadata set.

    A multi-line plain scalar whose continuation line contains ``: `` makes
    PyYAML raise ScannerError; the old behaviour dropped priority / phase /
    category / status entirely (the row rendered as "待讨论" with "-" for
    every column).
    """
    _, _, read_entries = _load()
    project = _make_project(
        tmp_path,
        {
            "broken-imp": (
                "---\n"
                "优先级: P2\n"
                "来源: 2026-09-28 多次审计 (commit ab5ded7)\n"
                "  入口未正式文档化。新 skill 作者不知道:\n"
                "  - 有哪些模块可用\n"
                "阶段: v4.1 follow-up\n"
                "分类: documentation\n"
                "---\n\n"
                "# broken-imp\n"
            )
        },
    )
    entries = read_entries(project)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["priority"] == "P2"
    assert entry["phase"] == "v4.1 follow-up"
    assert entry["category"] == "documentation"
    # the breakage is reported, not swallowed
    assert "invalid YAML front matter" in entry.get("meta_parse_error", "")


def test_pending_reports_broken_front_matter(tmp_path):
    """A broken front matter must show up in the errors channel."""
    sys.path.insert(0, PROJECT_ROOT)
    from _lib.dashboard import collect_pending

    project = _make_project(
        tmp_path,
        {
            "broken-imp": (
                "---\n"
                "优先级: P2\n"
                "来源: text\n"
                "  trailing colon:\n"
                "阶段: v4\n"
                "---\n\n"
                "# broken-imp\n"
            )
        },
    )
    snap = collect_pending(project)
    assert [s.name for s in snap.suggestions] == ["broken-imp"]
    assert snap.suggestions[0].priority == "P2"
    assert any("broken-imp" in err for err in snap.errors)


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
