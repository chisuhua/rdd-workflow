"""Unit tests for cross_repo_deps core (parse/graph/cycle/topo/eta/mermaid)."""
import json
from pathlib import Path
import tempfile
import pytest

from skills._lib.cross_repo_deps import (
    parse_spoke_iteration,
    build_cross_repo_graph,
    detect_cycle,
    kahn_topological_sort,
    eta_fallback_chain,
    generate_mermaid,
)


def test_parse_spoke_iteration_extracts_deps():
    data = {
        "version": 7,
        "changes": {
            "add-x": {
                "spoke_repo": "org/repo-a",
                "cross_repo_dependencies": ["org/repo-b#add-y"],
            }
        }
    }
    result = parse_spoke_iteration(data, spoke_key="org/repo-a")
    assert result == [{"change": "add-x", "depends_on": "org/repo-b#add-y"}]


def test_build_cross_repo_graph_no_deps():
    spokes = {"org/a": [], "org/b": []}
    graph = build_cross_repo_graph(spokes)
    assert graph == {"org/a": [], "org/b": []}


def test_build_cross_repo_graph_with_deps():
    spokes = {
        "org/a": [{"change": "add-x", "depends_on": "org/b#add-y"}],
        "org/b": [],
    }
    graph = build_cross_repo_graph(spokes)
    assert graph["org/a"] == ["org/b#add-y"]


def test_detect_cycle_finds_loop():
    graph = {"a": ["b"], "b": ["a"]}
    cycle = detect_cycle(graph)
    assert "a" in cycle or "b" in cycle


def test_detect_cycle_no_loop():
    graph = {"a": ["b"], "b": ["c"], "c": []}
    assert detect_cycle(graph) == []


def test_kahn_topological_sort_returns_waves():
    graph = {"a": ["b"], "b": []}
    waves = kahn_topological_sort(graph)
    assert waves == [["b"], ["a"]]


def test_eta_fallback_chain_lv1_from_tasks():
    with tempfile.TemporaryDirectory() as tmp:
        tasks = Path(tmp) / "tasks.md"
        tasks.write_text("- [ ] task1\n- [ ] task2\n")
        eta = eta_fallback_chain({"tasks_path": str(tasks)})
        assert eta == 2


def test_eta_fallback_chain_lv2_from_frontmatter():
    eta = eta_fallback_chain({"eta": 5})
    assert eta == 5


def test_eta_fallback_chain_lv3_manual():
    eta = eta_fallback_chain({"manual_eta": 10})
    assert eta == 10


def test_generate_mermaid_basic():
    graph = {"a": ["b"]}
    etas = {"a": 3, "b": 5}
    mermaid = generate_mermaid(graph, etas)
    assert "graph TD" in mermaid
    assert "a --> b" in mermaid
    assert "3d" in mermaid
