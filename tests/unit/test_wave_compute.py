"""Wave computation from deps-analysis.json (per phase-2-general-20260829063801)."""
from __future__ import annotations
import pytest

from _lib.wave_compute import compute_waves, WaveCycleError


def _deps(pairs):
    """Build deps_data with `blocks` field: [from, to] pairs."""
    blocks = [{"from": a, "to": b} for a, b in pairs]
    return {"blocks": blocks}


def test_linear_chain_3_waves():
    """A blocks B, B blocks C → waves = [[A], [B], [C]]."""
    out = compute_waves(_deps([("a", "b"), ("b", "c")]))
    assert out == [["a"], ["b"], ["c"]]


def test_diamond_2_waves():
    """A blocks B,C; B,C block D → waves = [[A], [B,C], [D]]."""
    out = compute_waves(_deps([("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]))
    assert out == [["a"], ["b", "c"], ["d"]]


def test_isolated_changes_one_wave():
    """A blocks B → only A in wave 0 (B in wave 1)."""
    out = compute_waves(_deps([("a", "b")]))
    assert out[0] == ["a"]


def test_cyclic_blocks_raises():
    """A→B→A cycle → WaveCycleError."""
    with pytest.raises(WaveCycleError):
        compute_waves(_deps([("a", "b"), ("b", "a")]))


def test_empty_blocks_returns_empty():
    assert compute_waves({"blocks": []}) == []