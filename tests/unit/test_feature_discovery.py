"""Unit tests for feature_discovery.list_active_features — improve-roadmap-feature-discovery.

Per improve-roadmap-feature-discovery proposal acceptance:
- list_active_features 正确枚举 features/*.md
- 空 features/ dir 返回空 list
- feature frontmatter 解析 (name, description, phase_refs)
- 设计 preflight 显示 active features
"""
import json
from pathlib import Path

import pytest


@pytest.fixture
def repo_with_features(tmp_path):
    """Build a repo with .rddf/roadmap/features/*.md."""
    features_dir = tmp_path / ".rddf" / "roadmap" / "features"
    features_dir.mkdir(parents=True)
    (features_dir / "feat-a.md").write_text(
        "---\nname: feat-a\ndescription: A feature\n---\n# feat-a\nphase-refs: [phase-1, phase-2]\n",
        encoding="utf-8",
    )
    (features_dir / "feat-b.md").write_text(
        "---\nname: feat-b\ndescription: B feature\n---\n",
        encoding="utf-8",
    )
    (features_dir / "no-name.md").write_text("# no-name\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_list_active_features_returns_all_with_name(repo_with_features):
    from skills.guide_design.scripts.feature_discovery import list_active_features
    features = list_active_features(repo_with_features)
    assert len(features) == 2
    names = {f["name"] for f in features}
    assert names == {"feat-a", "feat-b"}


def test_list_active_features_extracts_description(repo_with_features):
    from skills.guide_design.scripts.feature_discovery import list_active_features
    features = list_active_features(repo_with_features)
    by_name = {f["name"]: f for f in features}
    assert by_name["feat-a"]["description"] == "A feature"
    assert by_name["feat-b"]["description"] == "B feature"


def test_list_active_features_extracts_phase_refs(repo_with_features):
    from skills.guide_design.scripts.feature_discovery import list_active_features
    features = list_active_features(repo_with_features)
    by_name = {f["name"]: f for f in features}
    assert by_name["feat-a"]["phase_refs"] == ["phase-1", "phase-2"]
    assert by_name["feat-b"]["phase_refs"] == []


def test_list_active_features_empty_dir_returns_empty(tmp_path):
    from skills.guide_design.scripts.feature_discovery import list_active_features
    features = list_active_features(tmp_path)
    assert features == []


def test_list_active_features_skips_files_without_name(tmp_path):
    """Files without frontmatter name: are skipped (not errors)."""
    features_dir = tmp_path / ".rddf" / "roadmap" / "features"
    features_dir.mkdir(parents=True)
    (features_dir / "no-frontmatter.md").write_text("# no frontmatter\n", encoding="utf-8")
    from skills.guide_design.scripts.feature_discovery import list_active_features
    features = list_active_features(tmp_path)
    assert features == []


def test_list_active_features_missing_dir_returns_empty(tmp_path):
    """No .rddf/roadmap/features/ dir → returns empty list (graceful)."""
    from skills.guide_design.scripts.feature_discovery import list_active_features
    features = list_active_features(tmp_path)
    assert features == []