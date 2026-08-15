"""Tests for from_issue.env validation — anti-injection safety + format checks.

Validates:
1. ADD_IMPROVE_FROM_ISSUE must be a positive integer (issue number).
2. ADD_IMPROVE_GH_REPO must match "owner/repo" pattern (no shell metacharacters).
3. ADD_IMPROVE_ISSUE_TITLE max 200 chars, no shell metacharacters.
4. ADD_IMPROVE_ISSUE_BODY max 4000 chars (truncation enforced upstream).
5. Hard-exit (exit 1) on validation failure; describe mode prints JSON.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

WT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = WT_ROOT / "skills" / "add-improve" / "scripts" / "from_issue.env.py"


def _run_validate(env_overrides: dict):
    """Run from_issue.env.py validate with given env-var overrides."""
    env = os.environ.copy()
    for k, v in env_overrides.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    return subprocess.run(
        [sys.executable, str(SCRIPT), "validate"],
        env=env, capture_output=True, text=True,
    )


def _run_describe(env_overrides: dict):
    env = os.environ.copy()
    for k, v in env_overrides.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    return subprocess.run(
        [sys.executable, str(SCRIPT), "describe"],
        env=env, capture_output=True, text=True,
    )


# === Test Group 1: Format validation ===

def test_rejects_non_integer_issue_number():
    """From-issue must be a positive integer."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ISSUE": "not-a-number",
        "ADD_IMPROVE_GH_REPO": "foo/bar",
        "ADD_IMPROVE_ISSUE_TITLE": "Test",
    })
    assert result.returncode != 0
    assert "integer" in result.stderr.lower() or "issue" in result.stderr.lower()


def test_rejects_zero_or_negative_issue_number():
    """Issue number must be >= 1."""
    for bad in ["0", "-1"]:
        result = _run_validate({
            "ADD_IMPROVE_FROM_ISSUE": bad,
            "ADD_IMPROVE_GH_REPO": "foo/bar",
            "ADD_IMPROVE_ISSUE_TITLE": "Test",
        })
        assert result.returncode != 0, f"should reject {bad}"


def test_rejects_invalid_gh_repo_format():
    """Gh-repo must match owner/repo pattern."""
    for bad in ["foo", "foo/bar/extra", "../../etc/passwd"]:
        result = _run_validate({
            "ADD_IMPROVE_FROM_ISSUE": "42",
            "ADD_IMPROVE_GH_REPO": bad,
            "ADD_IMPROVE_ISSUE_TITLE": "Test",
        })
        assert result.returncode != 0, f"should reject {bad}"


# === Test Group 2: Anti-injection in title and body ===

def test_rejects_shell_metachars_in_title():
    """Title must not contain shell metacharacters."""
    for evil in ["evil$(whoami)", "evil`id`", "evil;rm", "evil|cat", "evil&bg"]:
        result = _run_validate({
            "ADD_IMPROVE_FROM_ISSUE": "42",
            "ADD_IMPROVE_GH_REPO": "foo/bar",
            "ADD_IMPROVE_ISSUE_TITLE": evil,
        })
        assert result.returncode != 0, f"should reject {evil!r}"


def test_rejects_oversized_title():
    """Title must be <= 200 chars."""
    long_title = "x" * 201
    result = _run_validate({
        "ADD_IMPROVE_FROM_ISSUE": "42",
        "ADD_IMPROVE_GH_REPO": "foo/bar",
        "ADD_IMPROVE_ISSUE_TITLE": long_title,
    })
    assert result.returncode != 0
    assert "200" in result.stderr


def test_rejects_oversized_body():
    """Body must be <= 4000 chars (truncation enforced upstream)."""
    long_body = "x" * 4001
    result = _run_validate({
        "ADD_IMPROVE_FROM_ISSUE": "42",
        "ADD_IMPROVE_GH_REPO": "foo/bar",
        "ADD_IMPROVE_ISSUE_TITLE": "Test",
        "ADD_IMPROVE_ISSUE_BODY": long_body,
    })
    assert result.returncode != 0
    assert "4000" in result.stderr


# === Test Group 3: Happy path + describe mode ===

def test_accepts_valid_inputs():
    """Valid inputs produce exit 0."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ISSUE": "42",
        "ADD_IMPROVE_GH_REPO": "chisuhua/rdd-workflow",
        "ADD_IMPROVE_ISSUE_TITLE": "Fix race condition",
        "ADD_IMPROVE_ISSUE_BODY": "Steps to reproduce...",
    })
    assert result.returncode == 0, result.stderr


def test_describe_returns_json():
    """Describe mode prints JSON with all validated fields."""
    result = _run_describe({
        "ADD_IMPROVE_FROM_ISSUE": "42",
        "ADD_IMPROVE_GH_REPO": "chisuhua/rdd-workflow",
        "ADD_IMPROVE_ISSUE_TITLE": "Fix race",
        "ADD_IMPROVE_ISSUE_BODY": "Body",
    })
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["issue_num"] == 42
    assert data["gh_repo"] == "chisuhua/rdd-workflow"
    assert data["title"] == "Fix race"
    assert data["body"] == "Body"
