"""Unit tests for cross_repo_gate.check_cross_repo_deps_blocked.

Covers 5 key paths from tasks.md 1.3:
1. no blocker
2. single blocker
3. cross-repo chain
4. cycle-detect
5. cache-hit (no second call to kahn)
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from skills._lib import cross_repo_gate
from skills._lib.cross_repo_gate import check_cross_repo_deps_blocked


def _write_cache(cache_path: Path, spokes_key: str, data: dict) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {spokes_key: {"data": data, "timestamp": 9999999999}}
    cache_path.write_text(json.dumps(payload))


def test_no_blocker(tmp_path):
    cache_path = tmp_path / "cache.json"
    with mock.patch.object(
        cross_repo_gate,
        "_gather_local_spokes",
        return_value={"spoke1": []},
    ):
        result = check_cross_repo_deps_blocked(
            tmp_path, spokes_key="default", cache_path=cache_path
        )
    assert result == []


def test_single_blocker(tmp_path):
    cache_path = tmp_path / "cache.json"
    spokes_data = {
        "org/foo": [
            {"change": "change1", "depends_on": "org/bar#dependency-x"}
        ]
    }
    result = check_cross_repo_deps_blocked(
        tmp_path, spokes_key="default",
        spokes_data=spokes_data, cache_path=cache_path,
    )
    assert result == ["change1: blocked by org/bar"]


def test_cross_repo_chain(tmp_path):
    cache_path = tmp_path / "cache.json"
    spokes_data = {
        "org/foo": [
            {"change": "A", "depends_on": "org/bar#B"},
            {"change": "B", "depends_on": "org/baz#C"},
        ],
        "org/bar": [
            {"change": "B-dep", "depends_on": "org/baz#C"},
        ],
    }
    result = check_cross_repo_deps_blocked(
        tmp_path, spokes_key="default",
        spokes_data=spokes_data, cache_path=cache_path,
    )
    assert any("A: blocked by org/bar" in r for r in result)
    assert any("B: blocked by org/baz" in r for r in result)
    assert any("B-dep: blocked by org/baz" in r for r in result)
    assert len(result) == 3


def test_cycle_detect(tmp_path):
    cache_path = tmp_path / "cache.json"
    spokes_data = {
        "spoke-A": [{"change": "A", "depends_on": "spoke-B#B"}],
        "spoke-B": [{"change": "B", "depends_on": "spoke-A#A"}],
    }
    result = check_cross_repo_deps_blocked(
        tmp_path, spokes_key="default",
        spokes_data=spokes_data, cache_path=cache_path,
    )
    assert any(
        "A" in msg and "B" in msg for msg in result
    ), f"expected cross-repo chain blockers mentioning A and B, got {result!r}"


def test_cache_hit_skips_recomputation(tmp_path):
    cache_path = tmp_path / "cache.json"
    cached_data = {"blockers": [
        {"change": "from-cache", "spoke": "spoke-x", "depends_on": "spoke-x#y"}
    ]}
    _write_cache(cache_path, "default", cached_data)

    with mock.patch.object(
        cross_repo_gate, "_gather_local_spokes"
    ) as mock_gather:
        result = check_cross_repo_deps_blocked(
            tmp_path, spokes_key="default", cache_path=cache_path
        )
    mock_gather.assert_not_called()
    assert result == ["from-cache: blocked by spoke-x"]