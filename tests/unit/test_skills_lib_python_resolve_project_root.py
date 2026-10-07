"""Verify skill-layer Python wrapper for project_root resolution.

Per C-SLP-1 / C-SLP-2 / C-SLP-3 / AC-SLP-1 / AC-SLP-2 / AC-SLP-3 / AC-SLP-7:
    The wrapper `skills._lib._python_resolve_project_root.resolve_project_root()`
    shall be:
    - importable from `skills._lib._python_resolve_project_root`
    - callable
    - env var (RDDF_PROJECT_ROOT) override-aware
    - behaviorally identical to `_lib.cli.__main__.resolve_project_root()`
    - NOT triggering `_lib.cli.__main__` module load at import time
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Importability / callability
# ---------------------------------------------------------------------------

def test_wrapper_module_importable() -> None:
    """AC-SLP-1: `skills._lib._python_resolve_project_root` is importable."""
    mod = importlib.import_module("skills._lib._python_resolve_project_root")
    assert hasattr(mod, "resolve_project_root"), "Wrapper must expose resolve_project_root()"


def test_resolve_project_root_callable() -> None:
    """AC-SLP-1: wrapper's resolve_project_root() is callable and returns str."""
    from skills._lib._python_resolve_project_root import resolve_project_root
    result = resolve_project_root()
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Env var override
# ---------------------------------------------------------------------------

def test_rddf_project_root_env_override_wins() -> None:
    """AC-SLP-2: RDDF_PROJECT_ROOT env var overrides the git probe."""
    with mock.patch.dict(os.environ, {"RDDF_PROJECT_ROOT": "/custom/override/path"}):
        from skills._lib._python_resolve_project_root import resolve_project_root
        assert resolve_project_root() == "/custom/override/path"


def test_env_override_takes_precedence_over_cwd() -> None:
    """AC-SLP-2: env override is preferred over fallback to os.getcwd()."""
    with mock.patch.dict(os.environ, {"RDDF_PROJECT_ROOT": "/explicit/path"}):
        from skills._lib._python_resolve_project_root import resolve_project_root
        result = resolve_project_root()
        assert result == "/explicit/path"
        assert result != os.getcwd()


# ---------------------------------------------------------------------------
# Behavior parity with dispatcher resolver
# ---------------------------------------------------------------------------

def test_behavioral_parity_with_dispatcher_resolver() -> None:
    """AC-SLP-3 + C-SLP-3: when env var is unset, wrapper delegates to
    dispatcher and produces identical results. (With env var set, the
    wrapper intentionally short-circuits before delegating -- this is
    by design, not a parity violation.)
    """
    from skills._lib._python_resolve_project_root import resolve_project_root as wrapper_fn
    from _lib.cli.__main__ import resolve_project_root as dispatcher_fn

    # Case: RDDF_PROJECT_ROOT unset -> wrapper delegates, parity with dispatcher.
    # Use empty string override so the existing real-env (None) doesn't leak.
    with mock.patch.dict(os.environ, {"RDDF_PROJECT_ROOT": ""}, clear=False):
        # Both should resolve to git toplevel (we're in a git repo).
        assert wrapper_fn() == dispatcher_fn()
        assert wrapper_fn() == str(PROJECT_ROOT)  # we're running in this repo


def test_fallback_to_cwd_in_non_git_directory() -> None:
    """AC-SLP-7: when not in a git repo and env var unset, returns os.getcwd()."""
    with mock.patch("subprocess.run") as mock_run:
        # Make all git rev-parse fail to simulate non-git directory.
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr=""
        )
        with mock.patch.dict(os.environ, {"RDDF_PROJECT_ROOT": ""}, clear=False):
            with mock.patch("os.getcwd", return_value="/tmp/non-git"):
                from skills._lib._python_resolve_project_root import resolve_project_root
                assert resolve_project_root() == "/tmp/non-git"


# ---------------------------------------------------------------------------
# Import-time safety (no circular import)
# ---------------------------------------------------------------------------

def test_import_does_not_trigger_dispatcher_module_load() -> None:
    """AC-SLP-1 + AC-SLP-3: importing the wrapper does NOT trigger loading of
    _lib.cli.__main__. This proves the lazy import pattern avoids the
    circular import risk documented in fix-33-handlers.

    Strategy: subprocess test -- import the wrapper in a fresh Python process
    and verify _lib.cli.__main__ was not loaded into sys.modules.

    Uses a CLEAN env (excluding RDDF_PROJECT_ROOT) so the wrapper actually
    delegates to dispatcher instead of short-circuiting on leaked env.
    """
    # Use subprocess so module load order is fresh.
    code = """
import sys

# Reset and capture sys.modules snapshot AFTER wrapper import
before = set(sys.modules.keys())
import skills._lib._python_resolve_project_root  # noqa: F401
after = set(sys.modules.keys())

new = after - before
# If lazy import works, _lib.cli.__main__ should NOT be in 'new' modules
assert '_lib.cli.__main__' not in new, (
    f"_lib.cli.__main__ was eagerly loaded by wrapper import. "
    f"New modules: {[m for m in new if 'cli' in m]}"
)
print("OK")
"""
    # Clean env: exclude RDDF_PROJECT_ROOT (which earlier tests may have leaked)
    # to ensure wrapper actually invokes the dispatcher, not short-circuits.
    clean_env = {k: v for k, v in os.environ.items() if k != "RDDF_PROJECT_ROOT"}
    clean_env["PYTHONPATH"] = str(PROJECT_ROOT)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        env=clean_env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Lazy import failed (returncode={result.returncode}).\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "OK" in result.stdout, f"Expected 'OK' in stdout, got: {result.stdout}"


def test_invocation_does_load_dispatcher_lazily() -> None:
    """After wrapper import (no eager load), calling resolve_project_root()
    triggers _lib.cli.__main__ load -- confirms lazy import pattern.

    Implemented as a subprocess test to avoid sys.modules pollution from
    earlier tests in the pytest session (other tests import the dispatcher
    directly, so it would be in sys.modules already).

    Uses a CLEAN env (excluding RDDF_PROJECT_ROOT) so the wrapper actually
    delegates to dispatcher instead of short-circuiting on leaked env."""
    code = """
import sys

# Wrapper import -- dispatcher must NOT be loaded yet.
import skills._lib._python_resolve_project_root  # noqa: F401
assert '_lib.cli.__main__' not in sys.modules, (
    '_lib.cli.__main__ was eagerly loaded by wrapper import'
)

# First invocation -- should trigger lazy import.
from skills._lib._python_resolve_project_root import resolve_project_root
result = resolve_project_root()
assert isinstance(result, str)

# After invocation -- dispatcher should be loaded.
assert '_lib.cli.__main__' in sys.modules, (
    'Lazy import should populate sys.modules after first call'
)
print('OK')
"""
    # Clean env: exclude RDDF_PROJECT_ROOT so wrapper actually delegates.
    clean_env = {k: v for k, v in os.environ.items() if k != "RDDF_PROJECT_ROOT"}
    clean_env["PYTHONPATH"] = str(PROJECT_ROOT)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        env=clean_env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Lazy import test failed (returncode={result.returncode}).\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "OK" in result.stdout, f"Expected 'OK' in stdout, got: {result.stdout}"


# ---------------------------------------------------------------------------
# Cross-language parity (bash wrapper)
# ---------------------------------------------------------------------------

def test_cross_language_parity_with_bash_helper() -> None:
    """AC-SLP-7: under identical conditions, the Python wrapper and the bash
    helper `_resolve_project_root` SHALL return the same path.

    Both helpers use the same resolution order (env override -> git probe -> cwd).

    Uses monkeypatch to override RDDF_PROJECT_ROOT explicitly so the test
    is not affected by env leaks from earlier tests in the session.
    """
    import subprocess as sp
    test_root = str(PROJECT_ROOT)

    # Use subprocess with CLEAN env (no leaked RDDF_PROJECT_ROOT) for the
    # bash helper call to ensure bash also sees the expected path.
    bash_helper_file = PROJECT_ROOT / "skills/_lib/orchestrator_entry.sh"
    bash_content = bash_helper_file.read_text()
    bash_lines = [
        line for line in bash_content.split("\n")
        if not line.strip().startswith("set -")
    ]
    bash_body = "\n".join(bash_lines)
    bash_script = (
        f'set -e\nsource /dev/stdin <<\'ORCH_EOF\'\n{bash_body}\nORCH_EOF\n'
        f'export RDDF_PROJECT_ROOT="{test_root}"\n'
        f'_resolve_project_root\n'
    )
    clean_env = {k: v for k, v in os.environ.items() if k != "RDDF_PROJECT_ROOT"}
    clean_env["RDDF_PROJECT_ROOT"] = test_root  # explicit override
    bash_result = sp.run(
        ["bash", "-c", bash_script],
        cwd=test_root,
        env=clean_env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert bash_result.returncode == 0, (
        f"Bash helper failed: rc={bash_result.returncode}, stderr={bash_result.stderr!r}"
    )
    bash_out = bash_result.stdout.strip()
    assert bash_out == test_root, (
        f"Bash returned {bash_out!r}, expected {test_root!r}"
    )

    # Run python wrapper with monkeypatch to override leaked env.
    # monkeypatch.setenv automatically restores the original value after the test.
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("RDDF_PROJECT_ROOT", test_root)
    try:
        from skills._lib._python_resolve_project_root import resolve_project_root
        py_result = resolve_project_root()
    finally:
        monkeypatch.undo()

    assert py_result == test_root, (
        f"Python wrapper returned {py_result!r}, expected {test_root!r}"
    )
    assert py_result == bash_out, (
        f"Parity violation: Python={py_result!r}, Bash={bash_out!r}"
    )


# ---------------------------------------------------------------------------
# Skill scripts use the wrapper (no direct dispatcher import)
# ---------------------------------------------------------------------------

SCRIPTS = [
    "skills/propose/scripts/propose_quality_check.py",
    "skills/propose/scripts/propose_quality_hook.py",
    "skills/report-issue/scripts/report_issue_rfc.py",
    "skills/sync-hub/scripts/sync_hub.py",
    "skills/watch-hub/scripts/watch_hub.py",
]


@pytest.mark.parametrize("script_rel", SCRIPTS)
def test_script_imports_wrapper_not_dispatcher(script_rel: str) -> None:
    """AC-SLP-2: each skill script imports from `skills._lib._python_resolve_project_root`,
    not from `_lib.cli.__main__`."""
    text = (PROJECT_ROOT / script_rel).read_text()
    assert "from skills._lib._python_resolve_project_root import resolve_project_root" in text, (
        f"{script_rel} should import from skills._lib._python_resolve_project_root"
    )
    assert "from _lib.cli.__main__ import resolve_project_root" not in text, (
        f"{script_rel} still imports directly from _lib.cli.__main__"
    )