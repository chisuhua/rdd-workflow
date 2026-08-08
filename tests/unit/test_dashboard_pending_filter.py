"""Unit tests for fix-proposal-approved-missing-after-archive dashboard filter."""
import os
import sys
import tempfile
from pathlib import Path


def _setup_env(tmpdir):
    """Re-exec import under sys.path."""
    sys.path.insert(0, "/workspace/project/rdd-workflow")
    sys.path.insert(0, "/home/ubuntu/.agents/skills")
    os.chdir(tmpdir)


def test_archived_change_excluded_from_pending():
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_env(tmpdir)
        Path("improvements").mkdir()
        Path("openspec/changes/archive/2026-08-08-foo").mkdir(parents=True)
        Path("improvements/foo.md").write_text("# foo")
        Path("proposal-approved.md").write_text("| header |\n|--|\n")
        from _lib.dashboard import collect
        data = collect(tmpdir)
        names = [s.name for s in data.suggestions]
        assert "foo" not in names, f"archived foo should not be in pending: {names}"
        assert data.pending_suggestions == 0


def test_approved_change_excluded_from_pending():
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_env(tmpdir)
        Path("improvements").mkdir()
        Path("improvements/bar.md").write_text("# bar")
        Path("proposal-approved.md").write_text(
            "| [bar](improvements/bar.md) | P1 | 2026-01-01 |\n"
        )
        from _lib.dashboard import collect
        data = collect(tmpdir)
        names = [s.name for s in data.suggestions]
        assert "bar" not in names


def test_pending_improvement_still_in_pending():
    with tempfile.TemporaryDirectory() as tmpdir:
        _setup_env(tmpdir)
        Path("improvements").mkdir()
        Path("improvements/draft.md").write_text("# draft")
        Path("proposal-approved.md").write_text("| header |\n|--|\n")
        from _lib.dashboard import collect
        data = collect(tmpdir)
        names = [s.name for s in data.suggestions]
        assert "draft" in names
        assert data.pending_suggestions == 1
