"""DependencyScheduler — build dependency graphs, topological sort (Kahn), gate execution.

Used by guide-plan / guide-ship to sequence OpenSpec changes. A change can only
execute when every change it depends on is in the `completed` set.

Graph representation
-------------------
``build_dependency_graph`` returns ``Dict[str, List[str]]`` where the key is the
change name and the value is the list of dependency names it must wait for.

Algorithm
---------
``topological_sort`` implements Kahn's algorithm: nodes with in-degree zero are
emitted, then their outgoing edges are removed. If any nodes remain at the end,
the graph contains a cycle and ``ValueError`` is raised.
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Iterable, List, Set


class DependencyScheduler:
    """Build, sort, and query a directed dependency graph of named changes."""

    # ------------------------------------------------------------------ build

    def build_dependency_graph(self, changes: List[Dict]) -> Dict[str, List[str]]:
        """Convert a list of change dicts into an adjacency map.

        Each change dict must carry ``name`` (str) and ``dependencies`` (iterable
        of str). Missing keys are tolerated with sensible defaults so callers can
        pass partial records from scanners without crashing the planner.

        Returns
        -------
        dict
            ``{change_name: [dep_name, ...]}``. Every change name appears as a
            key, even if it has no dependencies.
        """
        graph: Dict[str, List[str]] = {}
        for change in changes:
            name = change["name"]
            deps = list(change.get("dependencies") or [])
            graph[name] = deps
        self._graph_cache = graph
        return graph

    # --------------------------------------------------------------- topo sort

    def topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """Return a topological ordering using Kahn's algorithm.

        Determinism: when multiple nodes have in-degree zero, they are emitted
        in the order they first appear as keys in ``graph`` (Python 3.7+ dict
        insertion order is preserved).

        Raises
        ------
        ValueError
            If ``graph`` contains a cycle. The error message lists the nodes
            that could not be resolved so callers can surface it to the user.
        """
        # In-degree counts only over edges whose target is actually in the graph;
        # dangling references are ignored on purpose so the planner does not
        # crash when a scanner emits an unknown dependency name.
        in_degree: Dict[str, int] = {node: 0 for node in graph}
        reverse: Dict[str, List[str]] = defaultdict(list)

        for node, deps in graph.items():
            for dep in deps:
                if dep in graph:
                    reverse[dep].append(node)
                    in_degree[node] += 1

        # Seed the queue in insertion order so output is deterministic.
        queue: "deque[str]" = deque(
            node for node in graph if in_degree[node] == 0
        )
        order: List[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for dependent in reverse[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(graph):
            unresolved = [node for node in graph if in_degree[node] > 0]
            raise ValueError(
                f"Cycle detected in dependency graph; unresolved nodes: {unresolved}"
            )

        return order

    # ---------------------------------------------------------- execution gate

    def can_execute(self, change_name: str, completed: Set[str]) -> bool:
        """Return True when every dependency of ``change_name`` is in ``completed``.

        The graph is consulted through ``remaining_dependencies`` so a missing
        or unknown change (empty remainder) is treated as executable. Callers
        that need stricter semantics should validate names up-front.
        """
        graph = self._graph_cache
        deps = self.remaining_dependencies(change_name, completed, graph)
        return len(deps) == 0

    def remaining_dependencies(
        self,
        change_name: str,
        completed: Iterable[str],
        graph: Dict[str, List[str]],
    ) -> List[str]:
        """List dependencies of ``change_name`` that are not in ``completed``.

        Returned in the order they appear in the graph. A change with no entry
        in ``graph`` (or an empty dependency list) yields ``[]``.
        """
        completed_set = set(completed)
        deps = graph.get(change_name, [])
        return [dep for dep in deps if dep not in completed_set]

    # ----------------------------------------------------------------- state

    # ``can_execute`` is a hot path called many times per execution tick, but it
    # still needs the graph to know what to wait for. We cache the most recent
    # graph built via ``build_dependency_graph`` so callers can drive the gate
    # without re-passing the graph each time. ``remaining_dependencies`` is the
    # explicit variant for callers that want to keep multiple graphs in flight.
    _graph_cache: Dict[str, List[str]] = {}

    def __init__(self) -> None:
        self._graph_cache = {}