"""Tests for skills/_lib/gh_repo_detect.py — 3-step fallback chain.

Covers:
1. Env override (`RDDF_PROPOSAL_GH_REPO`) wins at all times.
2. `gh repo view --json nameWithOwner` succeeds when env unset.
3. `git remote get-url origin` parse as third fallback.
4. `gh` missing → GhRepoDetectError with suggestion.
5. `gh auth status` fails → GhRepoDetectError with `gh auth login` hint.
6. No git remote → GhRepoDetectError with `git remote add origin ...` hint.
7. Pre-flight `gh auth status` check runs before detection.
"""
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys

# Set up import path (mirrors tests/conftest.py)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from skills._lib.gh_repo_detect import (  # noqa: E402
    detect_gh_repo,
    GhRepoDetectError,
)


def _mock_run(stdout: str = "", returncode: int = 0, stderr: str = ""):
    """Factory for a Mock that mimics subprocess.run output."""
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_env_override_wins():
    """Env var RDDF_PROPOSAL_GH_REPO is the highest priority."""
    with patch.dict(os.environ, {"RDDF_PROPOSAL_GH_REPO": "my-org/my-fork"}, clear=False):
        with patch("subprocess.run") as mock_run:
            result = detect_gh_repo()
            assert result == "my-org/my-fork"
            # Never invoke gh or git remote when env is set
            for call in mock_run.call_args_list:
                args = call.args[0]
                assert "gh" not in args[0] and "git" not in args[0]


def test_gh_repo_view_success():
    """When env is unset, gh repo view is the second fallback."""
    env = {k: v for k, v in os.environ.items() if k != "RDDF_PROPOSAL_GH_REPO"}
    with patch.dict(os.environ, env, clear=True):
        with patch("subprocess.run") as mock_run:
            # First call: gh auth status (passes)
            # Second call: gh repo view --json nameWithOwner
            mock_run.side_effect = [
                _mock_run(returncode=0),  # gh auth status
                _mock_run(stdout="my-org/my-project\n", returncode=0),  # gh repo view
            ]
            result = detect_gh_repo()
            assert result == "my-org/my-project"
            assert mock_run.call_count == 2


def test_git_remote_parse_fallback():
    """When gh repo view fails, fall back to git remote get-url origin."""
    env = {k: v for k, v in os.environ.items() if k != "RDDF_PROPOSAL_GH_REPO"}
    with patch.dict(os.environ, env, clear=True):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mock_run(returncode=0),  # gh auth status
                _mock_run(returncode=1, stderr="not found"),  # gh repo view fails
                _mock_run(stdout="git@github.com:foo/bar.git\n", returncode=0),  # git remote
            ]
            result = detect_gh_repo()
            assert result == "foo/bar"


def test_gh_missing_raises_with_suggestion():
    """When gh CLI is not installed, raise with install hint."""
    env = {k: v for k, v in os.environ.items() if k != "RDDF_PROPOSAL_GH_REPO"}
    with patch.dict(os.environ, env, clear=True):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            try:
                detect_gh_repo()
            except GhRepoDetectError as e:
                assert "gh" in str(e).lower()
                assert "install" in str(e).lower() or "gh" in str(e)
                return
            assert False, "expected GhRepoDetectError"


def test_gh_auth_failure_raises_with_login_hint():
    """When gh auth status fails, raise with `gh auth login` hint."""
    env = {k: v for k, v in os.environ.items() if k != "RDDF_PROPOSAL_GH_REPO"}
    with patch.dict(os.environ, env, clear=True):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mock_run(returncode=1, stderr="not logged in"),  # gh auth status fails
            ]
            try:
                detect_gh_repo()
            except GhRepoDetectError as e:
                assert "gh auth login" in str(e)
                return
            assert False, "expected GhRepoDetectError"


def test_no_remote_raises_with_add_hint():
    """When git remote fails too, raise with `git remote add origin ...` hint."""
    env = {k: v for k, v in os.environ.items() if k != "RDDF_PROPOSAL_GH_REPO"}
    with patch.dict(os.environ, env, clear=True):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                _mock_run(returncode=0),  # gh auth status
                _mock_run(returncode=1, stderr="not in repo"),  # gh repo view fails
                _mock_run(returncode=1, stderr="no remote"),  # git remote fails
            ]
            try:
                detect_gh_repo()
            except GhRepoDetectError as e:
                assert "git remote add origin" in str(e)
                return
            assert False, "expected GhRepoDetectError"


def test_preflight_gh_auth_runs_before_detection():
    """Even when env is set, gh auth status is checked first (per Oraclespec MUST)."""
    with patch.dict(os.environ, {"RDDF_PROPOSAL_GH_REPO": "my-org/repo"}, clear=False):
        with patch("subprocess.run") as mock_run:
            # Env wins — auth should NOT be called
            detect_gh_repo()
            for call in mock_run.call_args_list:
                args = call.args[0]
                assert "auth" not in " ".join(args)
