"""Tests for arch_complete_revision writer in write_arch_handoff.py.

wave-handoff contract v2.1 (additive):
- arch_complete_revision: int — monotonically incremented per write
- Reader in planner_feedback._current_arch_handoff_revision reads it
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


def _call_write(project_root: str) -> dict:
    from skills.rdd_arch.scripts.write_arch_handoff import write_arch_handoff
    return write_arch_handoff(
        project_root,
        discovered_adr_dir="docs/adr",
        discovered_roadmap_path="roadmap.md",
        discovered_architecture_dir="docs/architecture",
        discovered_adr_pattern="ADR-*.md",
        discovered_adr_dir_found="true",
        discovered_roadmap_found="true",
        discovered_arch_found="true",
        discovered_adr_dir_tried="1",
        discovered_roadmap_tried="1",
        discovered_arch_tried="1",
        roadmap_exists_bool="true",
    )


def test_first_write_revision_is_one(tmp_path: Path):
    """No prior handoff → first write sets arch_complete_revision=1."""
    project_root = str(tmp_path)
    handoff = _call_write(project_root)
    assert handoff["arch_complete_revision"] == 1

    path = tmp_path / ".rddf" / "state" / ".arch-handoff.json"
    data = json.loads(path.read_text())
    assert data["arch_complete_revision"] == 1


def test_write_increments_revision(tmp_path: Path):
    """Two writes → revision 1 → 2 (baseline + 1)."""
    project_root = str(tmp_path)
    first = _call_write(project_root)
    assert first["arch_complete_revision"] == 1
    second = _call_write(project_root)
    assert second["arch_complete_revision"] == 2


def test_revision_persists_in_handoff_dict(tmp_path: Path):
    """Read back handoff contains arch_complete_revision field."""
    project_root = str(tmp_path)
    _call_write(project_root)
    path = tmp_path / ".rddf" / "state" / ".arch-handoff.json"
    data = json.loads(path.read_text())
    assert "arch_complete_revision" in data
    assert isinstance(data["arch_complete_revision"], int)
    assert data["arch_complete_revision"] >= 1


def test_revision_survives_concurrent_writes_via_lock(tmp_path: Path):
    """50 concurrent writes under FileLock → final revision == 50 (no lost increments)."""
    project_root = str(tmp_path)

    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(_call_write, project_root) for _ in range(50)]
        for f in futures:
            f.result()

    path = tmp_path / ".rddf" / "state" / ".arch-handoff.json"
    data = json.loads(path.read_text())
    assert data["arch_complete_revision"] == 50


def test_revision_starts_at_one_for_legacy_handoff(tmp_path: Path):
    """Legacy handoff (no arch_complete_revision) → next write sets to 1."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    handoff_path = state_dir / ".arch-handoff.json"
    legacy = {
        "version": 2,
        "arch_complete_at": "2026-09-01T10:00:00+00:00",
        "adr_count": 0,
        "completed_adr_ids": [],
        "roadmap_exists": False,
        "current_phase": "default",
    }
    handoff_path.write_text(json.dumps(legacy))

    project_root = str(tmp_path)
    handoff = _call_write(project_root)
    assert handoff["arch_complete_revision"] == 1