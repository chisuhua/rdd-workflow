"""Tests for artifact_dag.py — openspec DAG computation."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from skills.guide_plan.scripts.artifact_dag import (  # noqa: E402
    classify_ready_blocked,
    compute_required_artifacts,
    is_dag_available,
    parse_version,
    topological_order,
)


# === Version parsing ===

def test_parse_version_v170():
    assert parse_version("v1.7.0") == (1, 7, 0)


def test_parse_version_v200():
    assert parse_version("2.0.0") == (2, 0, 0)


def test_parse_version_v141():
    assert parse_version("1.4.1") == (1, 4, 1)


def test_parse_version_empty():
    assert parse_version("") == (0, 0, 0)


def test_parse_version_garbage():
    assert parse_version("xyz") == (0, 0, 0)


# === DAG availability ===

def test_dag_available_v170_true():
    assert is_dag_available("1.7.0") is True


def test_dag_available_v200_true():
    assert is_dag_available("v2.0.0") is True


def test_dag_available_v141_false():
    assert is_dag_available("1.4.1") is False


def test_dag_available_v131_false():
    assert is_dag_available("1.3.1") is False


# === Transitive closure ===

def test_compute_required_artifacts_simple():
    status = {
        "artifacts": [
            {"id": "proposal"},
            {"id": "design", "requires": ["proposal"]},
            {"id": "tasks", "requires": ["design"]},
        ],
        "applyRequires": ["tasks"],
    }
    closure = compute_required_artifacts(status)
    assert set(closure) == {"proposal", "design", "tasks"}


def test_compute_required_artifacts_multiple_roots():
    """applyRequires has multiple roots; closure must include all transitive deps."""
    status = {
        "artifacts": [
            {"id": "proposal"},
            {"id": "design", "requires": ["proposal"]},
            {"id": "tasks", "requires": ["design"]},
            {"id": "specs", "requires": ["proposal", "design"]},
        ],
        "applyRequires": ["tasks", "specs"],
    }
    closure = compute_required_artifacts(status)
    assert set(closure) == {"proposal", "design", "tasks", "specs"}


def test_compute_required_artifacts_no_extra_deps():
    """applyRequires with no requirements returns just those IDs."""
    status = {
        "artifacts": [
            {"id": "proposal"},
            {"id": "design", "requires": ["proposal"]},
        ],
        "applyRequires": ["proposal"],
    }
    closure = compute_required_artifacts(status)
    assert closure == ["proposal"]


def test_compute_required_artifacts_diamond_dep():
    """Diamond dependency: A -> B, A -> C, B -> D, C -> D — D appears once."""
    status = {
        "artifacts": [
            {"id": "proposal"},
            {"id": "design", "requires": ["proposal"]},
            {"id": "tasks", "requires": ["proposal"]},
            {"id": "specs", "requires": ["design", "tasks"]},
        ],
        "applyRequires": ["specs"],
    }
    closure = compute_required_artifacts(status)
    assert set(closure) == {"proposal", "design", "tasks", "specs"}
    assert len(closure) == 4  # no duplicates


# === Topological order ===

def test_topological_order_respects_dependencies():
    closure = ["proposal", "design", "tasks"]
    artifacts = {
        "proposal": {},
        "design": {"requires": ["proposal"]},
        "tasks": {"requires": ["design"]},
    }
    order = topological_order(closure, artifacts)
    assert order.index("proposal") < order.index("design")
    assert order.index("design") < order.index("tasks")


def test_topological_order_diamond():
    closure = ["proposal", "design", "tasks", "specs"]
    artifacts = {
        "proposal": {},
        "design": {"requires": ["proposal"]},
        "tasks": {"requires": ["proposal"]},
        "specs": {"requires": ["design", "tasks"]},
    }
    order = topological_order(closure, artifacts)
    assert order.index("proposal") < order.index("design")
    assert order.index("proposal") < order.index("tasks")
    assert order.index("design") < order.index("specs")
    assert order.index("tasks") < order.index("specs")


# === Ready/blocked ===

def test_classify_ready_blocked_ready():
    closure = ["proposal", "design"]
    artifacts = {
        "proposal": {"ready": True},
        "design": {"requires": ["proposal"], "ready": True},
    }
    result = classify_ready_blocked(closure, artifacts)
    assert set(result["ready"]) == {"proposal", "design"}
    assert result["blocked"] == []


def test_classify_ready_blocked_blocked():
    closure = ["proposal", "design"]
    artifacts = {
        "proposal": {"ready": False},
        "design": {"requires": ["proposal"], "ready": False},
    }
    result = classify_ready_blocked(closure, artifacts)
    # design has unmet requirement — definitely blocked
    assert "design" in result["blocked"]


def test_classify_ready_blocked_with_explicit_deps():
    """An artifact with unmet deps is always blocked, even if deps are absent."""
    closure = ["design"]
    artifacts = {
        "design": {"requires": ["proposal"], "ready": False},
    }
    result = classify_ready_blocked(closure, artifacts)
    assert "design" in result["blocked"]