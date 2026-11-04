"""Tests for the v4 planner-handoff stage detection in workflow_synthesizer.

The synthesizer used to read the v3 ``.plan-handoff.json`` and branch on an
``active_changes`` field that ``planner-handoff-v1`` does not define. Every
v4 project therefore looked like a "leftover" and the tree could never
recommend ``rdd-planner``.

These tests lock the v4 behavior:
  - arch done + no planner handoff        -> rdd-planner
  - planner handoff + active change       -> rdd-builder
  - planner handoff + no active change    -> rdd-builder (变更生成)
  - corrupt planner handoff               -> rdd-planner (not "complete")
"""
from __future__ import annotations

import json
from pathlib import Path

from skills._lib.workflow_synthesizer import synthesize


ARCH_HANDOFF = {"version": 1, "adr_dir": "docs/adr", "discovered": True, "adr_count": 1}
PLANNER_HANDOFF = {
    "schema": "planner-handoff-v1",
    "version": 1,
    "owner": "rdd-planner",
    "planner_complete_at": "2026-01-01",
    "current_sprint": "sprint-1",
    "recommended_route": "full",
    "awaiting_builder": ["add-x"],
}


def _make_project(tmp_path: Path, handoffs: dict, active_change: bool = False) -> str:
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    for name, payload in handoffs.items():
        if isinstance(payload, str):
            (state / name).write_text(payload, encoding="utf-8")
        else:
            (state / name).write_text(json.dumps(payload), encoding="utf-8")
    if active_change:
        (tmp_path / "openspec" / "changes" / "add-x").mkdir(parents=True)
    return str(tmp_path)


def test_arch_only_recommends_planner(tmp_path):
    project = _make_project(tmp_path, {".arch-handoff.json": ARCH_HANDOFF})
    rec = synthesize(project)
    assert rec.suggested_action == "rdd-planner"
    assert "planner" in rec.reason


def test_planner_handoff_with_active_change_recommends_builder(tmp_path):
    project = _make_project(
        tmp_path,
        {".arch-handoff.json": ARCH_HANDOFF, ".planner-handoff.json": PLANNER_HANDOFF},
        active_change=True,
    )
    rec = synthesize(project)
    assert rec.suggested_action == "rdd-builder"
    assert "残留" not in rec.reason


def test_planner_handoff_without_active_change_recommends_builder(tmp_path):
    project = _make_project(
        tmp_path,
        {".arch-handoff.json": ARCH_HANDOFF, ".planner-handoff.json": PLANNER_HANDOFF},
        active_change=False,
    )
    rec = synthesize(project)
    assert rec.suggested_action == "rdd-builder"


def test_corrupt_planner_handoff_is_not_treated_as_complete(tmp_path):
    project = _make_project(
        tmp_path,
        {
            ".arch-handoff.json": ARCH_HANDOFF,
            ".planner-handoff.json": '{"schema":"planner-handoff-v1", TRUNCATED',
        },
    )
    rec = synthesize(project)
    assert rec.suggested_action == "rdd-planner"


def test_planner_handoff_without_active_changes_field_is_not_misread_as_zero(tmp_path):
    """planner-handoff-v1 has no `active_changes` key — the old code read it
    as 0 and reported every project as a leftover."""
    project = _make_project(
        tmp_path,
        {".arch-handoff.json": ARCH_HANDOFF, ".planner-handoff.json": PLANNER_HANDOFF},
        active_change=True,
    )
    rec = synthesize(project)
    assert "残留" not in rec.reason
    assert "leftover" not in rec.reason.lower()
