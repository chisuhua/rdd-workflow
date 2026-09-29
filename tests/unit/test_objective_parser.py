"""Tests for _lib/objective_parser.collect_active_objectives.

Bug X3 fix: planner_stage_entry.sh and planner_stage_exit.sh each had ~45
lines of identical inline Python parsing objectives and serializing as JSON.
This module consolidates that logic into a single source of truth.

Tests cover:
- AC-5: happy path returns JSON list of active+deferred objectives
- empty objectives directory returns "[]"
- malformed objective file is skipped (does not crash)
- status filter: only active/deferred included (excludes completed/archived)
- N/A markers filtered from next_sprint_candidates (per D9)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _write_objective(obj_dir: Path, name: str, status: str, candidates: str = "") -> None:
    """Helper: write a minimal objective file."""
    (obj_dir / f"{name}.md").write_text(
        "---\n"
        f"id: {name}\n"
        f"status: {status}\n"
        "created: 2026-09-28\n"
        "last_revised: 2026-09-28\n"
        "review_by: 2026-12-27\n"
        "owner: rdd-planner\n"
        "priority: P1\n"
        "manual_deps: []\n"
        f"theme: theme for {name}\n"
        "---\n\n"
        "# Objective body\n\n"
        f"## 10. next_sprint_candidates\n{candidates}\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# AC-5: Happy path
# ---------------------------------------------------------------------------


def test_collect_active_objectives_happy_path(tmp_path):
    """Returns JSON list with id, priority, status, review_by, theme, next_sprint_candidates."""
    obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
    obj_dir.mkdir(parents=True)
    _write_objective(obj_dir, "objective-test", "active", "- [ ] candidate A\n- [ ] candidate B")

    from _lib.objective_parser import collect_active_objectives
    result = json.loads(collect_active_objectives(tmp_path))
    assert len(result) == 1
    assert result[0]["id"] == "objective-test"
    assert result[0]["status"] == "active"
    assert result[0]["priority"] == "P1"
    assert result[0]["review_by"] == "2026-12-27"
    assert result[0]["theme"] == "theme for objective-test"
    assert result[0]["next_sprint_candidates"] == ["candidate A", "candidate B"]


# ---------------------------------------------------------------------------
# Edge case: empty / missing directory
# ---------------------------------------------------------------------------


def test_collect_active_objectives_empty_dir_returns_empty_array(tmp_path):
    """Missing or empty .rddf/roadmap/objectives/ returns '[]' (graceful)."""
    from _lib.objective_parser import collect_active_objectives
    assert collect_active_objectives(tmp_path) == "[]"


def test_collect_active_objectives_no_rddf_dir_returns_empty(tmp_path):
    """Project root without .rddf returns '[]'."""
    from _lib.objective_parser import collect_active_objectives
    assert collect_active_objectives(tmp_path) == "[]"


# ---------------------------------------------------------------------------
# Status filter: only active + deferred included
# ---------------------------------------------------------------------------


def test_collect_active_objectives_status_filter(tmp_path):
    """Only active + deferred included; completed + archived excluded."""
    obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
    obj_dir.mkdir(parents=True)
    _write_objective(obj_dir, "obj-active", "active")
    _write_objective(obj_dir, "obj-deferred", "deferred")
    _write_objective(obj_dir, "obj-completed", "completed")
    _write_objective(obj_dir, "obj-archived", "archived")

    from _lib.objective_parser import collect_active_objectives
    result = json.loads(collect_active_objectives(tmp_path))
    ids = {r["id"] for r in result}
    assert ids == {"obj-active", "obj-deferred"}, (
        f"status filter failed; got {ids!r}, expected {{'obj-active', 'obj-deferred'}}"
    )


# ---------------------------------------------------------------------------
# Malformed objective: skip without crashing
# ---------------------------------------------------------------------------


def test_collect_active_objectives_skips_malformed(tmp_path):
    """Malformed objective (missing frontmatter) is skipped, not raised."""
    obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
    obj_dir.mkdir(parents=True)
    # Good objective
    _write_objective(obj_dir, "obj-good", "active")
    # Malformed: no frontmatter
    (obj_dir / "obj-bad.md").write_text(
        "# No frontmatter here\n\nJust prose, no ---\n",
        encoding="utf-8",
    )

    from _lib.objective_parser import collect_active_objectives
    result = json.loads(collect_active_objectives(tmp_path))
    assert len(result) == 1
    assert result[0]["id"] == "obj-good"


# ---------------------------------------------------------------------------
# N/A markers filtered (per D9)
# ---------------------------------------------------------------------------


def test_collect_active_objectives_filters_na_markers(tmp_path):
    """Lines starting with 'N/A' (deferred markers per D9) are filtered out."""
    obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
    obj_dir.mkdir(parents=True)
    _write_objective(
        obj_dir,
        "obj-deferred",
        "deferred",
        "- [ ] real candidate\n"
        "- N/A — 维持 v3.2 deferred 决策\n"
        "- another real one\n",
    )

    from _lib.objective_parser import collect_active_objectives
    result = json.loads(collect_active_objectives(tmp_path))
    assert len(result) == 1
    candidates = result[0]["next_sprint_candidates"]
    assert candidates == ["real candidate", "another real one"], (
        f"N/A markers not filtered; got {candidates!r}"
    )


# ---------------------------------------------------------------------------
# Archive subdirectory excluded
# ---------------------------------------------------------------------------


def test_collect_active_objectives_excludes_archive_subdir(tmp_path):
    """objectives/archive/*.md are excluded (not in main listing)."""
    obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
    archive_dir = obj_dir / "archive"
    obj_dir.mkdir(parents=True)
    archive_dir.mkdir()
    _write_objective(obj_dir, "obj-active", "active")
    _write_objective(archive_dir, "obj-old", "active")

    from _lib.objective_parser import collect_active_objectives
    result = json.loads(collect_active_objectives(tmp_path))
    ids = {r["id"] for r in result}
    assert ids == {"obj-active"}, f"archive subdir leaked; got {ids!r}"


# ---------------------------------------------------------------------------
# Theme truncation (200 char limit)
# ---------------------------------------------------------------------------


def test_collect_active_objectives_truncates_long_theme(tmp_path):
    """Theme field truncated to 200 chars (consistent with prior inline behavior)."""
    obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
    obj_dir.mkdir(parents=True)
    long_theme = "x" * 500
    (obj_dir / "obj-long.md").write_text(
        "---\n"
        "id: obj-long\n"
        "status: active\n"
        "created: 2026-09-28\n"
        "last_revised: 2026-09-28\n"
        "review_by: 2026-12-27\n"
        "owner: rdd-planner\n"
        "priority: P1\n"
        "manual_deps: []\n"
        f"theme: {long_theme}\n"
        "---\n",
        encoding="utf-8",
    )

    from _lib.objective_parser import collect_active_objectives
    result = json.loads(collect_active_objectives(tmp_path))
    assert len(result[0]["theme"]) == 200


# ---------------------------------------------------------------------------
# Unicode/CJK theme preserved (ensure_ascii=False)
# ---------------------------------------------------------------------------


def test_collect_active_objectives_preserves_cjk(tmp_path):
    """Chinese theme values are preserved as-is (ensure_ascii=False)."""
    obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
    obj_dir.mkdir(parents=True)
    (obj_dir / "obj-cjk.md").write_text(
        "---\n"
        "id: obj-cjk\n"
        "status: active\n"
        "created: 2026-09-28\n"
        "last_revised: 2026-09-28\n"
        "review_by: 2026-12-27\n"
        "owner: rdd-planner\n"
        "priority: P1\n"
        "manual_deps: []\n"
        "theme: 统一 bypass audit + hub federation governance\n"
        "---\n",
        encoding="utf-8",
    )

    from _lib.objective_parser import collect_active_objectives
    raw = collect_active_objectives(tmp_path)
    assert "统一 bypass audit" in raw, "CJK chars escaped as \\uXXXX (ensure_ascii=True leaked)"
    result = json.loads(raw)
    assert result[0]["theme"] == "统一 bypass audit + hub federation governance"
