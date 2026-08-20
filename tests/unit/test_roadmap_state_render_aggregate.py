"""Additional tests for render_fragment_index + aggregate_phase_progress (Task 4 / T6+T7)."""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from _lib.roadmap_state import (
    render_fragment_index,
    aggregate_phase_progress,
)


# Re-define fragments_dir fixture locally (pytest fixtures are file-scoped unless in conftest).
@pytest.fixture
def fragments_dir(tmp_path):
    """Create .rddf/roadmap/{phases,features,archive}/ with 4 sample fragments."""
    phases = tmp_path / ".rddf" / "roadmap" / "phases"
    features = tmp_path / ".rddf" / "roadmap" / "features"
    archive = tmp_path / ".rddf" / "roadmap" / "archive"
    for d in (phases, features, archive):
        d.mkdir(parents=True)
    (phases / "phase-2.md").write_text(
        "---\nid: phase-2\nkind: phase\nstatus: active\nphase_refs: []\n主题: 用户认证\n---\n\n## Phase 2 内容\n"
    )
    (phases / "phase-3.md").write_text(
        "---\nid: phase-3\nkind: phase\nstatus: done\nphase_refs: []\n主题: GPU 基础设施\n---\n\n## Phase 3 内容\n"
    )
    (features / "auth-v2.md").write_text(
        "---\nid: feat-auth-v2\nkind: feature\nstatus: active\nphase_refs: [phase-2, phase-3]\n主题: RBAC 权限模型\n---\n\n## Auth v2 内容\n"
    )
    (archive / "phase-1.md").write_text(
        "---\nid: phase-1\nkind: phase\nstatus: archived\nphase_refs: []\n主题: 基础架构\n---\n\n## Phase 1 (archived)\n"
    )
    return tmp_path / ".rddf" / "roadmap"


def test_render_fragment_index_writes_sentinel(tmp_path, fragments_dir):
    """render_fragment_index writes <!-- AUTO-INDEX --> sentinel grouping phases before features."""
    main_doc = tmp_path / ".rddf" / "roadmap.md"
    main_doc.write_text("# Roadmap\n\n## Phase Skeleton\n<!-- table here -->\n")
    render_fragment_index(str(fragments_dir), str(main_doc))
    content = main_doc.read_text()
    assert "<!-- AUTO-INDEX -->" in content
    # phases appear before features
    phase_idx = content.find("phase-2")
    feature_idx = content.find("feat-auth-v2")
    assert phase_idx < feature_idx, "phases must appear before features in auto-index"
    # Both phases and features section headers present
    assert "### Phases" in content
    assert "### Features" in content


def test_render_fragment_index_atomic_write(tmp_path, fragments_dir):
    """render_fragment_index uses tmp+rename (no partial writes)."""
    main_doc = tmp_path / ".rddf" / "roadmap.md"
    main_doc.write_text("# Roadmap\n")
    render_fragment_index(str(fragments_dir), str(main_doc))
    leftover = list(tmp_path.rglob("*.tmp"))
    assert leftover == [], f"Atomic write left tmp files: {leftover}"


def test_aggregate_phase_progress_counts_active_only(fragments_dir):
    """aggregate_phase_progress returns (active, total) for phase fragments only (excludes archived)."""
    active, total = aggregate_phase_progress(str(fragments_dir))
    # phase-2 is active, phase-3 is done, phase-1 is archived
    # active: 1, total: 2 (excludes archived by default)
    assert active == 1
    assert total == 2


def test_aggregate_phase_progress_empty_dir(tmp_path):
    """aggregate_phase_progress on non-existent dir returns (0, 0) (backward compat v1 handoff)."""
    active, total = aggregate_phase_progress(str(tmp_path / "nonexistent"))
    assert (active, total) == (0, 0)


def test_render_fragment_index_idempotent(tmp_path, fragments_dir):
    """Calling render_fragment_index twice doesn't duplicate the sentinel block."""
    main_doc = tmp_path / ".rddf" / "roadmap.md"
    main_doc.write_text("# Roadmap\n\n## Phase Skeleton\n")
    render_fragment_index(str(fragments_dir), str(main_doc))
    content_after_first = main_doc.read_text()
    render_fragment_index(str(fragments_dir), str(main_doc))
    content_after_second = main_doc.read_text()
    # Second call should be idempotent — same content (no duplicate index)
    assert content_after_first == content_after_second, "render_fragment_index is not idempotent"
