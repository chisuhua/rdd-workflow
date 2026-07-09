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