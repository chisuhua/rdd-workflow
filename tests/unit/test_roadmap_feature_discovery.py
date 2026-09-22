"""Tests for improve-roadmap-feature-discovery proposal.

Covers rddf roadmap list-features CLI + rddf roadmap --update-agent-md.
Per proposal AC-1, AC-2, AC-9.

Setup mirrors test_roadmap_state_fragments.py:
  - tmp_path fixture builds .rddf/roadmap/{phases,features,archive}/
  - AGENTS.md built per-case with optional AUTO sentinels
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from _lib.roadmap_state import (
    AGENTS_AUTO_SENTINEL_END,
    AGENTS_AUTO_SENTINEL_START,
    Fragment,
    list_features,
    update_agent_md,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_with_features(tmp_path):
    """Build a complete project_root with .rddf/roadmap/features + AGENTS.md."""
    frags = tmp_path / ".rddf" / "roadmap"
    (frags / "phases").mkdir(parents=True)
    (frags / "features").mkdir(parents=True)
    (frags / "archive").mkdir(parents=True)

    # phase fragment (prerequisite for phase_refs validation if added later)
    (frags / "phases" / "phase-1.md").write_text(
        "---\nid: phase-1\nkind: phase\nstatus: active\n"
        "phase_refs: []\n主题: phase-1\n---\n\nbody\n"
    )
    (frags / "phases" / "phase-2.md").write_text(
        "---\nid: phase-2\nkind: phase\nstatus: active\n"
        "phase_refs: []\n主题: phase-2\n---\n\nbody\n"
    )

    (frags / "features" / "feat-auth-v2.md").write_text(
        "---\nid: feat-auth-v2\nkind: feature\nstatus: active\n"
        "phase_refs: [phase-1, phase-2]\n"
        "主题: RBAC 权限模型\n---\n\nbody\n"
    )
    (frags / "features" / "feat-deprecate-legacy.md").write_text(
        "---\nid: feat-deprecate-legacy\nkind: feature\nstatus: done\n"
        "phase_refs: [phase-1]\n主题: 测试已删除\n---\n\nbody\n"
    )
    (frags / "archive" / "feat-legacy-old.md").write_text(
        "---\nid: feat-legacy-old\nkind: feature\nstatus: archived\n"
        "phase_refs: [phase-1]\n主题: legacy\n---\n\nbody\n"
    )

    # AGENTS.md without AUTO block
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS.md\n\nExisting manual section.\n", encoding="utf-8"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# AC-1: list-features CLI
# ---------------------------------------------------------------------------

def test_list_features_table_renders_3_features_including_archived(project_with_features):
    """AC-1 + AC-9: list-features default (include_archived=True) returns all features."""
    fragments_dir = str(project_with_features / ".rddf" / "roadmap")
    out = list_features(fragments_dir, fmt="table")
    # All 3 features (active + done + archived) appear
    assert "feat-auth-v2" in out
    assert "feat-deprecate-legacy" in out
    assert "feat-legacy-old" in out
    # Table has header + separator + 3 data rows
    rows = [r for r in out.strip().splitlines() if r.strip()]
    assert len(rows) == 5  # header + separator + 3 features
    # Theme appears in output
    assert "RBAC 权限模型" in out


def test_list_features_excludes_archived_when_requested(project_with_features):
    """AC-9 MUST: --no-archived filters out status='archived' features."""
    fragments_dir = str(project_with_features / ".rddf" / "roadmap")
    out = list_features(fragments_dir, fmt="table", include_archived=False)
    assert "feat-auth-v2" in out
    assert "feat-deprecate-legacy" in out
    assert "feat-legacy-old" not in out  # archived filtered out


def test_list_features_json_output_is_valid(project_with_features):
    """AC-1: --format=json returns parseable JSON."""
    import json
    fragments_dir = str(project_with_features / ".rddf" / "roadmap")
    out = list_features(fragments_dir, fmt="json")
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert len(parsed) == 3
    ids = {f["id"] for f in parsed}
    assert ids == {"feat-auth-v2", "feat-deprecate-legacy", "feat-legacy-old"}
    # Verify required fields per AC-1
    sample = parsed[0]
    assert {"id", "status", "phase_refs", "theme", "file"} <= set(sample.keys())


def test_list_features_yaml_output_has_required_keys(project_with_features):
    """AC-1: --format=yaml returns parseable YAML."""
    fragments_dir = str(project_with_features / ".rddf" / "roadmap")
    out = list_features(fragments_dir, fmt="yaml")
    # Minimal YAML check: contains id/status/theme strings
    assert "feat-auth-v2" in out
    assert "RBAC 权限模型" in out
    assert "active" in out


def test_list_features_yaml_shape_matches_json(project_with_features):
    """Oracle critical issue #1: YAML and JSON output must have identical shape."""
    pytest.importorskip("yaml")
    import json
    import yaml as _yaml

    fragments_dir = str(project_with_features / ".rddf" / "roadmap")
    parsed_json = json.loads(list_features(fragments_dir, fmt="json"))
    parsed_yaml = _yaml.safe_load(list_features(fragments_dir, fmt="yaml"))

    assert isinstance(parsed_json, list)
    assert isinstance(parsed_yaml, list)
    assert len(parsed_json) == len(parsed_yaml)
    assert parsed_json == parsed_yaml, (
        f"YAML shape diverges from JSON: json={parsed_json!r}, yaml={parsed_yaml!r}"
    )


def test_list_features_yaml_empty_dir(tmp_path):
    """YAML output for empty fragments dir returns empty string (not a malformed skeleton)."""
    pytest.importorskip("yaml")
    import yaml as _yaml

    frags = tmp_path / ".rddf" / "roadmap"
    for sub in ("phases", "features", "archive"):
        (frags / sub).mkdir(parents=True)
    out = list_features(str(frags), fmt="yaml")
    parsed = _yaml.safe_load(out) if out.strip() else []
    assert parsed == []


def test_list_features_invalid_format_raises():
    """AC-1 edge case: invalid fmt → ValueError."""
    with pytest.raises(ValueError, match="fmt must be table/json/yaml"):
        list_features("/nonexistent", fmt="xml")


def test_list_features_empty_dir_returns_help_message(tmp_path):
    """Edge case: no features → friendly message, not crash."""
    frags = tmp_path / ".rddf" / "roadmap"
    (frags / "phases").mkdir(parents=True)
    (frags / "features").mkdir(parents=True)
    (frags / "archive").mkdir(parents=True)
    out = list_features(str(frags), fmt="table")
    assert "no feature fragments" in out.lower()


# ---------------------------------------------------------------------------
# AC-2 + AC-9: update-agent-md
# ---------------------------------------------------------------------------

def test_update_agent_md_inserts_block_when_no_sentinel(project_with_features):
    """AC-2: missing sentinels → AUTO block inserted at top of file."""
    result = update_agent_md(
        project_root=str(project_with_features),
        agents_md_path="AGENTS.md",
        fragments_dir=".rddf/roadmap",
    )
    assert result["inserted"] is True
    assert result["feature_count"] == 3  # all included

    agents_text = (project_with_features / "AGENTS.md").read_text()
    assert AGENTS_AUTO_SENTINEL_START in agents_text
    assert AGENTS_AUTO_SENTINEL_END in agents_text
    # All 3 features appear in AUTO block table
    for fid in ("feat-auth-v2", "feat-deprecate-legacy", "feat-legacy-old"):
        assert fid in agents_text


def test_update_agent_md_replaces_existing_block_idempotently(project_with_features):
    """AC-9 (MUST idempotent): 2 calls produce identical second-call output (updated, not inserted)."""
    update_agent_md(
        project_root=str(project_with_features),
        agents_md_path="AGENTS.md",
        fragments_dir=".rddf/roadmap",
    )
    text_after_first = (project_with_features / "AGENTS.md").read_text()

    # Second call: must be 'updated' (not 'inserted') and produce identical text
    result2 = update_agent_md(
        project_root=str(project_with_features),
        agents_md_path="AGENTS.md",
        fragments_dir=".rddf/roadmap",
    )
    assert result2["inserted"] is False
    assert result2["feature_count"] == 3

    text_after_second = (project_with_features / "AGENTS.md").read_text()
    assert text_after_first == text_after_second, "Second call must be idempotent"


def test_update_agent_md_preserves_other_sections(project_with_features):
    """AC-9 (MUST NOT): other AGENTS.md sections must be untouched."""
    update_agent_md(
        project_root=str(project_with_features),
        agents_md_path="AGENTS.md",
        fragments_dir=".rddf/roadmap",
    )
    agents_text = (project_with_features / "AGENTS.md").read_text()
    # The pre-existing manual section must still be present
    assert "Existing manual section." in agents_text
    # And the H1 header too
    assert "# AGENTS.md" in agents_text


def test_update_agent_md_creates_minimal_file_when_missing(tmp_path):
    """Edge case: AGENTS.md does not exist → create with AUTO block."""
    frags = tmp_path / ".rddf" / "roadmap"
    (frags / "phases").mkdir(parents=True)
    (frags / "features").mkdir(parents=True)
    (frags / "archive").mkdir(parents=True)
    (frags / "features" / "feat-x.md").write_text(
        "---\nid: feat-x\nkind: feature\nstatus: active\n"
        "phase_refs: []\n主题: x\n---\n"
    )
    result = update_agent_md(
        project_root=str(tmp_path),
        agents_md_path="AGENTS.md",
        fragments_dir=".rddf/roadmap",
    )
    assert result["inserted"] is True
    assert result["feature_count"] == 1
    assert (tmp_path / "AGENTS.md").exists()
    text = (tmp_path / "AGENTS.md").read_text()
    assert AGENTS_AUTO_SENTINEL_START in text
    assert "feat-x" in text


def test_update_agent_md_after_deleting_feature(project_with_features):
    """AC-9 (delete-feature regression): AUTO block reflects post-delete state."""
    # Initial: 3 features
    update_agent_md(
        project_root=str(project_with_features),
        agents_md_path="AGENTS.md",
        fragments_dir=".rddf/roadmap",
    )
    agents_text = (project_with_features / "AGENTS.md").read_text()
    assert "feat-auth-v2" in agents_text
    assert "feat-deprecate-legacy" in agents_text
    assert "feat-legacy-old" in agents_text

    # Delete one feature
    (project_with_features / ".rddf" / "roadmap" / "features" / "feat-auth-v2.md").unlink()

    # Refresh: deleted feature removed from block
    result = update_agent_md(
        project_root=str(project_with_features),
        agents_md_path="AGENTS.md",
        fragments_dir=".rddf/roadmap",
    )
    assert result["feature_count"] == 2
    agents_text = (project_with_features / "AGENTS.md").read_text()
    assert "feat-auth-v2" not in agents_text
    assert "feat-deprecate-legacy" in agents_text
    assert "feat-legacy-old" in agents_text


def test_update_agent_md_uses_sentinel_constants():
    """Constants are exported and stable (downstream docs/tests depend on them)."""
    assert AGENTS_AUTO_SENTINEL_START == "<!-- AUTO: feature fragments start -->"
    assert AGENTS_AUTO_SENTINEL_END == "<!-- AUTO: feature fragments end -->"


# ---------------------------------------------------------------------------
# Sanity: list_features filters kind=phase (only features, not phases)
# ---------------------------------------------------------------------------

def test_list_features_excludes_phase_instructions(project_with_features):
    """Only kind='feature' appear; kind='phase' are filtered out."""
    fragments_dir = str(project_with_features / ".rddf" / "roadmap")
    out = list_features(fragments_dir, fmt="table")
    # phase-1 / phase-2 are kind='phase' and must NOT appear in features listing
    # (the table only contains phase_refs strings, not feature rows for them)
    rows = [
        line for line in out.splitlines()
        if line.startswith("feat-")
    ]
    assert len(rows) == 3  # only feature rows, not phase rows