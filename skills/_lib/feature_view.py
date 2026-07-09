"""Feature-level derived view of iteration.json.

Pure derivation — no source-of-truth mutation. The 5 pure step functions
(Steps 1-5) take plain Python data and return plain Python data; the
6th function is the IO orchestrator that reads iteration.json + deps-analysis.json
and writes the computed `feature_view` node back to iteration.json.
"""
from __future__ import annotations

import datetime
import re

from skills._lib import iteration as it_mod


# Synthetic feature name for changes with no parent_feature and no feature- prefix.
# Excluded from edge computation and execution_order waves.
UNGROUPED = "__ungrouped__"

# Mirror iteration._FEATURE_PREFIX_RE so this module is self-contained
# (avoids a private import; iteration.py exports `derive_feature_name`).
_FEATURE_PREFIX_RE = re.compile(r"^(feature-[a-z0-9]+)(-[a-z0-9-]+)?$")


def _is_ungrouped(change_name: str, derived: str) -> bool:
    """Return True if the change ended up in a self-group (no real feature).

    Self-group happens when derive_feature_name returns the change name itself,
    which means no parent_feature field AND no `feature-<name>-<sub>` prefix.
    """
    if derived != change_name:
        return False
    return not _FEATURE_PREFIX_RE.match(change_name)


def group_changes_by_feature(changes: list[dict]) -> dict[str, list[str]]:
    """Group changes by derived feature name.

    Returns a dict keyed by feature name, values are sorted lists of change names.
    The synthetic `__ungrouped__` key buckets changes with no real feature
    affiliation (no parent_feature field AND no `feature-` prefix in the name).
    """
    groups: dict[str, list[str]] = {}
    for ch in changes:
        name = ch["name"]
        parent = ch.get("parent_feature")
        # Replicate iteration.derive_feature_name inline to also know
        # whether the result was a self-group.
        if parent:
            derived = parent
        else:
            m = _FEATURE_PREFIX_RE.match(name)
            derived = m.group(1) if m else name
        if _is_ungrouped(name, derived):
            groups.setdefault(UNGROUPED, []).append(name)
        else:
            groups.setdefault(derived, []).append(name)
    # Sort for deterministic output
    for k in groups:
        groups[k] = sorted(groups[k])
    return dict(sorted(groups.items()))


# Status priority chain for rollup (first match wins).
# in_worktree + review both count as "in flight" for rollup purposes.
_IN_FLIGHT = ("in_worktree", "review")
_PENDING = ("proposed", "planned")


def rollup_status(changes: list[dict]) -> str:
    """Roll up a list of change dicts into a feature status enum.

    Priority chain: blocked > in_progress > ready > done > ungrouped.
    """
    if not changes:
        return "ungrouped"
    statuses = {c.get("status") for c in changes}
    if "blocked_by" in statuses:
        return "blocked"
    if any(s in _IN_FLIGHT for s in statuses):
        return "in_progress"
    if all(s in _PENDING for s in statuses):
        return "ready"
    if statuses == {"archived"}:
        return "done"
    return "in_progress"


def compute_feature_edges(
    deps_analysis: dict, feature_groups: dict
) -> list[tuple[str, str, str]]:
    """Compute feature-level dependency edges from change-level hard deps.

    For each pair (Fa, Fb) with Fa != Fb, count hard change-level edges from
    any change in Fa to any change in Fb. Produce a feature edge iff every
    possible (from_change, to_change) pair is present (all-pairs-hard rule).

    Returns list of (from_feature, to_feature, "hard") tuples.
    The synthetic UNGROUPED feature is excluded from edge computation.

    Note: Under the single-blocker schema (blocker: str | None), a feature
    edge Fa→Fb can only form when |Fb| == 1, since each change provides at
    most one blocker and the all-pairs-hard rule requires |Fa| × |Fb| edges.
    """
    changes_map = deps_analysis.get("changes", {})
    real_groups = {k: v for k, v in feature_groups.items() if k != UNGROUPED}
    features = sorted(real_groups.keys())

    edges: list[tuple[str, str, str]] = []
    for fa in features:
        for fb in features:
            if fa >= fb:  # avoid duplicates (lex order) and self-loops
                continue
            n = 0
            m = 0
            for from_ch in real_groups[fa]:
                info = changes_map.get(from_ch, {})
                blocker = info.get("blocker")
                if blocker in real_groups[fb]:
                    n += 1
                m += 1
            m_total = m * len(real_groups[fb])
            if m_total > 0 and n == m_total:
                edges.append((fa, fb, "hard"))
    return edges


class FeatureCycleError(Exception):
    """Raised when the feature dependency graph contains a cycle."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"feature dependency cycle: {' -> '.join(cycle)}")


def compute_parallel_groups(
    edges: list[tuple[str, str, str]], features: dict
) -> dict[str, int]:
    """Assign each feature to a parallel-group wave index via BFS topo layering.

    `features` is a dict (values ignored; keys are the feature names).
    Returns dict[feature_name, wave_index]. Wave 0 = no incoming edges.
    Raises FeatureCycleError if a cycle is detected.
    """
    if not features:
        return {}
    in_degree: dict[str, int] = {f: 0 for f in features}
    successors: dict[str, list[str]] = {f: [] for f in features}
    for fa, fb, _kind in edges:
        if fa in features and fb in features:
            in_degree[fb] = in_degree.get(fb, 0) + 1
            successors[fa].append(fb)

    wave = 0
    groups: dict[str, int] = {}
    remaining = set(features.keys())
    while remaining:
        current_wave = sorted(f for f in remaining if in_degree.get(f, 0) == 0)
        if not current_wave:
            raise FeatureCycleError(sorted(remaining))
        for f in current_wave:
            groups[f] = wave
            remaining.discard(f)
            for succ in successors.get(f, []):
                if succ in remaining:
                    in_degree[succ] -= 1
        wave += 1
    return groups