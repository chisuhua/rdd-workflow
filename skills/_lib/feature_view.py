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
            in_degree[fb] += 1
            successors[fa].append(fb)

    wave = 0
    groups: dict[str, int] = {}
    remaining = set(features.keys())
    while remaining:
        current_wave = sorted(f for f in remaining if in_degree[f] == 0)
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


def render_mermaid(
    features: dict,
    edges: list[tuple[str, str, str]],
    conflicts: list[tuple[str, str]],
    parallel_groups: dict[str, int],
) -> str:
    """Render a Mermaid flowchart at feature granularity.

    `features` is a dict[feature_name, {status, archived_count, change_count, parallel_group}].
    `parallel_groups` is accepted for API consistency with the orchestrator (Step 6)
    but the wave index is sourced from `info['parallel_group']` to ensure the rendered
    label always reflects what is persisted in the feature_view node.
    Returns the Mermaid source as a string.
    """
    lines = ["flowchart LR"]
    for name, info in sorted(features.items()):
        label = (
            f"{name}<br/>"
            f"{info['status']} · "
            f"{info['archived_count']}/{info['change_count']} · "
            f"wave {info['parallel_group']}"
        )
        safe = label.replace('"', "&quot;")
        lines.append(f'  {name}["{safe}"]')
    for fa, fb, _ in edges:
        lines.append(f"  {fa} --> {fb}")
    for fa, fb in conflicts:
        lines.append(f"  {fa} -.->|冲突| {fb}")
    return "\n".join(lines)


class NoIterationError(Exception):
    """Raised when iteration.json is missing — feature view cannot be computed."""


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _compute_rollup_basis(change_names, all_changes):
    bases = set()
    for n in change_names:
        ch = all_changes.get(n, {})
        if ch.get("parent_feature"):
            bases.add("explicit")
        else:
            bases.add("name_prefix")
    if bases == {"explicit"}:
        return "explicit"
    if bases == {"name_prefix"}:
        return "name_prefix"
    return "mixed"


def _enrich_changes_with_deps_status(all_changes, deps_analysis):
    """Return {name: enriched_change} with `status` overridden from deps when applicable.

    Each iteration change keeps its iteration status by default. If the deps
    analysis marks the change with `status: "blocked_by"`, the enriched copy
    has `status: "blocked_by"` so that `rollup_status` correctly classifies
    the parent feature as `blocked`. Original `all_changes` dict is NOT mutated;
    saves back to iteration.json leave iteration statuses untouched.
    """
    deps_changes = deps_analysis.get("changes", {})
    enriched = {}
    for name, ch in all_changes.items():
        ch_copy = dict(ch)
        dep = deps_changes.get(name, {})
        if dep.get("status") == "blocked_by":
            ch_copy["status"] = "blocked_by"
        enriched[name] = ch_copy
    return enriched


def _attach_conflicts(features, deps_analysis):
    changes_map = deps_analysis.get("changes", {})
    feature_to_changes = {f: info["change_names"] for f, info in features.items()}
    features_list = sorted(feature_to_changes.keys())
    for i, fa in enumerate(features_list):
        if fa == UNGROUPED:
            continue
        for fb in features_list[i + 1:]:
            if fb == UNGROUPED:
                continue
            if fb in features[fa]["conflicts_with"]:
                continue
            fa_set = set(feature_to_changes[fa])
            fb_set = set(feature_to_changes[fb])
            for ch_name, ch_info in changes_map.items():
                if ch_name in fa_set:
                    for c in ch_info.get("conflicts", []):
                        if c in fb_set:
                            features[fa]["conflicts_with"].append(fb)
                            features[fb]["conflicts_with"].append(fa)
                            break
                    if fb in features[fa]["conflicts_with"]:
                        break
                elif ch_name in fb_set:
                    for c in ch_info.get("conflicts", []):
                        if c in fa_set:
                            features[fa]["conflicts_with"].append(fb)
                            features[fb]["conflicts_with"].append(fa)
                            break
                    if fb in features[fa]["conflicts_with"]:
                        break
    return features


def _waves_to_order(parallel_groups):
    if not parallel_groups:
        return []
    max_wave = max(parallel_groups.values())
    waves = [[] for _ in range(max_wave + 1)]
    for f, w in sorted(parallel_groups.items()):
        waves[w].append(f)
    return waves


def update_iteration_feature_view(project_root):
    data = it_mod.load(project_root)
    if not data or not data.get("changes"):
        raise NoIterationError(
            "iteration.json missing — run `skill_use('guide-plan')` at least once first."
        )
    all_changes = {c["name"]: c for c in data.get("changes", [])}
    changes_list = list(all_changes.values())

    from skills._lib import deps_output

    deps = deps_output.load_analysis(project_root) or {}

    groups = group_changes_by_feature(changes_list)

    features = {}
    enriched_changes = _enrich_changes_with_deps_status(all_changes, deps)
    for name, ch_names in groups.items():
        ch_records = [enriched_changes[n] for n in ch_names]
        features[name] = {
            "name": name,
            "status": rollup_status(ch_records),
            "change_names": ch_names,
            "change_count": len(ch_names),
            "archived_count": sum(1 for c in ch_records if c.get("status") == "archived"),
            "rollup_basis": _compute_rollup_basis(ch_names, all_changes),
            "depends_on": [],
            "blocks": [],
            "parallel_group": 0,
            "conflicts_with": [],
        }

    edges = compute_feature_edges(deps, groups)
    cycle_warning = False
    cycle_members = []
    try:
        pg = compute_parallel_groups(edges, features)
    except FeatureCycleError as exc:
        cycle_warning = True
        cycle_members = exc.cycle
        pg = {f: 0 for f in features}
    for f in features:
        features[f]["parallel_group"] = pg.get(f, 0)
    for fa, fb, _ in edges:
        if fa in features and fb in features:
            features[fa]["blocks"].append(fb)
            features[fb]["depends_on"].append(fa)
    features = _attach_conflicts(features, deps)

    execution_order = _waves_to_order(pg)

    feature_view_node = {
        "schema_version": 1,
        "updated_at": _now_iso(),
        "features": features,
        "execution_order": execution_order,
    }
    if cycle_warning:
        feature_view_node["__cycle_warning__"] = True
        feature_view_node["__cycle_members__"] = cycle_members

    data["feature_view"] = feature_view_node
    it_mod.save(project_root, data)
    return len(features)