"""Verify Python project_root resolution impls satisfy contract invariants.

Per consolidate-resolve-project-root-helpers (P3):
    Tests 3 invariants across 2 Python impls = 6 parametrize cases:
    - skills._lib._python_resolve_project_root.resolve_project_root (skill wrapper)
    - _lib.cli.__main__.resolve_project_root (CLI dispatcher)

Invariants (per skills/_lib/_resolve_project_root_contract.yaml):
    - invariant_env_override: RDDF_PROJECT_ROOT env var wins
    - invariant_git_probe: in git repo → git toplevel
    - invariant_cwd_fallback: non-git → cwd as-is

Note: invariant_function_signature (return type str) is implicit in
the return value checks below; if a future impl returns non-str, the
equality assertions will fail.

Implementation note: We call the functions directly (not via subprocess)
because the wrapper triggers a circular import in fresh interpreters
(via skills/_lib/cli/__init__.py shim — pre-existing issue, see
add-skill-layer-resolve-project-root-helper). Direct calls work fine
in the test process where modules are already loaded.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path
from unittest import mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# Resolve the 2 Python impls under test.
# Note: return a callable that, when invoked, calls the impl's
# resolve_project_root() — not the function itself.
def _resolve_wrapper():
    """skill layer wrapper (shipped commit 281423d)."""
    mod = importlib.import_module("skills._lib._python_resolve_project_root")
    return mod.resolve_project_root()


def _resolve_cli():
    """CLI dispatcher resolver (per ADR-0033)."""
    mod = importlib.import_module("_lib.cli.__main__")
    return mod.resolve_project_root()


IMPLS = [
    ("skill_wrapper", _resolve_wrapper),
    ("cli_dispatcher", _resolve_cli),
]


@pytest.fixture(autouse=True)
def _isolate_rddf_env_and_cwd(monkeypatch):
    """Strip RDDF_PROJECT_ROOT (avoid leakage from earlier tests via
    cli_main.main()'s os.environ.setdefault at _lib/cli/__main__.py:203)
    and snapshot cwd (restore after each test).
    """
    monkeypatch.delenv("RDDF_PROJECT_ROOT", raising=False)
    monkeypatch.chdir(PROJECT_ROOT)


# ---------------------------------------------------------------------------
# invariant_env_override
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("impl_name,resolve_fn", IMPLS[:1])  # only skill_wrapper
def test_invariant_env_override_wins_when_rddf_set(impl_name, resolve_fn):
    """Contract: if RDDF_PROJECT_ROOT env var set and non-empty, return it.

    Applies to bash_helper and python_wrapper (skill layer).
    NOTE: python_cli dispatcher does NOT honor this invariant — see
    test_python_cli_does_not_honor_env_override for the layer-specific
    exception documented in the contract.
    """
    with mock.patch.dict(os.environ, {"RDDF_PROJECT_ROOT": "/explicit/override"}, clear=False):
        assert resolve_fn() == "/explicit/override"


def test_python_cli_does_not_honor_env_override():
    """Layer-specific exception (per contract): CLI dispatcher does NOT
    honor RDDF_PROJECT_ROOT env var by default. Callers must set env var
    before invoking if override is needed (e.g. _lib.cli.__main__.py:203
    setdefault at cli_main.main() entry does this for the CLI itself).
    """
    with mock.patch.dict(os.environ, {"RDDF_PROJECT_ROOT": "/explicit/override"}, clear=False):
        result = _resolve_cli()
        # CLI dispatcher falls through to git probe (returning PROJECT_ROOT).
        # This is documented behavior per consolidate-resolve-project-root-helpers.
        assert result == str(PROJECT_ROOT)


@pytest.mark.parametrize("impl_name,resolve_fn", IMPLS)
def test_invariant_env_override_empty_falls_through(impl_name, resolve_fn):
    """Contract: empty string falls through to git probe (truthy check)."""
    with mock.patch.dict(os.environ, {"RDDF_PROJECT_ROOT": ""}, clear=False):
        # When in git repo (we are in PROJECT_ROOT per autouse fixture),
        # should return PROJECT_ROOT not "".
        assert resolve_fn() == str(PROJECT_ROOT)


# ---------------------------------------------------------------------------
# invariant_git_probe
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("impl_name,resolve_fn", IMPLS)
def test_invariant_git_probe_returns_toplevel_when_in_repo(impl_name, resolve_fn):
    """Contract: env var unset AND cwd in git repo → git toplevel."""
    # autouse fixture sets cwd=PROJECT_ROOT (git repo)
    assert resolve_fn() == str(PROJECT_ROOT)


# ---------------------------------------------------------------------------
# invariant_cwd_fallback
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("impl_name,resolve_fn", IMPLS)
def test_invariant_cwd_fallback_returns_cwd_when_no_git(impl_name, resolve_fn):
    """Contract: env var unset AND cwd NOT in git repo → cwd as-is.

    /tmp is not a git repo (typically). Use monkeypatch.chdir to control cwd.
    """
    with mock.patch.dict(os.environ, {}, clear=False):
        os.chdir("/tmp")  # not in git repo
        try:
            assert resolve_fn() == "/tmp"
        finally:
            os.chdir(PROJECT_ROOT)  # restore


# ---------------------------------------------------------------------------
# invariant_function_signature (implicit via return value checks above)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("impl_name,resolve_fn", IMPLS)
def test_invariant_returns_str_type(impl_name, resolve_fn):
    """Contract: returns absolute path string."""
    result = resolve_fn()
    assert isinstance(result, str), f"{impl_name} returned non-str: {type(result)}"
    assert result.startswith("/"), f"{impl_name} returned non-absolute: {result!r}"