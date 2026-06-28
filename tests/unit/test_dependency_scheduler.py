"""Tests for DependencyScheduler — Kahn topological sort + cycle detection."""
import pytest

from skills._lib.dependency_scheduler import DependencyScheduler


@pytest.fixture
def scheduler():
    return DependencyScheduler()


# ---------------------------------------------------------------------------
# build_dependency_graph + topological_sort
# ---------------------------------------------------------------------------


def test_empty_graph_returns_empty_order(scheduler):
    """Empty input graph produces an empty topological order."""
    changes = []
    graph = scheduler.build_dependency_graph(changes)
    assert graph == {}
    order = scheduler.topological_sort(graph)
    assert order == []


def test_simple_linear_dependency(scheduler):
    """A -> B -> C linearizes to [A, B, C]."""
    changes = [
        {"name": "A", "dependencies": []},
        {"name": "B", "dependencies": ["A"]},
        {"name": "C", "dependencies": ["B"]},
    ]
    graph = scheduler.build_dependency_graph(changes)
    order = scheduler.topological_sort(graph)
    assert order == ["A", "B", "C"]


def test_diamond_dependency(scheduler):
    """Diamond: A -> B, A -> C, B -> D, C -> D. D must come last; A first."""
    changes = [
        {"name": "A", "dependencies": []},
        {"name": "B", "dependencies": ["A"]},
        {"name": "C", "dependencies": ["A"]},
        {"name": "D", "dependencies": ["B", "C"]},
    ]
    graph = scheduler.build_dependency_graph(changes)
    order = scheduler.topological_sort(graph)
    assert order[0] == "A"
    assert order[-1] == "D"
    assert order.index("B") < order.index("D")
    assert order.index("C") < order.index("D")
    assert set(order) == {"A", "B", "C", "D"}


def test_cycle_detection_raises(scheduler):
    """A -> B -> A cycle must raise ValueError."""
    changes = [
        {"name": "A", "dependencies": ["B"]},
        {"name": "B", "dependencies": ["A"]},
    ]
    graph = scheduler.build_dependency_graph(changes)
    with pytest.raises(ValueError):
        scheduler.topological_sort(graph)


# ---------------------------------------------------------------------------
# can_execute
# ---------------------------------------------------------------------------


def test_can_execute_returns_true_when_no_deps(scheduler):
    """A node with no dependencies is always executable."""
    changes = [{"name": "A", "dependencies": []}]
    scheduler.build_dependency_graph(changes)
    assert scheduler.can_execute("A", set()) is True
    assert scheduler.can_execute("A", {"something-else"}) is True


def test_can_execute_returns_false_when_deps_unmet(scheduler):
    """B depends on A; with A not yet completed, B cannot execute."""
    changes = [
        {"name": "A", "dependencies": []},
        {"name": "B", "dependencies": ["A"]},
    ]
    scheduler.build_dependency_graph(changes)
    assert scheduler.can_execute("B", set()) is False
    assert scheduler.can_execute("B", {"other"}) is False


def test_can_execute_returns_true_when_all_deps_met(scheduler):
    """B depends on A and C; once both are completed, B is executable."""
    changes = [
        {"name": "A", "dependencies": []},
        {"name": "B", "dependencies": []},
        {"name": "C", "dependencies": ["A", "B"]},
    ]
    scheduler.build_dependency_graph(changes)
    assert scheduler.can_execute("C", {"A", "B"}) is True