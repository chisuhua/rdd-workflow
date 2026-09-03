"""Tests for planner_attach (validated proposal attach)."""
from __future__ import annotations

import pytest

from _lib.planner_attach import AttachError, attach_proposal, list_valid_projects, list_valid_phases


def _setup_roadmap(parent, themes, phases):
    rmp = parent / ".rddf" / "roadmap.md"
    rmp.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"| {p} | {t} | active | | |" for p, t in zip(phases, themes))
    rmp.write_text(f"# Roadmap\n\n## Phase Skeleton\n| Phase | Theme | Status | Started | Done |\n|-------|-------|--------|---------|------|\n{rows}\n\n<!-- AUTO-INDEX -->\n")


def _setup_improvement(parent, name, *, fm_extra=""):
    imp = parent / ".rddf" / "improvements" / f"{name}.md"
    imp.parent.mkdir(parents=True, exist_ok=True)
    imp.write_text(f"---\nname: {name}\npriority: P2\n{fm_extra}---\n\n# proposal\n")


def test_list_valid_projects_reads_skeleton_themes(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar", "baz qux"], phases=["phase-2", "phase-3"])
    assert list_valid_projects(tmp_path) == {"foo bar", "baz qux"}


def test_list_valid_phases_reads_skeleton_and_fragment_ids(tmp_path):
    _setup_roadmap(tmp_path, themes=["t"], phases=["phase-2"])
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-extra.md").write_text("---\nid: phase-extra\nkind: phase\n---\n")
    assert list_valid_phases(tmp_path) == {"phase-2", "phase-extra"}


def test_attach_writes_roadmap_ref_and_preserves_other_frontmatter(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1", fm_extra="custom_key: keep_me\n")
    attach_proposal(project_root=tmp_path, proposal="imp1", project_id="foo bar", phase="phase-2")
    text = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    assert "project_id: foo bar" in text
    assert "phase: phase-2" in text
    assert "custom_key: keep_me" in text
    assert "priority: P2" in text


def test_attach_is_idempotent_for_same_mapping(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1")
    attach_proposal(project_root=tmp_path, proposal="imp1", project_id="foo bar", phase="phase-2")
    first = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    attach_proposal(project_root=tmp_path, proposal="imp1", project_id="foo bar", phase="phase-2")
    second = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    assert first == second


def test_attach_rejects_unknown_project(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1")
    with pytest.raises(AttachError, match="project_id not in roadmap"):
        attach_proposal(project_root=tmp_path, proposal="imp1", project_id="nope", phase="phase-2")


def test_attach_rejects_unknown_phase(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1")
    with pytest.raises(AttachError, match="phase not in roadmap"):
        attach_proposal(project_root=tmp_path, proposal="imp1", project_id="foo bar", phase="phase-nope")


def test_attach_rejects_malformed_frontmatter_without_writing(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    imp = tmp_path / ".rddf" / "improvements" / "broken.md"
    imp.parent.mkdir(parents=True)
    imp.write_text("---\nname: x\n: bad: yaml: :\n---\n")
    original = imp.read_text()
    with pytest.raises(AttachError):
        attach_proposal(project_root=tmp_path, proposal="broken", project_id="foo bar", phase="phase-2")
    assert imp.read_text() == original


def test_attach_rejects_path_traversal(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    with pytest.raises(AttachError, match="invalid proposal"):
        attach_proposal(project_root=tmp_path, proposal="../escape", project_id="foo bar", phase="phase-2")


def test_attach_does_not_modify_other_files(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1")
    _setup_improvement(tmp_path, "imp2")
    other = (tmp_path / ".rddf" / "improvements" / "imp2.md").read_text()
    attach_proposal(project_root=tmp_path, proposal="imp1", project_id="foo bar", phase="phase-2")
    assert (tmp_path / ".rddf" / "improvements" / "imp2.md").read_text() == other


def test_attach_rejects_overwrite_without_explicit_flag(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2", "phase-3"])
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-3.md").write_text("---\nid: phase-3\nkind: phase\n---\n")
    imp = tmp_path / ".rddf" / "improvements" / "imp1.md"
    imp.parent.mkdir(parents=True)
    imp.write_text("---\nname: imp1\npriority: P2\nroadmap_ref:\n  project_id: foo bar\n  phase: phase-2\n---\n\n# proposal\n")
    with pytest.raises(AttachError, match="existing roadmap_ref differs"):
        attach_proposal(project_root=tmp_path, proposal="imp1", project_id="foo bar", phase="phase-3")


def test_attach_overwrite_replaces_divergent_mapping(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar", "bar baz"], phases=["phase-2", "phase-3"])
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-3.md").write_text("---\nid: phase-3\nkind: phase\n---\n")
    imp = tmp_path / ".rddf" / "improvements" / "imp1.md"
    imp.parent.mkdir(parents=True)
    imp.write_text("---\nname: imp1\npriority: P2\nroadmap_ref:\n  project_id: foo bar\n  phase: phase-2\n---\n\n# proposal\n")
    attach_proposal(
        project_root=tmp_path, proposal="imp1",
        project_id="bar baz", phase="phase-3", overwrite=True,
    )
    text = imp.read_text()
    assert "project_id: bar baz" in text
    assert "phase: phase-3" in text
    assert "project_id: foo bar" not in text


def test_attach_overwrite_false_rejects_divergent_mapping(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2", "phase-3"])
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-3.md").write_text("---\nid: phase-3\nkind: phase\n---\n")
    imp = tmp_path / ".rddf" / "improvements" / "imp1.md"
    imp.parent.mkdir(parents=True)
    imp.write_text("---\nname: imp1\npriority: P2\nroadmap_ref:\n  project_id: foo bar\n  phase: phase-2\n---\n\n# proposal\n")
    original = imp.read_text()
    with pytest.raises(AttachError, match="existing roadmap_ref differs"):
        attach_proposal(
            project_root=tmp_path, proposal="imp1",
            project_id="foo bar", phase="phase-3",
        )
    assert imp.read_text() == original


def test_attach_theme_idempotent_when_existing_omits_theme(tmp_path):
    """theme=None on second call matches existing {project_id, phase} (theme ignored)."""
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1")
    attach_proposal(project_root=tmp_path, proposal="imp1",
                    project_id="foo bar", phase="phase-2", theme="t")
    first = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    attach_proposal(project_root=tmp_path, proposal="imp1",
                    project_id="foo bar", phase="phase-2", theme=None)
    second = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    assert "theme: t" in first
    assert first == second


def test_attach_accepts_fragment_main_theme_as_project_id(tmp_path):
    """fragment 主题 field is a valid backup source for project_id."""
    _setup_roadmap(tmp_path, themes=["skeleton theme"], phases=["phase-2"])
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-2.md").write_text(
        "---\nid: phase-2\nkind: phase\n主题: fragment theme\n---\n"
    )
    _setup_improvement(tmp_path, "imp1")
    attach_proposal(project_root=tmp_path, proposal="imp1",
                    project_id="fragment theme", phase="phase-2")
    text = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    assert "project_id: fragment theme" in text


def test_attach_logs_warning_when_fragment_theme_conflicts(tmp_path, caplog):
    import logging
    _setup_roadmap(tmp_path, themes=["skeleton theme"], phases=["phase-2"])
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-2.md").write_text(
        "---\nid: phase-2\nkind: phase\n主题: fragment fallback\n---\n"
    )
    _setup_improvement(tmp_path, "imp1")
    with caplog.at_level(logging.WARNING, logger="_lib.planner_attach"):
        attach_proposal(project_root=tmp_path, proposal="imp1",
                        project_id="fragment fallback", phase="phase-2")
    assert any("Theme conflict" in r.message or "fallback" in r.message for r in caplog.records)