"""Tests for verdict cache schema v2.

Per fix-rdd-verifier-lifecycle-dashboard Task 3:
- Cache carries verification_state, failed_acs, schema_version, implementation_ref, source/ran_by
- Backward compat with v1 (version=1) reads

Per complete-project-yaml-config-gaps M2 Task 2.4:
- cache_key() supports provider=hook with SHA+command-hash composite
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.cache import (
    verdict_cache, read_verdict_cache, is_cache_fresh,
    _cache_path, _SCHEMA_VERSION, cache_key,
)


def test_cache_path():
    p = _cache_path(Path("/tmp/proj"), "ch-x")
    assert p == Path("/tmp/proj/.rddf/state/.ac-verdict-ch-x.json")


def test_cache_v2_full_fields(tmp_path):
    verdict_cache(
        tmp_path, "ch-x", "abc123",
        [{"ac_id": "AC-1", "status": "fail", "reasoning": "missing"}],
        ran_by="rdd-verifier",
        verification_state="failed",
        failed_acs=["AC-1"],
        implementation_ref="openspec/ch-x",
    )
    cached = read_verdict_cache(tmp_path, "ch-x")
    assert cached is not None
    assert cached["schema_version"] == 2
    assert cached["verification_state"] == "failed"
    assert cached["failed_acs"] == ["AC-1"]
    assert cached["implementation_ref"] == "openspec/ch-x"
    assert cached["ran_by"] == "rdd-verifier"
    assert cached["codebase_commit"] == "abc123"


def test_cache_default_source_is_rdd_verifier(tmp_path):
    verdict_cache(tmp_path, "ch-x", "abc", [], ran_by="rdd-verifier")
    cached = read_verdict_cache(tmp_path, "ch-x")
    assert cached["source"] == "rdd-verifier"
    assert cached["ran_by"] == "rdd-verifier"


def test_cache_archive_gate_fallback_source(tmp_path):
    verdict_cache(tmp_path, "ch-x", "abc", [], ran_by="archive_gate_check")
    cached = read_verdict_cache(tmp_path, "ch-x")
    assert cached["source"] == "archive_gate_check"


def test_cache_v1_legacy_reads_as_v1(tmp_path):
    legacy = {
        "version": 1,
        "change": "ch-x",
        "codebase_commit": "old_sha",
        "verdict": [],
        "ran_at": "2026-08-20T00:00:00Z",
        "ran_by": "rdd-verifier",
    }
    cache_dir = tmp_path / ".rddf" / "state"
    cache_dir.mkdir(parents=True)
    (_cache_path(tmp_path, "ch-x")).write_text(json.dumps(legacy))
    cached = read_verdict_cache(tmp_path, "ch-x")
    assert cached is not None
    assert cached["version"] == 1
    assert cached.get("schema_version") is None
    assert "verification_state" not in cached


def test_is_cache_fresh_when_sha_matches(tmp_path):
    verdict_cache(tmp_path, "ch-x", "sha-abc", [], ran_by="rdd-verifier")
    assert is_cache_fresh(tmp_path, "ch-x", "sha-abc")


def test_is_cache_stale_when_sha_differs(tmp_path):
    verdict_cache(tmp_path, "ch-x", "sha-old", [], ran_by="rdd-verifier")
    assert not is_cache_fresh(tmp_path, "ch-x", "sha-new")


def test_is_cache_missing_returns_false(tmp_path):
    assert not is_cache_fresh(tmp_path, "ch-x", "any-sha")


def test_cache_failed_acs_serialized_as_list(tmp_path):
    verdict_cache(tmp_path, "ch-y", "abc", [], ran_by="rdd-verifier",
                  failed_acs=["AC-1", "AC-3"])
    cached = read_verdict_cache(tmp_path, "ch-y")
    assert cached["failed_acs"] == ["AC-1", "AC-3"]


def test_schema_version_constant_is_2():
    assert _SCHEMA_VERSION == 2


# ============================================================================
# M2 Task 2.4 (complete-project-yaml-config-gaps M2):
# cache_key supports provider=hook with SHA+command-hash composite
# ============================================================================


def test_cache_key_default_provider_is_llm(tmp_path):
    """cache_key with no provider defaults to 'llm' (backward compat)."""
    key = cache_key("ch-x", tmp_path)
    key_explicit = cache_key("ch-x", tmp_path, provider="llm")
    assert isinstance(key, str)
    assert len(key) == 64  # SHA256 hex digest
    assert key == key_explicit


def test_cache_key_hook_differs_from_llm(tmp_path):
    """cache_key with provider=hook must differ from provider=llm."""
    key_llm = cache_key("ch-x", tmp_path, provider="llm")
    key_hook = cache_key("ch-x", tmp_path, provider="hook")
    assert key_llm != key_hook


def test_cache_key_hook_includes_command_path(tmp_path):
    """Two hook commands produce different cache keys (prevent cross-hook poisoning)."""
    hook_a = tmp_path / "hook_a.sh"
    hook_b = tmp_path / "hook_b.sh"
    key_a = cache_key("ch-x", tmp_path, provider="hook", hook_path=hook_a)
    key_b = cache_key("ch-x", tmp_path, provider="hook", hook_path=hook_b)
    assert key_a != key_b


def test_cache_key_stable_across_calls(tmp_path):
    """Same inputs → same SHA (deterministic)."""
    key1 = cache_key("ch-x", tmp_path, provider="hook", hook_path=tmp_path/"h.sh")
    key2 = cache_key("ch-x", tmp_path, provider="hook", hook_path=tmp_path/"h.sh")
    assert key1 == key2


def test_cache_key_different_changes_produce_different_keys(tmp_path):
    """Different change_name → different cache keys (per-change isolation)."""
    key_x = cache_key("ch-x", tmp_path, provider="llm")
    key_y = cache_key("ch-y", tmp_path, provider="llm")
    assert key_x != key_y
