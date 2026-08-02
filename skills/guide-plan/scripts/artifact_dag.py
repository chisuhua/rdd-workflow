"""skills/guide-plan/scripts/artifact_dag.py — openspec artifact DAG driver.

Consumes `openspec status --change <name> --json` output and computes:
  - transitive closure of applyRequires (root + requires edges recursive)
  - topological order respecting requires edges
  - ready/blocked classification per artifact
  - OPENSPEC_DAG_AVAILABLE flag (set to true when CLI >= 1.7.0)

v1.7.0 changelog notes that applyRequires must be a transitive closure
(pre-1.7.0 only checked root nodes — bug). This module implements the
correct recursive behavior.
"""
from __future__ import annotations

import json
import re
import subprocess
from typing import Optional


# Artifact order used for fallback when OPENSPEC_DAG_AVAILABLE=false
FALLBACK_ARTIFACT_ORDER = ["proposal", "design", "tasks", "specs"]


def parse_version(version_str: str) -> tuple[int, int, int]:
    """Parse '1.7.0' or 'v1.7.0' into (1, 7, 0). Returns (0, 0, 0) on failure."""
    if not version_str:
        return (0, 0, 0)
    m = re.search(r"v?(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def is_dag_available(cli_version: str) -> bool:
    """True when openspec CLI >= 1.7.0 (artifacts[].requires exists in status --json)."""
    major, minor, patch = parse_version(cli_version)
    return (major, minor, patch) >= (1, 7, 0)


def compute_required_artifacts(status_json: dict) -> list[str]:
    """Compute transitive closure of applyRequires from status JSON.

    Iteratively expands requires edges until fixpoint. Returns a list of
    artifact IDs in topological-respecting order (best-effort; full
    topological sort is `topological_order()`).

    v1.7.0+ status --json format:
      {
        "artifacts": [
          {"id": "design", "requires": ["proposal"], "ready": true},
          ...
        ],
        "applyRequires": ["design", "tasks"]
      }

    Pre-1.7.0 (root-only) would only have applyRequires as a flat list with
    no transitive closure. This function computes the closure.
    """
    artifacts = {a["id"]: a for a in status_json.get("artifacts", [])}
    closure: set[str] = set(status_json.get("applyRequires", []))

    changed = True
    while changed:
        changed = False
        new_items = set()
        for art_id in closure:
            art = artifacts.get(art_id, {})
            for req in art.get("requires", []):
                if req not in closure:
                    new_items.add(req)
                    changed = True
        closure |= new_items

    return sorted(closure)


def topological_order(closure: list[str], artifacts: dict[str, dict]) -> list[str]:
    """Kahn's algorithm: topological order respecting requires edges."""
    in_degree: dict[str, int] = {a: 0 for a in closure}
    graph: dict[str, list[str]] = {a: [] for a in closure}

    for art_id in closure:
        requires = artifacts.get(art_id, {}).get("requires", [])
        for req in requires:
            if req in closure:
                graph[req].append(art_id)
                in_degree[art_id] += 1

    queue = [a for a in closure if in_degree[a] == 0]
    order: list[str] = []
    while queue:
        queue.sort()  # deterministic order
        node = queue.pop(0)
        order.append(node)
        for succ in graph[node]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    return order


def classify_ready_blocked(closure: list[str], artifacts: dict[str, dict]) -> dict[str, list[str]]:
    """Classify closure into ready vs blocked.

    An artifact is ready if it has explicit ready=True (or status == done),
    or has no unmet requirements. Otherwise it is blocked.
    """
    ready: list[str] = []
    blocked: list[str] = []

    for art_id in closure:
        art = artifacts.get(art_id, {})
        is_done = art.get("status") == "done"
        explicit_ready = art.get("ready", False) or is_done

        requires = art.get("requires", [])
        unmet = [r for r in requires if r not in closure]

        if explicit_ready:
            ready.append(art_id)
        elif unmet:
            blocked.append(art_id)
        elif requires and not is_done:
            blocked.append(art_id)
        else:
            ready.append(art_id)

    return {"ready": sorted(ready), "blocked": sorted(blocked)}


def get_artifact_status(project_root: str, change_name: str) -> Optional[dict]:
    """Run `openspec status --change <name> --json` and parse. None if CLI fails."""
    try:
        result = subprocess.run(
            ["openspec", "status", "--change", change_name, "--json"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        return None


def fill_order_from_dag(project_root: str, change_name: str) -> list[str]:
    """Compute fill order for a change. Uses DAG when available; fallback otherwise.

    Returns list of artifact IDs to fill (e.g., ['proposal', 'design', 'tasks', 'specs']).
    """
    cli_version = os.environ.get("OPENSPEC_CLI_VERSION", "")
    if not cli_version:
        # Probe CLI version
        try:
            result = subprocess.run(
                ["openspec", "--version"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            cli_version = (result.stdout or "").strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            cli_version = ""

    if not is_dag_available(cli_version):
        return FALLBACK_ARTIFACT_ORDER

    status = get_artifact_status(project_root, change_name)
    if not status:
        return FALLBACK_ARTIFACT_ORDER

    closure = compute_required_artifacts(status)
    artifacts = {a["id"]: a for a in status.get("artifacts", [])}
    return topological_order(closure, artifacts)


import os  # placed here to avoid top-of-file import reordering warnings


if __name__ == "__main__":
    import os
    import sys

    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    change_name = os.environ.get("CHANGE_NAME", "")
    if not change_name:
        print("ERROR: CHANGE_NAME not set", file=sys.stderr)
        sys.exit(2)

    order = fill_order_from_dag(project_root, change_name)
    for art in order:
        print(art)