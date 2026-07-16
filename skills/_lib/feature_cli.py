"""Feature command-line interface functions.

Extracted from skills/feature.md L30-L182 — 4 subcommand renderers.
Each function loads iteration.json + deps-analysis.json + computes feature_view,
then prints the specific view.

Public functions:
    render_summary(project_root)     — table of all features
    render_graph(project_root)       — Mermaid flowchart
    render_status(project_root, target_name)  — one feature detail
    render_order(project_root)       — wave-grouped execution order
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _load_feature_view(project_root: str) -> dict:
    """Common loading + feature_view computation for all 4 subcommands."""
    try:
        sys.path.insert(0, project_root)
        from skills._lib import feature_view as fv  # noqa: F811
    except ImportError as e:
        print(f"❌ feature_view module unavailable: {e}", file=sys.stderr)
        sys.exit(2)

    iteration_path = Path(project_root) / ".rddf" / "state" / "iteration.json"
    if not iteration_path.exists():
        print("❌ iteration.json not found (run guide-plan first)", file=sys.stderr)
        sys.exit(1)

    try:
        fv.update_iteration_feature_view(project_root)
    except (fv.NoIterationError, fv.FileLockedError) as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    return json.loads(iteration_path.read_text())


def render_summary(project_root: str) -> None:
    """Print summary table of features (subcommand: summary)."""
    data = _load_feature_view(project_root)
    features = data["feature_view"]["features"]
    if not features:
        print("(no features — set parent_feature in proposal.md or use feature-<name>-<part> naming)")
        return

    print("| Feature | Status | Changes | Progress | Wave | Blocks | Blocked by |")
    print("|---------|--------|---------|----------|------|--------|------------|")
    for name in sorted(features):
        info = features[name]
        if name == "__ungrouped__":
            print(f"| **{name}** | ⚪ ungrouped | {info['change_count']} | — | — | — | — |")
            continue
        status_icon = {
            "blocked": "🔴", "in_progress": "🟡", "ready": "🟢", "done": "✅"
        }.get(info["status"], "⚪")
        blocks = ", ".join(info["blocks"]) or "—"
        blocked_by = ", ".join(info["depends_on"]) or "—"
        print(f"| {name} | {status_icon} {info['status']} | {info['change_count']} | "
              f"{info['archived_count']}/{info['change_count']} | {info['parallel_group']} | "
              f"{blocks} | {blocked_by} |")


def render_graph(project_root: str) -> None:
    """Print Mermaid flowchart (subcommand: graph)."""
    data = _load_feature_view(project_root)
    fv_node = data["feature_view"]
    features = fv_node["features"]
    edges = []
    conflicts = []
    seen = set()
    for name, info in features.items():
        for b in info.get("blocks", []):
            e = (name, b, "hard")
            if e not in seen:
                edges.append(e)
                seen.add(e)
        for c in info.get("conflicts_with", []):
            pair = tuple(sorted([name, c]))
            if pair not in seen:
                conflicts.append(pair)
                seen.add(pair)
    pg = {n: info["parallel_group"] for n, info in features.items()}

    sys.path.insert(0, project_root)
    from skills._lib import feature_view as fv  # noqa: F811
    mermaid = fv.render_mermaid(features, edges, conflicts, pg)
    print("```mermaid")
    print(mermaid)
    print("```")
    if fv_node.get("__cycle_warning__"):
        print(f"\n⚠️ Cycle detected: {fv_node.get('__cycle_members__')}")


def render_status(project_root: str, target_name: str) -> None:
    """Print details for one feature (subcommand: status <name>)."""
    data = _load_feature_view(project_root)
    info = data["feature_view"]["features"].get(target_name)
    if info is None:
        names = sorted(data["feature_view"]["features"].keys())
        print(f"❌ feature '{target_name}' not found. Known: {names}", file=sys.stderr)
        sys.exit(1)

    print(f"## {target_name}\n")
    print(f"- **Status:** {info['status']}")
    print(f"- **Rollup basis:** {info['rollup_basis']}")
    print(f"- **Change count:** {info['change_count']} (archived: {info['archived_count']})")
    print(f"- **Wave:** {info['parallel_group']}")
    print(f"- **Blocks:** {', '.join(info['blocks']) or '—'}")
    print(f"- **Blocked by:** {', '.join(info['depends_on']) or '—'}\n")
    print("| Change | Status | Blocker | Phase | Category |")
    print("|--------|--------|---------|-------|----------|")
    all_changes = {c["name"]: c for c in data.get("changes", [])}
    for n in info["change_names"]:
        c = all_changes.get(n, {})
        print(f"| {n} | {c.get('status', '—')} | {c.get('blocker') or '—'} | "
              f"{c.get('phase', '—')} | {c.get('category', '—')} |")


def render_order(project_root: str) -> None:
    """Print recommended wave execution order (subcommand: order)."""
    data = _load_feature_view(project_root)
    order = data["feature_view"].get("execution_order", [])
    features = data["feature_view"]["features"]
    if not order:
        print("(no features)")
        return

    print("## Recommended execution order\n")
    for i, wave in enumerate(order):
        if not wave:
            continue
        print(f"- **Wave {i}** (run in parallel):")
        for f in sorted(wave):
            info = features.get(f, {})
            print(f"  - {f} ({info.get('status', '—')} "
                  f"· {info.get('archived_count', 0)}/{info.get('change_count', 0)})")
