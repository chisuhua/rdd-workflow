"""Verify --help / -h uniform handling for all rddf subcommands (per fix-cmd-help-handling).

Per C-HELP-1 / C-HELP-2 / AC-HELP-1 / AC-HELP-2 / AC-HELP-3 / AC-HELP-4:
    `rddf <sub> --help` and `rddf <sub> -h` MUST return EXIT 0 for all 36
    subcommands. The dispatcher in _lib/cli/__init__.py::route() is expected
    to short-circuit --help/-h before invoking per-subcommand handlers.

Pre-fix (2026-09-25):
    - `rddf contract-check --help` → EXIT 2 (handler overrides argparse auto-help)
    - `rddf archive-sync --help` → EXIT 1 (no --help handling, --help treated as change name)

Post-fix: All 36 subcommands must exit 0 with --help / -h.

Strategy:
    1. Import _lib.cli (which loads _ROUTES via skills._lib.cli shim).
    2. For each subcommand in _ROUTES, invoke route(subcommand, ["--help"]) and
       route(subcommand, ["-h"]) and assert exit code 0.
    3. Also verify stdout/stderr contains the subcommand name (sanity).
"""
from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import pytest

# conftest.py adds project root to sys.path; skills._lib.cli shim
# transparently maps to _lib.cli.
from skills._lib.cli import _ROUTES, route  # noqa: E402


def _capture_route(subcommand: str, args: list[str]) -> tuple[int, str, str]:
    """Invoke route(subcommand, args) and capture stdout/stderr + return code."""
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        try:
            rc = route(subcommand, args)
        except SystemExit as e:
            # argparse calls sys.exit(0) for --help; capture and convert.
            rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    return rc, buf_out.getvalue(), buf_err.getvalue()


# All subcommands exposed via _ROUTES. Snapshot at test discovery time so the
# suite catches new subcommands when added (parametrize iterates the live dict).
ALL_SUBCOMMANDS = sorted(_ROUTES.keys())


@pytest.mark.parametrize("subcommand", ALL_SUBCOMMANDS)
def test_long_help_returns_zero(subcommand: str) -> None:
    """AC-HELP-1 / C-HELP-1: `rddf <sub> --help` returns EXIT 0."""
    rc, stdout, stderr = _capture_route(subcommand, ["--help"])
    assert rc == 0, (
        f"{subcommand} --help returned {rc} (expected 0).\n"
        f"stdout: {stdout!r}\nstderr: {stderr!r}"
    )


@pytest.mark.parametrize("subcommand", ALL_SUBCOMMANDS)
def test_short_h_returns_zero(subcommand: str) -> None:
    """AC-HELP-2 / C-HELP-2: `rddf <sub> -h` returns EXIT 0."""
    rc, stdout, stderr = _capture_route(subcommand, ["-h"])
    assert rc == 0, (
        f"{subcommand} -h returned {rc} (expected 0).\n"
        f"stdout: {stdout!r}\nstderr: {stderr!r}"
    )


@pytest.mark.parametrize("subcommand", ALL_SUBCOMMANDS)
def test_help_output_mentions_subcommand(subcommand: str) -> None:
    """Sanity: help output should reference the subcommand name (in usage line)."""
    rc, stdout, stderr = _capture_route(subcommand, ["--help"])
    combined = stdout + stderr
    assert rc == 0, f"{subcommand} --help returned {rc} (expected 0)"
    assert subcommand in combined, (
        f"{subcommand} --help output missing subcommand name.\n"
        f"combined: {combined[:300]!r}"
    )


# Targeted regression tests for the two known-broken subcommands (pre-fix).
def test_contract_check_help_regression() -> None:
    """AC-HELP-1 regression: contract-check --help used to return EXIT 2."""
    rc, stdout, stderr = _capture_route("contract-check", ["--help"])
    assert rc == 0, f"contract-check --help still returns {rc} (regression)"


def test_archive_sync_help_regression() -> None:
    """AC-HELP-1 regression: archive-sync --help used to return EXIT 1."""
    rc, stdout, stderr = _capture_route("archive-sync", ["--help"])
    assert rc == 0, f"archive-sync --help still returns {rc} (regression)"