"""Tests for roadmap_feature_check (cat-roadmap-feature).

Per feat-roadmap-discovery-completion proposal AC-5.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402


def _make_feature(tmp_path: Path, name: str, frontmatter: str) -> None:
    features_dir = tmp_path / ".rddf" / "roadmap" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / f"{name}.md").write_text(frontmatter)


def _make_phase(tmp_path: Path, name: str = "phase-1") -> None:
    phases_dir = tmp_path / ".rddf" / "roadmap" / "phases"
    phases_dir.mkdir(parents=True, exist_ok=True)
    (phases_dir / f"{name}.md").write_text(
        "---\n"
        f"id: {name}\nkind: phase\nstatus: active\n"
        "phase_refs: []\n主题: phase-1\n---\n\nbody\n"
    )


def _make_agents_md(tmp_path: Path, content: str) -> None:
    (tmp_path / "AGENTS.md").write_text(content)


def _make_iteration(tmp_path: Path, feature_id_bases: list[str]) -> None:
    """Build iteration.json containing `feat-<base>` for each base in feature_id_bases."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    feature_ids = [f"feat-{b}" for b in feature_id_bases]
    changes = [
        {
            "name": fid,
            "added_at": "2026-09-22T00:00:00+00:00",
            "status": "proposed",
            "phase": "phase-1",
            "category": "general",
            "priority": "P1",
            "parent_feature": fid,
        }
        for fid in feature_ids
    ]
    feature_view_features = {
        fid: {
            "name": fid,
            "status": "ready",
            "change_names": [fid],
            "change_count": 1,
            "archived_count": 0,
            "rollup_basis": "explicit",
            "depends_on": [],
            "blocks": [],
            "parallel_group": 0,
            "conflicts_with": [],
        }
        for fid in feature_ids
    }
    payload = {
        "version": 6,
        "updated_at": "2026-09-22T00:00:00+00:00",
        "current_phase": "default",
        "changes": changes,
        "feature_view": {
            "schema_version": 1,
            "updated_at": "2026-09-22T00:00:00+00:00",
            "features": feature_view_features,
            "execution_order": [],
        },
    }
    (state_dir / "iteration.json").write_text(__import__("json").dumps(payload))


# ---------------------------------------------------------------------------
# Tests (RED phase — these will FAIL until implementation is added)
# ---------------------------------------------------------------------------

def test_healthy_features_no_findings(tmp_path):
    """All features valid, iteration.json consistent, no AGENTS.md drift."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-active", (
        "---\n"
        "id: feat-active\nkind: feature\nstatus: active\n"
        "phase_refs: [phase-1]\n主题: 测试主题\n---\n\nbody\n"
    ))
    _make_iteration(tmp_path, ["active"])
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_missing_required_field_reports_warning(tmp_path):
    """Feature frontmatter lacks 主题 field → WARNING finding."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-x", (
        "---\n"
        "id: feat-x\nkind: feature\nstatus: active\n"
        "phase_refs: [phase-1]\n---\n\nbody\n"
    ))
    findings = run_check(project_root=tmp_path)
    warnings = [f for f in findings if f.severity == Severity.WARNING]
    assert any(
        "feat-x" in f.snippet and "主题" in f.snippet for f in warnings
    )


def test_agents_md_auto_block_stale_reports_critical(tmp_path):
    """AGENTS.md AUTO block contains stale feature id → CRITICAL finding."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-active", (
        "---\n"
        "id: feat-active\nkind: feature\nstatus: active\n"
        "phase_refs: [phase-1]\n主题: 测试\n---\n\nbody\n"
    ))
    _make_iteration(tmp_path, ["active"])
    _make_agents_md(tmp_path, (
        "<!-- AUTO: feature fragments start -->\n\n"
        "| id | status | phase_refs | theme |\n"
        "|---|---|---|---|\n"
        "| `feat-active` | active | phase-1 | 测试 |\n"
        "| `feat-deleted` | done | phase-1 | 不存在 |\n"
        "\n_auto-generated_\n"
        "<!-- AUTO: feature fragments end -->\n\n"
        "# AGENTS.md\n"
    ))
    findings = run_check(project_root=tmp_path)
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert any(
        "feat-deleted" in f.snippet and "AGENTS.md" in f.file
        for f in critical
    )


def test_iteration_json_missing_active_feature_reports_critical(tmp_path):
    """iteration.json feature_view missing an active feature → CRITICAL finding."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-x", (
        "---\n"
        "id: feat-x\nkind: feature\nstatus: active\n"
        "phase_refs: [phase-1]\n主题: 测试\n---\n\nbody\n"
    ))
    _make_iteration(tmp_path, [])
    findings = run_check(project_root=tmp_path)
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert any(
        "feat-x" in f.snippet and "iteration.json" in f.file
        for f in critical
    )