"""Cross-repo dependencies orchestration (Step 6 of Hub-and-Spoke federation).

Parses multiple Spoke iteration.json files, builds a unified dependency
graph, detects cycles (DFS), produces wave-based execution order (Kahn
topological sort), resolves ETAs via 3-level fallback, and emits Mermaid.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

PathLike = Union[str, Path]


def parse_spoke_iteration(data: Dict[str, Any], spoke_key: str) -> List[Dict[str, str]]:
    """Extract cross_repo_dependencies from one Spoke's iteration.json."""
    deps = []
    changes = data.get("changes", {})
    if isinstance(changes, dict):
        items = list(changes.items())
    else:
        items = [(c.get("name", ""), c) for c in changes]
    for name, change in items:
        for dep in change.get("cross_repo_dependencies", []) or []:
            deps.append({"change": name, "depends_on": dep})
    return deps


def build_cross_repo_graph(spokes_data: Dict[str, List[Dict[str, str]]]) -> Dict[str, List[str]]:
    """Build unified graph: spoke_key → list of 'org/repo#change' deps."""
    graph = {}
    for spoke_key, deps in spokes_data.items():
        graph[spoke_key] = []
        for entry in deps:
            graph[spoke_key].append(entry["depends_on"])
    return graph


def detect_cycle(graph: Dict[str, List[str]]) -> List[str]:
    """DFS-based cycle detection. Returns list of cycle members (empty if no cycle)."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    cycle = []

    def dfs(node, path):
        if color.get(node) == GRAY:
            cycle.extend(path[path.index(node):])
            return True
        if color.get(node) == BLACK:
            return False
        color[node] = GRAY
        path.append(node)
        for nxt in graph.get(node, []):
            if dfs(nxt, path):
                return True
        path.pop()
        color[node] = BLACK
        return False

    for n in list(graph.keys()):
        if color[n] == WHITE:
            dfs(n, [])
    return list(set(cycle))


def kahn_topological_sort(graph: Dict[str, List[str]]) -> List[List[str]]:
    """Kahn's algorithm: returns waves (each wave = independent nodes)."""
    # Initialize in_degree for ALL nodes first
    in_degree = {n: 0 for n in graph}
    reverse = {}
    for src, deps in graph.items():
        for d in deps:
            reverse.setdefault(d, []).append(src)
    # Count incoming edges: src depends on d, so in_degree[src]++
    for src, deps in graph.items():
        for d in deps:
            in_degree[src] += 1

    waves = []
    visited = set()
    # Start with nodes that have no incoming edges (in_degree == 0)
    remaining = {n for n in graph if in_degree[n] == 0}

    while remaining:
        waves.append(sorted(remaining))
        visited.update(remaining)
        next_wave = set()
        for n in remaining:
            for src in reverse.get(n, []):
                if src not in visited:
                    in_degree[src] -= 1
                    if in_degree[src] == 0:
                        next_wave.add(src)
        remaining = next_wave

    return waves


def eta_fallback_chain(change: Dict[str, Any]) -> int:
    """3-level ETA fallback: lv1 tasks.md → lv2 frontmatter → lv3 manual."""
    # LV1: tasks.md checkbox count
    tasks_path = change.get("tasks_path")
    if tasks_path and Path(tasks_path).exists():
        content = Path(tasks_path).read_text()
        count = len(re.findall(r"^- \[ \]", content, re.MULTILINE))
        if count > 0:
            return count
    # LV2: frontmatter eta
    if "eta" in change:
        return int(change["eta"])
    # LV3: manual
    if "manual_eta" in change:
        return int(change["manual_eta"])
    return 1


def generate_mermaid(graph: Dict[str, List[str]], etas: Dict[str, int]) -> str:
    """Generate Mermaid flowchart with ETA annotations."""
    lines = ["graph TD"]
    for node, eta in sorted(etas.items()):
        safe_id = node.replace("/", "_").replace("#", "_")
        lines.append(f"    {safe_id}[\"{node} ({eta}d)\"]")
    for src, deps in sorted(graph.items()):
        safe_src = src.replace("/", "_").replace("#", "_")
        for d in deps:
            safe_d = d.replace("/", "_").replace("#", "_")
            lines.append(f"    {safe_src} --> {safe_d}")
    return "\n".join(lines) + "\n"
