#!/usr/bin/env python3
"""rddf deps cross-repo: orchestrate cross-repo dependencies.

Usage:
  rddf deps cross-repo --spokes <org/repo1,org/repo2> [--output-format text|json|mermaid]
"""
import argparse
import json
import sys
from pathlib import Path

# --- import bootstrap ONLY (probe anchor + sys.path) ---
# skills/deps/scripts/<this file> -> skills/deps/scripts -> skills/deps -> skills -> <repo root>
_SCRIPT_ROOT = Path(__file__).resolve().parents[3]
if str(_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_ROOT))

# --- project root resolution (single authority) ---
# The resolver is the only thing allowed to answer "where is the project root";
# _SCRIPT_ROOT merely anchors its git probe so the answer does not depend on
# the caller's working directory.
from skills._lib._python_resolve_project_root import (  # noqa: E402
    resolve_project_root,
)

PROJECT_ROOT = Path(resolve_project_root(start_dir=_SCRIPT_ROOT))

from skills._lib.cross_repo_deps import (
    parse_spoke_iteration, build_cross_repo_graph,
    detect_cycle, kahn_topological_sort, eta_fallback_chain,
    generate_mermaid,
)
from skills._lib.cross_repo_deps_cache import load_cache, save_cache, is_cache_valid



def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spokes", required=True, help="Comma-separated org/repo list")
    parser.add_argument("--output-format", choices=["text", "json", "mermaid"], default="text")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument(
        "--cache-file",
        default=str(PROJECT_ROOT / ".rddf" / "state" / ".cross-repo-deps-cache.json"),
        help="Cache path (default: <project root>/.rddf/state/.cross-repo-deps-cache.json)",
    )
    args = parser.parse_args()

    spokes = args.spokes.split(",")
    spokes_data = {}
    cache_path = Path(args.cache_file)

    if not args.force_refresh and is_cache_valid(cache_path, args.spokes):
        cached = load_cache(cache_path, args.spokes)
        if cached:
            spokes_data = cached

    if not spokes_data:
        # In real impl: load each spoke's iteration.json via gh API
        # For now, stub with empty data per spoke
        spokes_data = {s: [] for s in spokes}

    graph = build_cross_repo_graph(spokes_data)
    cycle = detect_cycle(graph)
    waves = kahn_topological_sort(graph)
    etas = {n: eta_fallback_chain({"manual_eta": 1}) for n in graph}

    if args.output_format == "json":
        output = json.dumps({
            "graph": graph, "cycle": cycle, "waves": waves, "etas": etas
        }, indent=2)
    elif args.output_format == "mermaid":
        output = generate_mermaid(graph, etas)
    else:
        output = f"Waves: {waves}\nCycle: {cycle}\nGraph: {graph}"

    print(output)
    save_cache(cache_path, args.spokes, spokes_data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
