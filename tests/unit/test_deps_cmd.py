"""Unit tests for ``skills._lib.cli.deps_cmd`` cross-repo sub-dispatch.

fix-cli-routing-cross-repo-commands: ``rddf deps cross-repo [--spokes ...]``
must dispatch to the cross-repo handler (``cmd_deps_cross_repo``) instead of
silently rendering the regular deps-analysis table. The plain ``rddf deps``
path must remain untouched (existing regression).
"""
from __future__ import annotations

import skills._lib.cli.deps_cmd as deps_cmd


def test_cmd_deps_cross_repo_dispatches_with_remaining_args(monkeypatch):
    """``cmd_deps(['cross-repo', ...])`` forwards the remaining args to
    ``cmd_deps_cross_repo`` and propagates its exit code."""
    calls: list[list[str]] = []

    def _fake(args: list[str]) -> int:
        calls.append(list(args))
        return 0

    monkeypatch.setattr(deps_cmd, "cmd_deps_cross_repo", _fake)
    rc = deps_cmd.cmd_deps(["cross-repo", "--spokes", "org/foo,org/bar"])
    assert rc == 0
    assert calls == [["--spokes", "org/foo,org/bar"]]


def test_cmd_deps_cross_repo_help_dispatches(monkeypatch):
    """``cmd_deps(['cross-repo', '--help'])`` reaches the cross-repo handler
    (which prints the cross-repo usage, not the deps table)."""
    calls: list[list[str]] = []

    def _fake(args: list[str]) -> int:
        calls.append(list(args))
        return 0

    monkeypatch.setattr(deps_cmd, "cmd_deps_cross_repo", _fake)
    rc = deps_cmd.cmd_deps(["cross-repo", "--help"])
    assert rc == 0
    assert calls == [["--help"]]


def test_cmd_deps_without_cross_repo_does_not_dispatch(monkeypatch, tmp_path):
    """Plain ``rddf deps`` (no ``cross-repo`` first arg) must NOT dispatch —
    existing table behavior is preserved."""
    def _boom(args: list[str]) -> int:
        raise AssertionError("cmd_deps_cross_repo must not be called")

    monkeypatch.setattr(deps_cmd, "cmd_deps_cross_repo", _boom)
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    # No deps-analysis.json in tmp_path → prints the "不存在" hint, exit 0.
    rc = deps_cmd.cmd_deps([])
    assert rc == 0
