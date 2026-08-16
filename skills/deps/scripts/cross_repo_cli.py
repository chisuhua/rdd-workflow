#!/usr/bin/env python3
"""rddf deps cross-repo: orchestrate cross-repo dependencies.

Usage:
  rddf deps cross-repo --spokes <org/repo1,org/repo2> [--output-format text|json|mermaid]
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to path (script is at skills/deps/scripts/, go up 3 levels to skills/, then 1 more to project root)
# The project root contains 'skills/' which has the _lib package
_script_dir = os.path.dirname(os.path.abspath(__file__))
# skills/deps/scripts -> skills/deps -> skills -> project root
_skills_dir = os.path.dirname(os.path.dirname(_script_dir))  # skills/
_project_root = os.path.dirname(_skills_dir)  # project root

# Insert project root so 'import skills._lib.X' works
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Force re-setup of skills._lib to point to worktree's skills/_lib/
import types
_worktree_lib = os.path.join(_project_root, "skills", "_lib")
if "skills._lib" in sys.modules:
    _mod = sys.modules["skills._lib"]
    _mod.__path__ = [_worktree_lib]
else:
    _mod = types.ModuleType("skills._lib")
    _mod.__path__ = [_worktree_lib]
    _mod.__file__ = os.path.join(_worktree_lib, "__init__.py")
    sys.modules["skills._lib"] = _mod

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
    parser.add_argument("--cache-file", default=".rddf/state/.cross-repo-deps-cache.json")
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
