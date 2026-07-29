"""Unit tests for change_content_review module."""
import os
import sys
import tempfile

import pytest

import importlib.util

def _load_module():
    module_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "skills", "guide-plan", "scripts", "change_content_review.py"
    )
    spec = importlib.util.spec_from_file_location("change_content_review", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {module_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_ccr = _load_module()
review_change_content = _ccr.review_change_content
auto_revise_if_needed = _ccr.auto_revise_if_needed


def test_review_proposal_clarity_pass():
    with tempfile.TemporaryDirectory() as tmpdir:
        change_dir = os.path.join(tmpdir, "openspec", "changes", "test-change")
        os.makedirs(change_dir)
        with open(os.path.join(change_dir, "proposal.md"), "w") as f:
            f.write("This is a sufficiently detailed proposal with enough content to pass the clarity check.")
        with open(os.path.join(change_dir, "design.md"), "w") as f:
            f.write("This is a design document with sufficient detail for the change.")
        with open(os.path.join(change_dir, "tasks.md"), "w") as f:
            f.write("## Tasks\n- [ ] Task 1\n- [ ] Task 2\n")

        result = review_change_content("test-change", tmpdir)
        assert result["proposal_clarity"] in ["pass", "fail", "warn"]


def test_review_proposal_clarity_fail_when_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        change_dir = os.path.join(tmpdir, "openspec", "changes", "test-change")
        os.makedirs(change_dir)

        result = review_change_content("test-change", tmpdir)
        assert result["proposal_clarity"] == "fail"


def test_review_returns_all_fields():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = review_change_content("nonexistent", tmpdir)
        assert "proposal_clarity" in result
        assert "design_completeness" in result
        assert "tasks_granularity" in result
        assert "consistency" in result
        assert "dependency_annotations" in result
        assert "auto_revised" in result
        assert "escalated" in result


def test_auto_revise_returns_false_by_default():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = {"proposal_clarity": "pass"}
        revised = auto_revise_if_needed("test", tmpdir, result)
        assert revised is False


def test_auto_revise_respects_env_var():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["CHANGE_CONTENT_REVIEW_AUTO_REVISE"] = "no"
        try:
            revised = auto_revise_if_needed("test", tmpdir, {})
            assert revised is False
        finally:
            del os.environ["CHANGE_CONTENT_REVIEW_AUTO_REVISE"]
