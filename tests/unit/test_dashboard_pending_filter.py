"""Unit tests for fix-proposal-approved-missing-after-archive dashboard filter."""
import os
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = "/workspace/project/rdd-workflow"
SKILLS_ROOT = "/home/ubuntu/.agents/skills"


def test_archived_change_excluded_from_pending(tmp_path):
    """Archived changes (openspec/changes/archive/<date>-<name>/) MUST NOT show as pending."""
    tmp = tmp_path
    (tmp / "improvements").mkdir()
    (tmp / "openspec/changes/archive/2026-08-08-foo").mkdir(parents=True)
    (tmp / "improvements/foo.md").write_text("# foo")
    (tmp / "proposal-approved.md").write_text("| header |\n|--|\n")
    sys.path.insert(0, PROJECT_ROOT)
    sys.path.insert(0, SKILLS_ROOT)
    from _lib.dashboard import collect
    data = collect(str(tmp))
    names = [s.name for s in data.suggestions]
    assert "foo" not in names, f"archived foo should not be in pending: {names}"
    assert data.pending_suggestions == 0


def test_approved_change_excluded_from_pending(tmp_path):
    """Approved changes (proposal-approved.md main table) MUST NOT show as pending."""
    tmp = tmp_path
    (tmp / "improvements").mkdir()
    (tmp / "improvements/bar.md").write_text("# bar")
    (tmp / "proposal-approved.md").write_text(
        "| [bar](improvements/bar.md) | P1 | 2026-01-01 |\n"
    )
    sys.path.insert(0, PROJECT_ROOT)
    sys.path.insert(0, SKILLS_ROOT)
    from _lib.dashboard import collect
    data = collect(str(tmp))
    names = [s.name for s in data.suggestions]
    assert "bar" not in names


def test_pending_improvement_still_in_pending(tmp_path):
    """Improvements not in proposal-approved.md AND not archived MUST show as pending."""
    tmp = tmp_path
    (tmp / "improvements").mkdir()
    (tmp / "improvements/draft.md").write_text("# draft")
    (tmp / "proposal-approved.md").write_text("| header |\n|--|\n")
    sys.path.insert(0, PROJECT_ROOT)
    sys.path.insert(0, SKILLS_ROOT)
    from _lib.dashboard import collect
    data = collect(str(tmp))
    names = [s.name for s in data.suggestions]
    assert "draft" in names
    assert data.pending_suggestions == 1
