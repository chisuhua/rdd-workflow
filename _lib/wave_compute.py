"""Wave DAG computation from deps-analysis.json.

Per phase-2-general-20260829063801:
- compute_waves(deps_data) → list[list[str]]
  - wave 0: nodes with no inbound edges (can start immediately)
  - wave N+1: nodes whose ALL inbound neighbors are in waves 0..N
  - raises WaveCycleError if a cycle is detected
"""
from __future__ import annotations
import heapq
from typing import Dict, List, Set


class WaveCycleError(Exception):
    """Raised when deps form a cycle and wave computation cannot proceed."""


def _index_blocks(deps_data):
    """Return {node: set(downstream nodes it blocks)} from deps_data.blocks."""
    out = {}
    for entry in deps_data.get("blocks", []):
        src = entry["from"]
        dst = entry["to"]
        out.setdefault(src, set()).add(dst)
        out.setdefault(dst, set())
    return out


def _inbound(blocks):
    """Reverse map: {node: set(upstream nodes that block it)}."""
    out = {n: set() for n in blocks}
    for src, dsts in blocks.items():
        for dst in dsts:
            out[dst].add(src)
    return out


def compute_waves(deps_data):
    """Kahn-style level-sorted wave partition. Ties broken by node name
    for deterministic output (tests can assert exact waves)."""
    blocks = _index_blocks(deps_data)
    if not blocks:
        return []

    inbound = _inbound(blocks)
    remaining_in = {n: set(s) for n, s in inbound.items()}
    waves = []
    processed = set()

    ready = sorted([n for n, s in remaining_in.items() if not s])
    while ready:
        waves.append(ready)
        for n in ready:
            processed.add(n)
        next_ready = []
        for n in ready:
            for downstream in blocks.get(n, set()):
                remaining_in[downstream].discard(n)
                if downstream not in processed and not remaining_in[downstream]:
                    next_ready.append(downstream)
        ready = sorted(set(next_ready) - processed)

    if processed != set(blocks):
        unprocessed = set(blocks) - processed
        raise WaveCycleError(f"Cycle detected; unprocessed: {sorted(unprocessed)}")
    return waves