"""Propose phase auto cross-repo detection (3 acceptance cases)."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from _lib.propose_cross_repo_hooks import (
    detect_hub_scope,
    inject_hub_rfc_placeholder,
    update_cross_repo_cache,
)


def _make_change(tmp_path: Path, caps):
    """Create a fake change dir with specs/<cap>/spec.md for each cap."""
    change_dir = tmp_path / "change"
    change_dir.mkdir()
    specs = change_dir / "specs"
    for c in caps:
        cap_dir = specs / c
        cap_dir.mkdir(parents=True)
        (cap_dir / "spec.md").write_text("## ADDED Requirements\n")
    return change_dir


def test_local_only_change_no_placeholder(tmp_path):
    """Change with only local capabilities (no 'api-*' or 'cross-*') → no placeholder."""
    change = _make_change(tmp_path, ["local-feature", "internal-utils"])
    assert detect_hub_scope(change) == []
    proposal = "# Test\n\n## Why\nTBD\n\n## What Changes\nTBD\n"
    out = inject_hub_rfc_placeholder(proposal, [])
    assert "Hub RFC" not in out
    assert out == proposal


def test_cross_repo_change_injects_placeholder(tmp_path):
    """Change with api-* capability → Hub RFC placeholder inserted."""
    change = _make_change(tmp_path, ["api-auth", "local-cache"])
    scopes = detect_hub_scope(change)
    assert scopes == ["api-auth"]
    proposal = "# Test\n\n## Why\nTBD\n\n## What Changes\nTBD\n"
    out = inject_hub_rfc_placeholder(proposal, scopes)
    assert "## Hub RFC Placeholder" in out
    assert "api-auth" in out


def test_cross_repo_cache_hit_skips_regen(tmp_path):
    """If change_name already in cache, update_cross_repo_cache returns cached scopes without recompute."""
    cache_file = tmp_path / "cache.json"
    cached_scopes = ["api-auth", "api-profile"]
    cache_file.write_text(json.dumps({"api-auth": cached_scopes}))
    out = update_cross_repo_cache("api-auth", [], cache_path=cache_file)
    assert out == cached_scopes