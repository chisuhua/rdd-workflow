"""Tests for Fragment dataclass + load_fragments / get_fragment / list_active_fragments.

ADR-0016 v2 hierarchical roadmap structure — additive API on _lib/roadmap_state.py.
AC-1.5: ≥6 new functions (3 in this file, 3 in test_roadmap_state_render_aggregate.py).
AC-1.6: Fragment dataclass ≥8 fields.
AC-1.11: existing roadmap_state.py functions unchanged (verified via git diff).
AC-1.15: ≥15 unit tests total across Fragment + 6 functions (this file contributes 6).
"""
import pytest
from pathlib import Path
import sys

# Add project root so 'import _lib' works (consistent with conftest.py pattern)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from _lib.roadmap_state import (
    Fragment,
    load_fragments,
    get_fragment,
    list_active_fragments,
)


@pytest.fixture
def fragments_dir(tmp_path):
    """Create .rddf/roadmap/{phases,features,archive}/ with 4 sample fragments."""
    phases = tmp_path / ".rddf" / "roadmap" / "phases"
    features = tmp_path / ".rddf" / "roadmap" / "features"
    archive = tmp_path / ".rddf" / "roadmap" / "archive"
    for d in (phases, features, archive):
        d.mkdir(parents=True)
    (phases / "phase-2.md").write_text(
        "---\n"
        "id: phase-2\n"
        "kind: phase\n"
        "status: active\n"
        "phase_refs: []\n"
        "主题: 用户认证\n"
        "---\n\n"
        "## Phase 2 内容\n"
    )
    (phases / "phase-3.md").write_text(
        "---\n"
        "id: phase-3\n"
        "kind: phase\n"
        "status: done\n"
        "phase_refs: []\n"
        "主题: GPU 基础设施\n"
        "---\n\n"
        "## Phase 3 内容\n"
    )
    (features / "auth-v2.md").write_text(
        "---\n"
        "id: feat-auth-v2\n"
        "kind: feature\n"
        "status: active\n"
        "phase_refs: [phase-2, phase-3]\n"
        "主题: RBAC 权限模型\n"
        "---\n\n"
        "## Auth v2 内容\n"
    )
    (archive / "phase-1.md").write_text(
        "---\n"
        "id: phase-1\n"
        "kind: phase\n"
        "status: archived\n"
        "phase_refs: []\n"
        "主题: 基础架构\n"
        "---\n\n"
        "## Phase 1 (archived)\n"
    )
    return tmp_path / ".rddf" / "roadmap"


def test_fragment_dataclass_minimum_8_fields():
    """AC-1.6: Fragment MUST have at least 8 fields."""
    fields = Fragment.__dataclass_fields__
    assert len(fields) >= 8, f"Fragment must have ≥8 fields, got {len(fields)}: {list(fields.keys())}"
    # Verify expected field names
    expected = {"id", "kind", "status", "phase_refs", "theme", "file_path", "frontmatter", "body"}
    assert expected.issubset(set(fields.keys())), f"Missing required fields: {expected - set(fields.keys())}"


def test_fragment_dataclass_phase_round_trip(fragments_dir):
    """Phase fragment parses to Fragment with correct fields."""
    frag = get_fragment(str(fragments_dir), "phase-2")
    assert frag.id == "phase-2"
    assert frag.kind == "phase"
    assert frag.status == "active"
    assert frag.phase_refs == []
    assert frag.theme == "用户认证"
    assert frag.file_path.endswith("phase-2.md")
    assert isinstance(frag.frontmatter, dict)
    assert "## Phase 2" in frag.body


def test_fragment_dataclass_feature_with_phase_refs(fragments_dir):
    """Feature fragment with phase_refs list round-trips correctly."""
    frag = get_fragment(str(fragments_dir), "feat-auth-v2")
    assert frag.kind == "feature"
    assert frag.phase_refs == ["phase-2", "phase-3"]
    assert frag.theme == "RBAC 权限模型"


def test_load_fragments_excludes_archived_by_default(fragments_dir):
    """load_fragments(include_archived=False) excludes status='archived'."""
    all_frags = load_fragments(str(fragments_dir), include_archived=False)
    ids = {f.id for f in all_frags}
    assert "phase-1" not in ids, "archived fragment must be excluded by default"
    assert {"phase-2", "phase-3", "feat-auth-v2"}.issubset(ids)


def test_load_fragments_include_archived(fragments_dir):
    """load_fragments(include_archived=True) returns all fragments."""
    with_archived = load_fragments(str(fragments_dir), include_archived=True)
    ids = {f.id for f in with_archived}
    assert ids == {"phase-1", "phase-2", "phase-3", "feat-auth-v2"}


def test_load_fragments_missing_dir_returns_empty(tmp_path):
    """Backward compat: load_fragments on missing dir returns [] (v1 handoff behavior)."""
    result = load_fragments(str(tmp_path / "nonexistent"))
    assert result == []


def test_get_fragment_not_found_raises_keyerror(fragments_dir):
    """get_fragment raises KeyError for missing id."""
    with pytest.raises(KeyError, match="phase-99"):
        get_fragment(str(fragments_dir), "phase-99")


def test_list_active_fragments_filters_status(fragments_dir):
    """list_active_fragments returns only status='active' by default."""
    active = list_active_fragments(str(fragments_dir))
    assert len(active) == 2
    assert all(f.status == "active" for f in active)
    ids = {f.id for f in active}
    assert ids == {"phase-2", "feat-auth-v2"}


def test_list_active_fragments_by_kind(fragments_dir):
    """list_active_fragments(kind='phase') returns only phase fragments."""
    phases = list_active_fragments(str(fragments_dir), kind="phase")
    assert len(phases) == 1
    assert phases[0].id == "phase-2"  # phase-3 is done, phase-1 is archived


def test_list_active_fragments_kind_feature(fragments_dir):
    """list_active_fragments(kind='feature') returns only feature fragments."""
    features = list_active_fragments(str(fragments_dir), kind="feature")
    assert len(features) == 1
    assert features[0].id == "feat-auth-v2"
