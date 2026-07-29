"""Unit tests for proposal_deps_analyzer module."""
import os
import sys
import importlib.util

import pytest

def _load_module():
    module_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "skills", "propose", "scripts", "proposal_deps_analyzer.py"
    )
    spec = importlib.util.spec_from_file_location("proposal_deps_analyzer", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {module_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_pda = _load_module()
parse_proposal_metadata = _pda.parse_proposal_metadata
topological_sort = _pda.topological_sort


def test_parse_deps_metadata():
    content = "**依赖**: [add-bar, add-baz]\n**特性**: wave-core"
    result = parse_proposal_metadata(content)
    assert result["deps"] == ["add-bar", "add-baz"]
    assert result["feature"] == "wave-core"


def test_parse_no_deps():
    content = "Some proposal without deps"
    result = parse_proposal_metadata(content)
    assert result["deps"] == []
    assert result["feature"] is None


def test_auto_detect_references():
    content = "See improvements/add-foo.md for details"
    result = parse_proposal_metadata(content)
    assert "add-foo" in result["auto_detected"]


def test_topological_sort_simple():
    proposals = [
        {"name": "a", "deps": ["b"]},
        {"name": "b", "deps": []},
    ]
    result = topological_sort(proposals)
    assert result.index("b") < result.index("a")


def test_topological_sort_chain():
    proposals = [
        {"name": "c", "deps": ["b"]},
        {"name": "b", "deps": ["a"]},
        {"name": "a", "deps": []},
    ]
    result = topological_sort(proposals)
    assert result.index("a") < result.index("b")
    assert result.index("b") < result.index("c")


def test_topological_sort_no_deps():
    proposals = [
        {"name": "x", "deps": []},
        {"name": "y", "deps": []},
    ]
    result = topological_sort(proposals)
    assert len(result) == 2
    assert "x" in result
    assert "y" in result
