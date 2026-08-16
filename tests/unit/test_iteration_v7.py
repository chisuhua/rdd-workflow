"""Tests for iteration v7 schema (cross_repo_dependencies field)."""
import json
import pytest


def test_schema_v7_includes_cross_repo_deps():
    from pathlib import Path
    schema_path = Path(__file__).resolve().parent.parent.parent / "skills/_lib/schemas/iteration_schema.json"
    schema = json.loads(schema_path.read_text())
    assert schema.get("properties", {}).get("version", {}).get("enum") == [3, 4, 5, 6, 7]
    assert "cross_repo_dependencies" in schema.get("properties", {}).get("changes", {}).get("items", {}).get("properties", {})


def test_v6_data_loads_with_v7_loader():
    v6 = {"version": 6, "changes": {"x": {"name": "x"}}}
    from skills._lib.iteration import load_iteration_v6_compat
    result = load_iteration_v6_compat(v6)
    assert result["version"] == 7
    assert "x" in result["changes"]


def test_save_iteration_v7_writes_correctly(tmp_path):
    data = {"version": 7, "changes": {"x": {"name": "x", "cross_repo_dependencies": []}}}
    out = tmp_path / "iter.json"
    from skills._lib.iteration import save_iteration_v7
    save_iteration_v7(out, data)
    loaded = json.loads(out.read_text())
    assert loaded["version"] == 7
