"""Wave compute performance gate (MUST: ≤100ms for 5 change × 50 task)."""
from __future__ import annotations
import time

from _lib.wave_compute import compute_waves


def test_compute_waves_perf_5_changes_50_tasks():
    """5 changes × 10 tasks each → ~40 block edges → must finish < 100ms."""
    blocks = []
    for c in range(4):
        for t in range(10):
            blocks.append({"from": f"c{c}_t{t}", "to": f"c{c + 1}_t{t}"})
    deps = {"blocks": blocks}
    t0 = time.perf_counter()
    out = compute_waves(deps)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 100, f"compute_waves took {elapsed_ms:.1f}ms (limit 100ms)"
    assert len(out) == 5