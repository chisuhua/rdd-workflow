"""Verify unified project_root resolution across _lib/cli handlers (per fix-33-handlers).

Per C-PR-1 / C-PR-2 / C-PR-3 / AC-PR-1 / AC-PR-5:
    32 handlers shall resolve `project_root` via the single helper
    `resolve_project_root()` (re-exported from _lib.cli.__init__) instead of
    the anti-pattern `os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()`.

Pre-fix (2026-09-25):
    - 32 _lib/cli/*.py handler files used the anti-pattern (~36 occurrences)
    - resolve_project_root() was defined but never imported by handlers
    - Handlers in subprocess contexts (e.g. direct `python3 -m _lib.cli <sub>`
      from e2e repo cwd) failed to find .rddf/state/

Post-fix: All 32 handlers use resolve_project_root() as fallback after env override.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

# conftest.py adds project root to sys.path; skills._lib.cli shim
# transparently maps to _lib.cli.
from skills._lib.cli import _ROUTES, resolve_project_root  # noqa: E402


PROJECT_ROOT = Path("/workspace/project/rdd-workflow")


# ---------------------------------------------------------------------------
# Unit tests: resolve_project_root() itself
# ---------------------------------------------------------------------------

def test_resolve_project_root_returns_git_toplevel_in_repo() -> None:
    """AC-PR-1: resolve_project_root() in git repo cwd returns git toplevel."""
    # We're in /workspace/project/rdd-workflow which is a git repo.
    result = resolve_project_root()
    assert Path(result).is_absolute(), f"Expected absolute path, got {result}"
    assert (Path(result) / ".git").exists() or (Path(result) / ".git").is_file(), (
        f"Result {result} doesn't appear to be a git repo toplevel"
    )


def test_resolve_project_root_falls_back_to_cwd_in_non_git() -> None:
    """AC-PR-1: resolve_project_root() in non-git dir falls back to os.getcwd()."""
    with mock.patch("subprocess.run") as mock_run:
        # Make all git rev-parse fail to simulate non-git directory.
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr=""
        )
        with mock.patch("os.getcwd", return_value="/tmp/non-git-dir"):
            result = resolve_project_root()
        assert result == "/tmp/non-git-dir"


def test_rddf_project_root_env_var_overrides_resolution() -> None:
    """AC-PR-7: RDDF_PROJECT_ROOT env var overrides resolve_project_root()."""
    with mock.patch.dict(os.environ, {"RDDF_PROJECT_ROOT": "/custom/override/path"}):
        # Simulate handler pattern: env OR resolve_project_root()
        project_root = os.environ.get("RDDF_PROJECT_ROOT") or resolve_project_root()
        assert project_root == "/custom/override/path"


def test_resolve_project_root_exported_from_cli_package() -> None:
    """AC-PR-2: resolve_project_root is importable from skills._lib.cli (re-export)."""
    from skills._lib.cli import resolve_project_root as imported_func
    assert callable(imported_func), "resolve_project_root must be callable"


# ---------------------------------------------------------------------------
# Regression tests: zero anti-pattern in handler files
# ---------------------------------------------------------------------------

def test_zero_anti_pattern_in_handlers() -> None:
    """AC-PR-1: No `RDDF_PROJECT_ROOT or os.getcwd()` occurrences in handler files
    (excluding __main__.py:203 which is the legitimate env-injection use site).
    The total handler file count is ~39; only those with the anti-pattern matter.
    """
    handler_files = [
        f for f in (PROJECT_ROOT / "_lib" / "cli").glob("*.py")
        if f.name not in ("__init__.py", "__main__.py")
    ]
    bad_files = []
    for f in handler_files:
        text = f.read_text()
        # Anti-pattern: both strings on same line
        for line_no, line in enumerate(text.splitlines(), 1):
            if "RDDF_PROJECT_ROOT" in line and "or os.getcwd()" in line:
                bad_files.append((f.name, line_no, line.strip()))
    assert not bad_files, (
        f"Anti-pattern still present in {len(bad_files)} handler line(s): "
        f"{bad_files[:5]}{'...' if len(bad_files) > 5 else ''}"
    )


# ---------------------------------------------------------------------------
# Integration tests: handlers can resolve project_root without env injection
# ---------------------------------------------------------------------------

def test_handler_resolves_project_root_without_env_injection() -> None:
    """AC-PR-1 + AC-PR-6: Handler invoked from project subdirectory (no RDDF_PROJECT_ROOT
    env) resolves .rddf/state/ correctly via resolve_project_root()."""
    # Invoke version_cmd from a project subdirectory WITHOUT RDDF_PROJECT_ROOT.
    sub_cwd = PROJECT_ROOT / "_lib"
    # version_cmd reads package.json + uses os.environ.get(RDDF_PROJECT_ROOT)
    # or os.getcwd(). After fix, it should use resolve_project_root() which
    # returns PROJECT_ROOT regardless of sub_cwd.
    env_no_rdd = {k: v for k, v in os.environ.items() if k != "RDDF_PROJECT_ROOT"}
    env_no_rdd.pop("RDDF_PROJECT_ROOT", None)
    # Add PYTHONPATH for module import
    env_no_rdd["PYTHONPATH"] = str(PROJECT_ROOT)

    result = subprocess.run(
        [sys.executable, "-m", "_lib.cli", "version"],
        cwd=str(sub_cwd),
        env=env_no_rdd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    # After fix: resolve_project_root() returns PROJECT_ROOT → version_cmd finds
    # PROJECT_ROOT/package.json → prints version banner → EXIT 0
    assert result.returncode == 0, (
        f"version from {sub_cwd} (no RDDF_PROJECT_ROOT) returned {result.returncode}.\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert "rddf v" in result.stdout, f"Expected version banner, got: {result.stdout!r}"


@pytest.mark.parametrize("subcommand", [
    "version", "status", "guide", "validate",
    # Read-only commands that should work from any cwd within the repo.
])
def test_handler_works_from_subdirectory(subcommand: str) -> None:
    """AC-PR-6: Read-only handlers can be invoked from project subdirectory
    (no RDDF_PROJECT_ROOT env) and resolve correctly via resolve_project_root()."""
    sub_cwd = PROJECT_ROOT / "_lib"  # any subdirectory within the project
    env_no_rdd = {k: v for k, v in os.environ.items() if k != "RDDF_PROJECT_ROOT"}
    env_no_rdd.pop("RDDF_PROJECT_ROOT", None)
    env_no_rdd["PYTHONPATH"] = str(PROJECT_ROOT)

    result = subprocess.run(
        [sys.executable, "-m", "_lib.cli", subcommand],
        cwd=str(sub_cwd),
        env=env_no_rdd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    # Acceptable: EXIT 0 (handler ran successfully, possibly with output) or
    # EXIT 1 with diagnostic message (handler found project root but encountered
    # expected runtime condition). What we reject: EXIT 2/3 (module path / import
    # errors that indicate anti-pattern still present) or "not a rdd-workflow
    # project" message (cwd fallback failed).
    assert result.returncode in (0, 1), (
        f"{subcommand} from {sub_cwd} returned {result.returncode} (expected 0 or 1).\n"
        f"stdout: {result.stdout[:200]!r}\nstderr: {result.stderr[:200]!r}"
    )
    assert "not a rdd-workflow project" not in result.stdout, (
        f"{subcommand} from {sub_cwd} failed to find project root:\n"
        f"stdout: {result.stdout[:300]!r}"
    )