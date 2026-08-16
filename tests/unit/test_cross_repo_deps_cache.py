"""Tests for cross_repo_deps_cache (read/save/ttl)."""
import json
import time
from pathlib import Path
import pytest

from skills._lib.cross_repo_deps_cache import (
    load_cache, save_cache, is_cache_valid, CACHE_TTL_SECONDS,
)


def test_save_and_load(tmp_path):
    cache_file = tmp_path / "cache.json"
    data = {"graph": {"a": []}, "etas": {"a": 3}}
    save_cache(cache_file, "spokes-key", data)
    loaded = load_cache(cache_file, "spokes-key")
    assert loaded == data


def test_load_missing_returns_none(tmp_path):
    assert load_cache(tmp_path / "nope.json", "key") is None


def test_is_cache_valid_recent(tmp_path):
    cache_file = tmp_path / "cache.json"
    save_cache(cache_file, "k", {"v": 1})
    assert is_cache_valid(cache_file, "k") is True


def test_is_cache_valid_expired(tmp_path):
    cache_file = tmp_path / "cache.json"
    data = {"v": 1, "timestamp": time.time() - CACHE_TTL_SECONDS - 100}
    cache_file.write_text(json.dumps({"spokes-key": data}))
    assert is_cache_valid(cache_file, "spokes-key") is False
