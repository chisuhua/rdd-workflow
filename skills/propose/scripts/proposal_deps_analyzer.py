"""Proposal-level dependency and feature metadata analyzer.

Parses **依赖**: and **特性**: metadata from proposal content,
and provides topological sorting for dependency-ordered execution.
"""
import re
from typing import Dict, List, Any


def parse_proposal_metadata(content: str) -> Dict[str, Any]:
    """Parse **依赖**: and **特性**: metadata from proposal content.

    Returns a dict with:
    - deps: list of explicit dependency names
    - feature: optional feature group name
    - auto_detected: list of auto-detected improvement references
    """
    result: Dict[str, Any] = {
        "deps": [],
        "feature": None,
        "auto_detected": []
    }

    deps_match = re.search(r'\*\*依赖\*\*:\s*\[([^\]]+)\]', content)
    if deps_match:
        deps_str = deps_match.group(1)
        result["deps"] = [d.strip() for d in deps_str.split(',')]

    feature_match = re.search(r'\*\*特性\*\*:\s*(\S+)', content)
    if feature_match:
        result["feature"] = feature_match.group(1)

    auto_refs = re.findall(r'.rddf/improvements/([a-z0-9-]+)\.md', content)
    result["auto_detected"] = list(set(auto_refs))

    return result


def topological_sort(proposals: List[Dict[str, Any]]) -> List[str]:
    """Sort proposals by dependency order using topological sort.

    Each proposal dict must have 'name' and optional 'deps' keys.
    Returns a list of names in dependency-first order.
    """
    sorted_names: List[str] = []
    visited: set = set()

    def visit(name: str, deps_map: Dict[str, List[str]]) -> None:
        if name in visited:
            return
        visited.add(name)
        for dep in deps_map.get(name, []):
            visit(dep, deps_map)
        sorted_names.append(name)

    deps_map = {p["name"]: p.get("deps", []) for p in proposals}
    for p in proposals:
        visit(p["name"], deps_map)

    return sorted_names
