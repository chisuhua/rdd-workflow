"""Cross-repo dependencies gate (ADR-0018 escalation pattern).

Wraps `kahn_topological_sort` from skills._lib.cross_repo_deps with a
24h TTL cache (cross_repo_deps_cache.py). Outputs a list of blocker
descriptions consumed by plan_done_gate.sh's STRICT_DEPS_GATE check.

This module is intentionally side-effect-free: it does NOT read env
vars. Env-var handling (STRICT_DEPS_GATE / SKIP_DEPS_GATE) lives in
plan_done_gate.sh per ADR-0018 pattern.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

PathLike = Union[str, Path]

CACHE_FILENAME = ".cross-repo-deps-cache.json"


def _default_cache_path(project_root: PathLike) -> Path:
    return Path(project_root) / ".rddf" / "state" / CACHE_FILENAME


def _extract_blockers_from_spokes(spokes_data: Dict[str, List[Dict[str, str]]]) -> List[Dict[str, str]]:
    blockers: List[Dict[str, str]] = []
    for spoke_key, deps in spokes_data.items():
        for entry in deps:
            change = entry.get("change", "")
            depends_on = entry.get("depends_on", "")
            if not change or not depends_on:
                continue
            blocking_spoke = depends_on.split("#", 1)[0] if "#" in depends_on else spoke_key
            blockers.append({
                "change": change,
                "spoke": blocking_spoke,
                "depends_on": depends_on,
                "host_spoke": spoke_key,
            })
    return blockers


def _detect_cycle_message(graph: Dict[str, List[str]]) -> Optional[str]:
    try:
        from skills._lib.cross_repo_deps import detect_cycle
    except ImportError:
        return None
    cycle = detect_cycle(graph)
    if cycle:
        return "cycle detected: " + " -> ".join(cycle + [cycle[0]])
    return None


def check_cross_repo_deps_blocked(
    project_root: PathLike,
    spokes_key: str = "default",
    spokes_data: Optional[Dict[str, List[Dict[str, str]]]] = None,
    cache_path: Optional[PathLike] = None,
) -> List[str]:
    """Return human-readable blocker descriptions.

    Args:
        project_root: repository root (used to resolve cache file).
        spokes_key: identifier for the spokes slice in the cache.
        spokes_data: optional override that bypasses I/O for tests.
        cache_path: override cache file location.

    Returns:
        List of strings like ``"<change>: blocked by <spoke>"`` or
        ``"⚠️ cycle detected: A -> B -> A"``. Empty list means no blocker.
    """
    from skills._lib.cross_repo_deps_cache import (
        is_cache_valid, load_cache, save_cache,
    )

    cache_path = Path(cache_path) if cache_path else _default_cache_path(project_root)

    if spokes_data is None and is_cache_valid(cache_path, spokes_key):
        cached = load_cache(cache_path, spokes_key) or {}
        cached_blockers = cached.get("blockers", [])
        return [_format_blocker(b) for b in cached_blockers]

    if spokes_data is None:
        spokes_data = _gather_local_spokes(project_root)

    blockers = _extract_blockers_from_spokes(spokes_data)

    cycle_msg: Optional[str] = None
    try:
        from skills._lib.cross_repo_deps import build_cross_repo_graph
        graph = build_cross_repo_graph(spokes_data)
        cycle_msg = _detect_cycle_message(graph)
    except ImportError:
        pass

    save_cache(cache_path, spokes_key, {"blockers": blockers})

    messages = [_format_blocker(b) for b in blockers]
    if cycle_msg:
        messages.append(f"⚠️ {cycle_msg}")
    return messages


def _format_blocker(blocker: Dict[str, str]) -> str:
    change = blocker.get("change", "?")
    spoke = blocker.get("spoke", "?")
    return f"{change}: blocked by {spoke}"


def _gather_local_spokes(project_root: PathLike) -> Dict[str, List[Dict[str, str]]]:
    from skills._lib.cross_repo_deps import parse_spoke_iteration

    root = Path(project_root)
    candidates = []
    for rel in (".rddf/state/iteration.json",):
        path = root / rel
        if path.is_file():
            candidates.append(path)

    spokes_data: Dict[str, List[Dict[str, str]]] = {}
    for path in candidates:
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        spokes_data[path.stem] = parse_spoke_iteration(data, spoke_key=path.stem)
    return spokes_data


import json  # noqa: E402  (after function defs to keep module top-readable)