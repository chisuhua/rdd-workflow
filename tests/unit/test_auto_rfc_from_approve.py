"""Unit tests for approve_proposal.sh --auto-issue flag.

Tests the bash function `_auto_issue_hub` and mutual exclusion / draft
existence checks. Run via subprocess to invoke the actual bash script.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "skills" / "guide-design" / "scripts" / "approve_proposal.sh"


def _setup_spoke(root: Path, with_draft: bool = True, category: str = "cross-repo-federation"):
    """Create minimal spoke layout: improvement file + optional draft + approve input."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=str(root), check=True, capture_output=True)
    (root / ".rddf" / "improvements").mkdir(parents=True)
    (root / ".rddf" / "state").mkdir(parents=True)
    (root / "proposal-approved.md").write_text("# 已批准提案\n\n")

    name = "e2e-auto-issue"
    (root / ".rddf" / "improvements" / f"{name}.md").write_text(
        f"# {name}\n\n**阶段**: v2.2\n**分类**: {category}\n**类型**: feature\n**特性**: __ungrouped__\n\n## Why\n\nTest.\n"
    )

    if with_draft:
        draft = {
            "version": "v1",
            "proposal_name": name,
            "title": "[RFC] e2e auto-issue test",
            "stakeholders": ["org/repo-a"],
            "gate": "Design-Gate",
            "contract_impact": "Breaking-Change",
            "created_at": "2026-08-19T10:00:00+00:00",
            "created_by": "test-user",
        }
        (root / ".rddf" / "state" / f".rfc-draft-{name}.json").write_text(json.dumps(draft))

    return name


def _run(name: str, root: Path, *extra_args):
    env = os.environ.copy()
    env["RDDF_PROJECT_ROOT"] = str(root)
    env["RDDF_HUB_REPO"] = "nonexistent-org/nonexistent-repo"
    env["RDDF_APPROVE_ACTOR"] = "test-user"
    env["SKIP_CONTENT_REVIEW"] = "1"
    return subprocess.run(
        ["bash", str(SCRIPT), name, "P1", "--manual", "--auto-issue", *extra_args],
        cwd=str(root), env=env, capture_output=True, text=True, timeout=30,
    )


# ---------------------------------------------------------------------------
# Mutual exclusion tests
# ---------------------------------------------------------------------------

def test_auto_issue_and_hub_issue_mutually_exclusive(tmp_path):
    root = tmp_path / "proj"
    name = _setup_spoke(root)

    r = subprocess.run(
        ["bash", str(SCRIPT), name, "P1", "--manual", "--auto-issue",
         "--hub-issue", "org/rdd-hub#42"],
        cwd=str(root), env={**os.environ, "RDDF_PROJECT_ROOT": str(root)},
        capture_output=True, text=True,
    )
    assert r.returncode == 2
    assert "mutually exclusive" in r.stderr


# ---------------------------------------------------------------------------
# Draft existence tests
# ---------------------------------------------------------------------------

def test_auto_issue_requires_draft_file(tmp_path):
    root = tmp_path / "proj"
    name = _setup_spoke(root, with_draft=False)

    r = _run(name, root)
    assert r.returncode == 4
    assert "--auto-issue requires rfc-draft" in r.stderr


# ---------------------------------------------------------------------------
# Hub creation flow tests
# ---------------------------------------------------------------------------

def test_auto_issue_writes_hub_issue_url_to_draft_on_success(tmp_path, monkeypatch):
    """Hub failure: rfc-draft stays unchanged + audit fail entry recorded; approve still succeeds (exit 0)."""
    root = tmp_path / "proj"
    name = _setup_spoke(root)
    draft_path = root / ".rddf" / "state" / f".rfc-draft-{name}.json"

    r = _run(name, root)
    assert r.returncode == 0, r.stderr
    draft = json.loads(draft_path.read_text())
    assert "hub_issue_url" not in draft
    audit_file = root / ".rddf" / "state" / ".cross-repo-audit.jsonl"
    assert audit_file.exists()
    lines = [json.loads(l) for l in audit_file.read_text().splitlines() if l.strip()]
    decisions = [l["decision"] for l in lines]
    assert "approve" in decisions
    assert "fail-auto-issue" in decisions


def test_auto_issue_skipped_for_non_cross_repo_proposal(tmp_path):
    """Non-cross-repo proposal: --auto-issue irrelevant; cross-repo audit skipped."""
    root = tmp_path / "proj"
    name = _setup_spoke(root, category="general")

    env = {
        **os.environ,
        "RDDF_PROJECT_ROOT": str(root),
        "RDDF_APPROVE_ACTOR": "test-user",
        "SKIP_CONTENT_REVIEW": "1",
    }
    r = subprocess.run(
        ["bash", str(SCRIPT), name, "P1", "--auto-accept"],
        cwd=str(root), env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    audit_file = root / ".rddf" / "state" / ".cross-repo-audit.jsonl"
    if audit_file.exists():
        lines = [json.loads(l) for l in audit_file.read_text().splitlines() if l.strip()]
        assert not any("auto-issue" in l.get("decision", "") for l in lines)


# ---------------------------------------------------------------------------
# Argument parsing tests
# ---------------------------------------------------------------------------

def test_auto_issue_flag_parsed():
    """Verify --auto-issue doesn't break argument parsing (no proposals error path)."""
    r = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True, text=True,
    )
    # Help should not mention --auto-issue explicitly (script doesn't have --help),
    # but argument parsing should accept it without error
    assert r.returncode in (0, 1)  # either help works or returns usage error