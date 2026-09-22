"""Tests for roadmap_feature_check (cat-roadmap-feature).

Per feat-roadmap-discovery-completion proposal AC-5.
"""
from __future__ import annotations

import json
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


def _make_roadmap_md(tmp_path: Path, feature_ids: list[str] | None = None) -> None:
    """Create .rddf/roadmap.md with AUTO-INDEX and Features section."""
    (tmp_path / ".rddf").mkdir(parents=True, exist_ok=True)
    features_section = ""
    if feature_ids:
        features_section = "\n### Features\n"
        for fid in feature_ids:
            features_section += f"- `{fid}` — test theme (refs: phase-1)\n"
    (tmp_path / ".rddf" / "roadmap.md").write_text(
        "# Roadmap\n<!-- AUTO-INDEX -->\n\n"
        "## Fragment Index (auto-generated)\n"
        "\n### Phases\n- `phase-1` — test\n"
        f"{features_section}\n"
    )


def _make_iteration(
    tmp_path: Path,
    feature_ids: list[str],
    status_map: dict[str, str] | None = None,
) -> None:
    """Build iteration.json. status_map overrides per-feature status (default: 'ready')."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    status_map = status_map or {}
    feature_view_features = {
        fid: {
            "name": fid,
            "status": status_map.get(fid, "ready"),
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
    (state_dir / "iteration.json").write_text(json.dumps(payload))


# ---------------------------------------------------------------------------
# Tests
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
    _make_iteration(tmp_path, ["feat-active"])
    _make_roadmap_md(tmp_path, ["feat-active"])
    _make_agents_md(tmp_path, (
        "<!-- AUTO: feature fragments start -->\n\n"
        "| id | status | phase_refs | theme |\n"
        "|---|---|---|---|\n"
        "| `feat-active` | active | phase-1 | 测试主题 |\n"
        "\n_auto-generated_\n"
        "<!-- AUTO: feature fragments end -->\n\n"
        "# AGENTS.md\n"
    ))
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_missing_non_status_required_field_reports_warning(tmp_path):
    """Feature frontmatter lacks 主题 field but status present → WARNING finding."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-x", (
        "---\n"
        "id: feat-x\nkind: feature\nstatus: active\n"
        "phase_refs: [phase-1]\n---\n\nbody\n"
    ))
    _make_roadmap_md(tmp_path, ["feat-x"])
    findings = run_check(project_root=tmp_path)
    warnings = [f for f in findings if f.severity == Severity.WARNING]
    assert any(
        "feat-x" in f.snippet and "主题" in f.snippet for f in warnings
    )
    # Should NOT have CRITICAL for missing status since status is present
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert not any("feat-x" in f.snippet for f in critical)


def test_missing_status_field_reports_critical(tmp_path):
    """Feature frontmatter lacks status field → CRITICAL finding."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-x", (
        "---\n"
        "id: feat-x\nkind: feature\n"
        "phase_refs: [phase-1]\n主题: 测试\n---\n\nbody\n"
    ))
    _make_roadmap_md(tmp_path, ["feat-x"])
    findings = run_check(project_root=tmp_path)
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert any(
        "feat-x" in f.snippet and "status" in f.snippet for f in critical
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
    _make_iteration(tmp_path, ["feat-active"])
    _make_roadmap_md(tmp_path, ["feat-active"])
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
    _make_roadmap_md(tmp_path, ["feat-x"])
    _make_iteration(tmp_path, [])
    findings = run_check(project_root=tmp_path)
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert any(
        "feat-x" in f.snippet and "iteration.json" in f.file
        for f in critical
    )


def test_done_fragment_missing_from_roadmap_auto_index_reports_critical(tmp_path):
    """Fragment status=done but missing from .rddf/roadmap.md AUTO-INDEX → CRITICAL."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-done", (
        "---\n"
        "id: feat-done\nkind: feature\nstatus: done\n"
        "phase_refs: [phase-1]\n主题: 测试\n---\n\nbody\n"
    ))
    # AUTO-INDEX has NO features section
    _make_roadmap_md(tmp_path, feature_ids=None)
    findings = run_check(project_root=tmp_path)
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert any(
        "feat-done" in f.snippet and "AUTO-INDEX" in f.snippet
        for f in critical
    )


def test_fragment_in_auto_index_but_no_file_reports_critical(tmp_path):
    """AUTO-INDEX references a fragment that doesn't exist on disk → CRITICAL."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    # No features on disk
    _make_roadmap_md(tmp_path, ["feat-ghost"])
    findings = run_check(project_root=tmp_path)
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert any(
        "feat-ghost" in f.snippet and "AUTO-INDEX" in f.snippet
        for f in critical
    )


def test_iteration_json_status_mismatch_done_vs_ready_reports_warning(tmp_path):
    """Fragment status=done but iteration.json shows status=ready → WARNING."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-done-but-not", (
        "---\n"
        "id: feat-done-but-not\nkind: feature\nstatus: done\n"
        "phase_refs: [phase-1]\n主题: 测试\n---\n\nbody\n"
    ))
    _make_roadmap_md(tmp_path, ["feat-done-but-not"])
    _make_iteration(tmp_path, ["feat-done-but-not"], {"feat-done-but-not": "ready"})
    findings = run_check(project_root=tmp_path)
    warnings = [f for f in findings if f.severity == Severity.WARNING]
    assert any(
        "feat-done-but-not" in f.snippet
        and "fragment status=done" in f.snippet
        and "status=ready" in f.snippet
        for f in warnings
    )


def test_agents_md_sentinel_missing_reports_warning(tmp_path):
    """AGENTS.md exists but AUTO sentinel block missing → WARNING."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-x", (
        "---\n"
        "id: feat-x\nkind: feature\nstatus: active\n"
        "phase_refs: [phase-1]\n主题: 测试\n---\n\nbody\n"
    ))
    _make_roadmap_md(tmp_path, ["feat-x"])
    _make_agents_md(tmp_path, "# AGENTS.md\n\nSome content without sentinels.\n")
    findings = run_check(project_root=tmp_path)
    warnings = [f for f in findings if f.severity == Severity.WARNING]
    assert any(
        "AGENTS.md" in f.file and "sentinel" in f.snippet.lower()
        for f in warnings
    )


def test_agents_md_status_mismatch_reports_warning(tmp_path):
    """Fragment status=active but AGENTS.md shows done → WARNING."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-x", (
        "---\n"
        "id: feat-x\nkind: feature\nstatus: active\n"
        "phase_refs: [phase-1]\n主题: 测试\n---\n\nbody\n"
    ))
    _make_roadmap_md(tmp_path, ["feat-x"])
    _make_agents_md(tmp_path, (
        "<!-- AUTO: feature fragments start -->\n\n"
        "| id | status | phase_refs | theme |\n"
        "|---|---|---|---|\n"
        "| `feat-x` | done | phase-1 | 测试 |\n"
        "\n_auto-generated_\n"
        "<!-- AUTO: feature fragments end -->\n\n"
    ))
    findings = run_check(project_root=tmp_path)
    warnings = [f for f in findings if f.severity == Severity.WARNING]
    assert any(
        "feat-x" in f.snippet and "status=active" in f.snippet and "status=done" in f.snippet
        for f in warnings
    )


def test_fragment_not_in_agents_md_reports_critical(tmp_path):
    """Fragment exists on disk but not in AGENTS.md AUTO block → CRITICAL."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-orphan", (
        "---\n"
        "id: feat-orphan\nkind: feature\nstatus: active\n"
        "phase_refs: [phase-1]\n主题: 测试\n---\n\nbody\n"
    ))
    _make_roadmap_md(tmp_path, ["feat-orphan"])
    # AGENTS.md has different feature
    _make_agents_md(tmp_path, (
        "<!-- AUTO: feature fragments start -->\n\n"
        "| id | status | phase_refs | theme |\n"
        "|---|---|---|---|\n"
        "| `feat-other` | active | phase-1 | other |\n"
        "\n_auto-generated_\n"
        "<!-- AUTO: feature fragments end -->\n\n"
    ))
    findings = run_check(project_root=tmp_path)
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert any(
        "feat-orphan" in f.snippet and "AGENTS.md" in f.file
        for f in critical
    )


def test_iteration_json_stale_feature_reports_warning(tmp_path):
    """iteration.json has a feature entry with no matching fragment file → WARNING."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_feature(tmp_path, "feat-real", (
        "---\n"
        "id: feat-real\nkind: feature\nstatus: active\n"
        "phase_refs: [phase-1]\n主题: 测试\n---\n\nbody\n"
    ))
    _make_roadmap_md(tmp_path, ["feat-real"])
    # iteration includes both real and stale feature
    _make_iteration(tmp_path, ["feat-real", "feat-stale"], {"feat-real": "active", "feat-stale": "done"})
    findings = run_check(project_root=tmp_path)
    warnings = [f for f in findings if f.severity == Severity.WARNING]
    assert any(
        "feat-stale" in f.snippet
        and "iteration.json" in f.file
        and "no matching fragment" in f.snippet
        for f in warnings
    )


def test_multiple_views_all_aligned_no_findings(tmp_path):
    """All views (fragment, AUTO-INDEX, iteration, AGENTS.md) aligned → 0 findings."""
    from checks.roadmap_feature_check import run as run_check

    _make_phase(tmp_path)
    _make_phase(tmp_path, "phase-2")
    _make_feature(tmp_path, "feat-alice", (
        "---\n"
        "id: feat-alice\nkind: feature\nstatus: done\n"
        "phase_refs: [phase-1]\n主题: Alice\n---\n\nbody\n"
    ))
    _make_feature(tmp_path, "feat-bob", (
        "---\n"
        "id: feat-bob\nkind: feature\nstatus: active\n"
        "phase_refs: [phase-2]\n主题: Bob\n---\n\nbody\n"
    ))
    _make_roadmap_md(tmp_path, ["feat-alice", "feat-bob"])
    _make_iteration(
        tmp_path,
        ["feat-alice", "feat-bob"],
        {"feat-alice": "done", "feat-bob": "ready"},
    )
    _make_agents_md(tmp_path, (
        "<!-- AUTO: feature fragments start -->\n\n"
        "| id | status | phase_refs | theme |\n"
        "|---|---|---|---|\n"
        "| `feat-alice` | done | phase-1 | Alice |\n"
        "| `feat-bob` | active | phase-2 | Bob |\n"
        "\n_auto-generated_\n"
        "<!-- AUTO: feature fragments end -->\n\n"
        "# AGENTS.md\n"
    ))
    findings = run_check(project_root=tmp_path)
    assert findings == []