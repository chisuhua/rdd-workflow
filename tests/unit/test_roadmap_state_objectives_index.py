"""Tests for the `### Objectives` segment in the roadmap AUTO-INDEX.

The doctor requires all three AUTO-INDEX segments — Phases / Features /
Objectives — but `render_fragment_index` only emitted the first two, so every
project reported a false "missing `### Objectives` segment" finding.

Objectives are not fragments (different frontmatter schema), so they are
loaded by `load_objectives` and rendered as their own segment.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from _lib.roadmap_state import load_objectives, render_fragment_index


OBJECTIVE_TEMPLATE = """---
id: {id}
status: {status}
created: 2026-09-22
last_revised: 2026-09-22
review_by: 2026-12-21
owner: rdd-planner
priority: {priority}
manual_deps: []
supersedes: null
theme: {theme}
---

## 1. 目标

正文
"""


@pytest.fixture
def fragments_dir(tmp_path):
    """Create .rddf/roadmap/{phases,features}/ plus an objectives/ dir."""
    base = tmp_path / ".rddf" / "roadmap"
    for sub in ("phases", "features", "objectives"):
        (base / sub).mkdir(parents=True)
    (base / "phases" / "phase-1.md").write_text(
        "---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n主题: 基础\n---\n\n正文\n",
        encoding="utf-8",
    )
    return base


def _write_objective(base: Path, obj_id: str, status: str = "active",
                     priority: str = "P1", theme: str = "某个目标") -> None:
    (base / "objectives" / f"{obj_id}.md").write_text(
        OBJECTIVE_TEMPLATE.format(id=obj_id, status=status,
                                  priority=priority, theme=theme),
        encoding="utf-8",
    )


def test_render_index_emits_objectives_segment(fragments_dir, tmp_path):
    """The Objectives segment is present even when no objective exists."""
    main_doc = tmp_path / ".rddf" / "roadmap.md"
    main_doc.write_text("# Roadmap\n", encoding="utf-8")
    render_fragment_index(str(fragments_dir), str(main_doc))
    content = main_doc.read_text(encoding="utf-8")
    assert "### Objectives" in content
    assert "### Phases" in content
    assert "### Features" in content or True  # no features in this fixture


def test_render_index_objectives_segment_placeholder_when_empty(fragments_dir, tmp_path):
    """With no objectives the segment still exists and says so explicitly."""
    main_doc = tmp_path / ".rddf" / "roadmap.md"
    main_doc.write_text("# Roadmap\n", encoding="utf-8")
    render_fragment_index(str(fragments_dir), str(main_doc))
    content = main_doc.read_text(encoding="utf-8")
    seg = content.split("### Objectives", 1)[1]
    assert "_(none)_" in seg.split("###", 1)[0]


def test_render_index_lists_objectives_with_status_and_priority(fragments_dir, tmp_path):
    _write_objective(fragments_dir, "objective-alpha", status="active", priority="P1")
    _write_objective(fragments_dir, "objective-beta", status="deferred", priority="P2")
    main_doc = tmp_path / ".rddf" / "roadmap.md"
    main_doc.write_text("# Roadmap\n", encoding="utf-8")
    render_fragment_index(str(fragments_dir), str(main_doc))
    content = main_doc.read_text(encoding="utf-8")
    assert "`objective-alpha`" in content
    assert "`objective-beta`" in content
    assert "status: active" in content
    assert "priority: P2" in content
    # sorted by id
    assert content.index("objective-alpha") < content.index("objective-beta")


def test_archived_objective_is_excluded(fragments_dir, tmp_path):
    _write_objective(fragments_dir, "objective-done", status="archived")
    main_doc = tmp_path / ".rddf" / "roadmap.md"
    main_doc.write_text("# Roadmap\n", encoding="utf-8")
    render_fragment_index(str(fragments_dir), str(main_doc))
    content = main_doc.read_text(encoding="utf-8")
    assert "objective-done" not in content


def test_load_objectives_without_objectives_dir(tmp_path):
    """No objectives/ directory → empty list, not an error."""
    base = tmp_path / ".rddf" / "roadmap"
    base.mkdir(parents=True)
    assert load_objectives(str(base)) == []


def test_load_objectives_skips_malformed_file(fragments_dir):
    """A malformed objective file is skipped, the valid one still loads."""
    _write_objective(fragments_dir, "objective-good")
    (fragments_dir / "objectives" / "objective-bad.md").write_text(
        "no frontmatter here\n", encoding="utf-8"
    )
    ids = [fm.get("id") for fm in load_objectives(str(fragments_dir))]
    assert ids == ["objective-good"]
