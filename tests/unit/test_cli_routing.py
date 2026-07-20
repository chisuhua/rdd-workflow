"""Unit tests for ``skills._lib.cli`` subcommand routing and project-root resolution.

Covers:
  - ``cli.route()``: subcommand -> handler dispatch for dashboard/status/sessions
  - ``cli.list_commands()``: registry contents
  - ``cli.__main__.resolve_project_root()``: worktree-safe git root resolution
  - ``cli.__main__._is_in_worktree()``: linked-worktree detection

The routing tests stub handler modules in ``sys.modules`` so that the lazy
import inside ``route()`` resolves to a fake callable - we verify the dispatch
plumbing, not the handler output formatting (those have their own test files).

The path-resolution tests mock ``subprocess.run`` to simulate the various
``git rev-parse --git-common-dir`` outputs (relative ``.git``, worktree path,
timeout) without requiring an actual worktree to exist on disk.
"""
from __future__ import annotations

import os
import subprocess
import sys
import types

import pytest

from skills._lib.cli import list_commands, route
from skills._lib.cli import __main__ as cli_main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_fake_handler(module_name: str, func_name: str, return_value: int = 0):
    """Register a fake handler module in ``sys.modules`` and return its callable.

    The lazy import inside ``route()`` does ``importlib.import_module(module_path)``
    then ``getattr(module, func_name)``. By pre-registering a synthetic module
    under the target name, we short-circuit the import and let us assert that
    the right handler was reached with the right args.
    """
    fake_module = types.ModuleType(module_name)
    calls: list[list[str]] = []

    def _handler(args: list[str]) -> int:
        calls.append(list(args))
        return return_value

    _handler.calls = calls  # type: ignore[attr-defined]
    setattr(fake_module, func_name, _handler)
    sys.modules[module_name] = fake_module
    return _handler


@pytest.fixture
def fake_dashboard_handler():
    """Stub ``skills._lib.cli.dashboard_cmd:cmd_dashboard``."""
    yield _make_fake_handler(
        "skills._lib.cli.dashboard_cmd", "cmd_dashboard", return_value=0
    )
    sys.modules.pop("skills._lib.cli.dashboard_cmd", None)


@pytest.fixture
def fake_status_handler():
    """Stub ``skills._lib.cli.status_cmd:cmd_status``."""
    yield _make_fake_handler(
        "skills._lib.cli.status_cmd", "cmd_status", return_value=0
    )
    sys.modules.pop("skills._lib.cli.status_cmd", None)


@pytest.fixture
def fake_sessions_handler():
    """Stub ``skills._lib.cli.sessions_cmd:cmd_sessions``."""
    yield _make_fake_handler(
        "skills._lib.cli.sessions_cmd", "cmd_sessions", return_value=0
    )
    sys.modules.pop("skills._lib.cli.sessions_cmd", None)


# ---------------------------------------------------------------------------
# list_commands()
# ---------------------------------------------------------------------------


def test_list_commands_returns_sorted_list():
    """list_commands() returns a sorted list of registered subcommand names."""
    cmds = list_commands()
    assert isinstance(cmds, list)
    assert cmds == sorted(cmds), "list_commands() output must be sorted"


def test_list_commands_contains_dashboard_status_sessions():
    """The three documented subcommands are all registered."""
    cmds = list_commands()
    assert "dashboard" in cmds
    assert "status" in cmds
    assert "sessions" in cmds


# ---------------------------------------------------------------------------
# route() - happy paths
# ---------------------------------------------------------------------------


def test_route_dashboard_returns_handler_exit_code(fake_dashboard_handler):
    """routing 'dashboard' invokes cmd_dashboard and returns its exit code."""
    rc = route("dashboard", ["--json"])
    assert rc == 0
    assert fake_dashboard_handler.calls == [["--json"]]


def test_route_status_invokes_status_handler(fake_status_handler):
    """routing 'status' invokes cmd_status with the forwarded args."""
    rc = route("status", ["--iteration"])
    assert rc == 0
    assert fake_status_handler.calls == [["--iteration"]]


def test_route_sessions_invokes_sessions_handler(fake_sessions_handler):
    """routing 'sessions' invokes cmd_sessions with the forwarded args."""
    rc = route("sessions", ["show", "rds_abc123"])
    assert rc == 0
    assert fake_sessions_handler.calls == [["show", "rds_abc123"]]


def test_route_forwards_empty_args(fake_dashboard_handler):
    """route() passes an empty args list through to the handler unchanged."""
    rc = route("dashboard", [])
    assert rc == 0
    assert fake_dashboard_handler.calls == [[]]


def test_route_propagates_nonzero_exit_code():
    """A handler returning non-zero propagates through route() unchanged."""
    _make_fake_handler(
        "skills._lib.cli.dashboard_cmd", "cmd_dashboard", return_value=42
    )
    try:
        rc = route("dashboard", [])
        assert rc == 42
    finally:
        sys.modules.pop("skills._lib.cli.dashboard_cmd", None)


# ---------------------------------------------------------------------------
# route() - error paths
# ---------------------------------------------------------------------------


def test_route_unknown_command_raises_keyerror():
    """An unknown subcommand raises KeyError (per the docstring contract)."""
    with pytest.raises(KeyError):
        route("nonexistent-command", [])


def test_route_unknown_command_keyerror_carries_name():
    """The KeyError's first arg is the unknown subcommand name (so callers
    can print a friendly message like ``unknown command: <name>``)."""
    with pytest.raises(KeyError) as exc_info:
        route("bogus", [])
    assert exc_info.value.args[0] == "bogus"


def test_route_empty_string_raises_keyerror():
    """Empty-string subcommand is not in _ROUTES and raises KeyError."""
    with pytest.raises(KeyError):
        route("", [])


def test_route_none_subcommand_raises_keyerror():
    """None is not a valid key (and would otherwise TypeError on dict lookup)."""
    with pytest.raises((KeyError, TypeError)):
        route(None, [])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# route() - help / -h (these are handled by __main__.main, NOT route()).
# Verify that route() itself does NOT special-case 'help' or '-h'.
# ---------------------------------------------------------------------------


def test_route_does_not_special_case_help():
    """``help`` / ``-h`` are handled by ``__main__.main`` before route() is
    called; route() itself should treat them as unknown subcommands."""
    with pytest.raises(KeyError):
        route("help", [])
    with pytest.raises(KeyError):
        route("-h", [])


def test_main_help_flag_returns_zero(capsys):
    """``main(['help'])`` / ``main(['-h'])`` / ``main(['--help'])`` / ``main([])``
    all print help to stdout and return 0 without invoking any handler."""
    for argv in ([], ["help"], ["-h"], ["--help"]):
        rc = cli_main.main(argv)
        assert rc == 0, f"main({argv!r}) should return 0"
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower() or "subcommands" in captured.out.lower()


def test_main_unknown_command_returns_two(capsys):
    """``main(['bogus'])`` returns exit code 2 and prints to stderr."""
    rc = cli_main.main(["bogus"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "unknown command" in captured.err.lower()
    assert "bogus" in captured.err


# ---------------------------------------------------------------------------
# resolve_project_root() - real git repo (this test file lives in one)
# ---------------------------------------------------------------------------


def test_resolve_project_root_in_real_git_repo_returns_valid_path():
    """When run inside an actual git repo (the project itself), the returned
    path is an absolute directory containing a ``.git`` entry (file or dir)."""
    root = cli_main.resolve_project_root()
    assert os.path.isabs(root), "resolve_project_root() must return absolute path"
    assert os.path.isdir(root), f"resolved root must exist: {root}"
    git_path = os.path.join(root, ".git")
    assert os.path.exists(git_path), (
        f"resolved root must contain .git (file or dir), got: {root}"
    )


# ---------------------------------------------------------------------------
# resolve_project_root() - mocked subprocess.run cases
# ---------------------------------------------------------------------------


def _mock_completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    """Build a CompletedProcess with the given stdout (stderr empty)."""
    return subprocess.CompletedProcess(
        args=["git", "rev-parse", "--git-common-dir"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


def test_resolve_project_root_relative_dotgit(monkeypatch, tmp_path):
    """When ``git rev-parse --git-common-dir`` returns the relative ``.git``
    (the typical output when run from the repo root), the resolved root is
    the absolute path of the cwd."""
    monkeypatch.chdir(tmp_path)

    def fake_run(cmd, *args, **kwargs):
        assert cmd == ["git", "rev-parse", "--git-common-dir"]
        return _mock_completed(".git\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    root = cli_main.resolve_project_root()
    assert root == str(tmp_path)


def test_resolve_project_root_absolute_dotgit(monkeypatch, tmp_path):
    """When git returns an absolute ``<main>/.git`` path, we strip the
    trailing ``/.git`` and return the parent directory."""
    main_root = tmp_path / "main-repo"
    main_root.mkdir()
    git_dir = main_root / ".git"

    def fake_run(cmd, *args, **kwargs):
        return _mock_completed(f"{git_dir}\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    root = cli_main.resolve_project_root()
    assert os.path.abspath(root) == os.path.abspath(str(main_root))


def test_resolve_project_root_worktree_path(monkeypatch, tmp_path):
    """When run inside a linked worktree, ``--git-common-dir`` returns
    ``<main>/.git/worktrees/<name>``; we strip back 3 levels to recover
    the main repo root."""
    main_root = tmp_path / "main-repo"
    main_root.mkdir()
    common_dir = main_root / ".git" / "worktrees" / "feature-x"

    def fake_run(cmd, *args, **kwargs):
        return _mock_completed(f"{common_dir}\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    root = cli_main.resolve_project_root()
    assert os.path.abspath(root) == os.path.abspath(str(main_root))


def test_resolve_project_root_worktree_path_with_trailing_slash(monkeypatch, tmp_path):
    """Trailing slash on the worktree common-dir path should still resolve
    correctly (os.path.abspath normalizes it)."""
    main_root = tmp_path / "main-repo"
    main_root.mkdir()
    common_dir = main_root / ".git" / "worktrees" / "feature-y"

    def fake_run(cmd, *args, **kwargs):
        return _mock_completed(f"{common_dir}/\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    root = cli_main.resolve_project_root()
    assert os.path.abspath(root) == os.path.abspath(str(main_root))


def test_resolve_project_root_timeout_falls_back_to_cwd(monkeypatch, tmp_path):
    """If ``git rev-parse`` times out, resolve_project_root() falls back to
    os.getcwd() rather than raising."""
    monkeypatch.chdir(tmp_path)

    def fake_run(cmd, *args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=10)

    monkeypatch.setattr(subprocess, "run", fake_run)
    root = cli_main.resolve_project_root()
    assert root == str(tmp_path)


def test_resolve_project_root_git_not_installed_falls_back_to_cwd(monkeypatch, tmp_path):
    """If ``git`` binary is missing (FileNotFoundError), fall back to cwd."""
    monkeypatch.chdir(tmp_path)

    def fake_run(cmd, *args, **kwargs):
        raise FileNotFoundError("git binary not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    root = cli_main.resolve_project_root()
    assert root == str(tmp_path)


def test_resolve_project_root_nonzero_returncode_falls_back_to_cwd(monkeypatch, tmp_path):
    """If git exits non-zero (e.g. cwd is not inside a repo), fall back to cwd."""
    monkeypatch.chdir(tmp_path)

    def fake_run(cmd, *args, **kwargs):
        return _mock_completed("", returncode=128)

    monkeypatch.setattr(subprocess, "run", fake_run)
    root = cli_main.resolve_project_root()
    assert root == str(tmp_path)


def test_resolve_project_root_empty_stdout_falls_back_to_cwd(monkeypatch, tmp_path):
    """If git prints empty stdout (returncode 0 but no path), fall back to cwd."""
    monkeypatch.chdir(tmp_path)

    def fake_run(cmd, *args, **kwargs):
        return _mock_completed("\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    root = cli_main.resolve_project_root()
    assert root == str(tmp_path)


# ---------------------------------------------------------------------------
# _is_in_worktree()
# ---------------------------------------------------------------------------


def test_is_in_worktree_false_in_main_repo(monkeypatch, tmp_path):
    """In the main repo, ``--git-common-dir`` and ``--git-dir`` return the
    same path, so _is_in_worktree() returns False."""
    main_root = tmp_path / "main-repo"
    main_root.mkdir()
    git_dir = main_root / ".git"

    def fake_run(cmd, *args, **kwargs):
        if "--git-common-dir" in cmd:
            return _mock_completed(f"{git_dir}\n")
        if "--git-dir" in cmd:
            return _mock_completed(f"{git_dir}\n")
        raise AssertionError(f"unexpected git invocation: {cmd}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert cli_main._is_in_worktree() is False


def test_is_in_worktree_true_in_linked_worktree(monkeypatch, tmp_path):
    """In a linked worktree, ``--git-common-dir`` returns ``<main>/.git``
    while ``--git-dir`` returns ``<main>/.git/worktrees/<name>``. The two
    differ, so _is_in_worktree() returns True."""
    main_root = tmp_path / "main-repo"
    main_root.mkdir()
    common = main_root / ".git"
    git_dir = main_root / ".git" / "worktrees" / "feat"

    def fake_run(cmd, *args, **kwargs):
        if "--git-common-dir" in cmd:
            return _mock_completed(f"{common}\n")
        if "--git-dir" in cmd:
            return _mock_completed(f"{git_dir}\n")
        raise AssertionError(f"unexpected git invocation: {cmd}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert cli_main._is_in_worktree() is True


def test_is_in_worktree_false_on_timeout(monkeypatch):
    """If both git calls time out, _is_in_worktree() returns False (safe default)."""

    def fake_run(cmd, *args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=10)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert cli_main._is_in_worktree() is False


def test_is_in_worktree_false_on_git_missing(monkeypatch):
    """If git is not installed, _is_in_worktree() returns False."""

    def fake_run(cmd, *args, **kwargs):
        raise FileNotFoundError("git binary not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert cli_main._is_in_worktree() is False


def test_is_in_worktree_false_on_nonzero_returncode(monkeypatch):
    """If git exits non-zero (not in a repo), _is_in_worktree() returns False."""

    def fake_run(cmd, *args, **kwargs):
        return _mock_completed("", returncode=128)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert cli_main._is_in_worktree() is False
