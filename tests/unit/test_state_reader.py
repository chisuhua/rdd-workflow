"""Unit tests for skills/_lib/state_reader.py - shared read-only data layer.

TDD contract: these tests lock the read-only behavior of every public
function in state_reader.py. Downstream consumers (guide recommender,
status CLI, feature CLI, guide-arch/plan/ship intake phases) depend on
this contract:

  - All scalar/dict readers return ``None`` on missing/corrupt input.
  - All list readers return ``[]`` on missing/corrupt input.
  - **Read-only guarantee**: no function ever writes, renames, or
    backs up any file. In particular, ``read_iteration`` must NOT
    create a ``.corrupt.<ts>`` backup file (unlike ``iteration.load``).
  - ``list_worktrees`` and ``list_change_dirs`` never raise.
"""
import json
import os
import subprocess

import pytest

from skills._lib import state_reader
from skills._lib.iteration import store as iteration_store


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path):
    """A fresh project root with .rddf/state/ pre-created."""
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    return str(tmp_path)


@pytest.fixture
def state_dir(project_root):
    """The .rddf/state/ directory path under project_root."""
    return os.path.join(project_root, ".rddf", "state")


def _write_json(path: str, data) -> None:
    """Write ``data`` as JSON to ``path`` (creating parent dirs if needed)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _corrupt_backup_files(state_dir: str) -> list:
    """Return list of corrupt-backup files (``*.corrupt.<ts>``) in state_dir."""
    if not os.path.isdir(state_dir):
        return []
    return [f for f in os.listdir(state_dir) if ".corrupt." in f]


def _make_valid_iteration(phase: str = "default") -> dict:
    """Build a minimal valid v5 iteration dict (passes schema validation)."""
    return {
        "version": 5,
        "updated_at": "2026-07-21T00:00:00+00:00",
        "current_phase": phase,
        "changes": [
            {
                "name": "feature-x",
                "status": "proposed",
                "added_at": "2026-07-21T00:00:00+00:00",
                "phase": phase,
            }
        ],
    }


# ---------------------------------------------------------------------------
# read_arch_handoff
# ---------------------------------------------------------------------------

class TestReadArchHandoff:
    def test_returns_dict_when_present(self, project_root, state_dir):
        path = os.path.join(state_dir, ".arch-handoff.json")
        _write_json(path, {"version": 1, "adr_dir": "docs/adr"})

        result = state_reader.read_arch_handoff(project_root)

        assert result is not None
        assert result["version"] == 1
        assert result["adr_dir"] == "docs/adr"

    def test_returns_none_when_missing(self, project_root):
        # No file written - state dir is empty
        assert state_reader.read_arch_handoff(project_root) is None

    def test_returns_none_on_corrupt_json(self, project_root, state_dir):
        path = os.path.join(state_dir, ".arch-handoff.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{ not valid json")

        assert state_reader.read_arch_handoff(project_root) is None

    def test_returns_none_when_top_level_not_dict(self, project_root, state_dir):
        path = os.path.join(state_dir, ".arch-handoff.json")
        _write_json(path, ["not", "a", "dict"])

        assert state_reader.read_arch_handoff(project_root) is None


# ---------------------------------------------------------------------------
# read_plan_handoff
# ---------------------------------------------------------------------------

class TestReadPlanHandoff:
    def test_returns_dict_when_present(self, project_root, state_dir):
        path = os.path.join(state_dir, ".plan-handoff.json")
        _write_json(path, {"version": 1, "changes": ["c1"]})

        result = state_reader.read_plan_handoff(project_root)

        assert result is not None
        assert result["version"] == 1
        assert result["changes"] == ["c1"]

    def test_returns_none_when_missing(self, project_root):
        assert state_reader.read_plan_handoff(project_root) is None

    def test_returns_none_on_corrupt_json(self, project_root, state_dir):
        path = os.path.join(state_dir, ".plan-handoff.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("not json {{{")

        assert state_reader.read_plan_handoff(project_root) is None

    def test_returns_none_when_top_level_not_dict(self, project_root, state_dir):
        path = os.path.join(state_dir, ".plan-handoff.json")
        _write_json(path, "a string, not a dict")

        assert state_reader.read_plan_handoff(project_root) is None


# ---------------------------------------------------------------------------
# read_iteration
# ---------------------------------------------------------------------------

class TestReadIteration:
    """Critical contract: read_iteration must NEVER create a ``.corrupt.*``
    backup file, even when iteration.json is corrupt. This is the key
    difference from ``iteration.store.load`` (which DOES back up).
    """

    def test_returns_dict_when_valid_v4(self, project_root, state_dir):
        path = os.path.join(state_dir, "iteration.json")
        _write_json(path, _make_valid_iteration("v2.1"))

        result = state_reader.read_iteration(project_root)

        assert result is not None
        assert result["version"] == 5
        assert result["current_phase"] == "v2.1"
        assert len(result["changes"]) == 1
        assert result["changes"][0]["name"] == "feature-x"

    def test_returns_none_when_missing(self, project_root, state_dir):
        # File does not exist - read_unlocked returns None
        result = state_reader.read_iteration(project_root)

        assert result is None
        # No backup file should be created for a missing file
        assert _corrupt_backup_files(state_dir) == []

    def test_returns_none_on_corrupt_json_without_backup(self, project_root, state_dir):
        """Critical read-only contract: corrupt JSON must NOT create a backup."""
        path = os.path.join(state_dir, "iteration.json")
        original_content = "{ this is not valid json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(original_content)

        result = state_reader.read_iteration(project_root)

        assert result is None
        # The critical assertion: NO .corrupt.* file must exist
        backups = _corrupt_backup_files(state_dir)
        assert backups == [], (
            f"read_iteration created a corrupt backup (violates read-only contract): {backups}"
        )
        # The original file must remain untouched
        with open(path, encoding="utf-8") as f:
            assert f.read() == original_content

    def test_returns_none_on_schema_violation_without_backup(self, project_root, state_dir):
        """Critical: schema-invalid v4 file must NOT trigger a backup either."""
        path = os.path.join(state_dir, "iteration.json")
        original_content = json.dumps({"version": 999, "changes": []})  # invalid version
        with open(path, "w", encoding="utf-8") as f:
            f.write(original_content)

        result = state_reader.read_iteration(project_root)

        assert result is None
        assert _corrupt_backup_files(state_dir) == [], (
            "read_iteration created a backup on schema violation (read-only contract broken)"
        )

    def test_contrast_with_load_which_does_backup(self, project_root, state_dir):
        """Sanity check: iteration.store.load DOES create a backup on corrupt
        input, confirming that read_iteration's no-backup behavior is a
        deliberate departure (uses _read_unlocked instead of load).
        """
        path = os.path.join(state_dir, "iteration.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{ corrupt }")

        iteration_store.load(project_root)

        # load() creates a backup
        backups = _corrupt_backup_files(state_dir)
        assert len(backups) >= 1, "sanity check: load() should create a backup"


# ---------------------------------------------------------------------------
# read_sessions
# ---------------------------------------------------------------------------

class TestReadSessions:
    def test_returns_list_when_present(self, project_root, state_dir):
        path = os.path.join(state_dir, "sessions.json")
        _write_json(path, {
            "version": 1,
            "sessions": [
                {"id": "ses_1", "phase": "arch"},
                {"id": "ses_2", "phase": "plan"},
            ],
        })

        result = state_reader.read_sessions(project_root)

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "ses_1"
        assert result[1]["phase"] == "plan"

    def test_returns_empty_list_when_sessions_empty(self, project_root, state_dir):
        path = os.path.join(state_dir, "sessions.json")
        _write_json(path, {"version": 1, "sessions": []})

        result = state_reader.read_sessions(project_root)

        assert result is not None
        assert result == []

    def test_returns_none_when_missing(self, project_root):
        assert state_reader.read_sessions(project_root) is None

    def test_returns_none_on_corrupt_json(self, project_root, state_dir):
        path = os.path.join(state_dir, "sessions.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{ broken")

        assert state_reader.read_sessions(project_root) is None

    def test_returns_none_when_sessions_field_not_list(self, project_root, state_dir):
        """If the ``sessions`` field is present but not a list (e.g. a dict
        or string), return None rather than coercing."""
        path = os.path.join(state_dir, "sessions.json")
        _write_json(path, {"version": 1, "sessions": "not a list"})

        assert state_reader.read_sessions(project_root) is None

    def test_returns_none_when_sessions_field_missing(self, project_root, state_dir):
        """If the file is valid JSON dict but lacks the ``sessions`` field,
        return None (absent field is treated as invalid)."""
        path = os.path.join(state_dir, "sessions.json")
        _write_json(path, {"version": 1})  # no sessions key

        assert state_reader.read_sessions(project_root) is None

    def test_returns_none_when_top_level_not_dict(self, project_root, state_dir):
        path = os.path.join(state_dir, "sessions.json")
        _write_json(path, ["not", "a", "dict"])

        assert state_reader.read_sessions(project_root) is None


# ---------------------------------------------------------------------------
# read_roadmap_state
# ---------------------------------------------------------------------------

class TestReadRoadmapState:
    def test_returns_dict_when_present(self, project_root, state_dir):
        path = os.path.join(state_dir, "roadmap-state.json")
        _write_json(path, {"phases": {"v2.1": {"count": 3}}})

        result = state_reader.read_roadmap_state(project_root)

        assert result is not None
        assert result["phases"]["v2.1"]["count"] == 3

    def test_returns_none_when_missing(self, project_root):
        assert state_reader.read_roadmap_state(project_root) is None

    def test_returns_none_on_corrupt_json(self, project_root, state_dir):
        path = os.path.join(state_dir, "roadmap-state.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("not json {{{")

        assert state_reader.read_roadmap_state(project_root) is None

    def test_returns_none_when_top_level_not_dict(self, project_root, state_dir):
        path = os.path.join(state_dir, "roadmap-state.json")
        _write_json(path, 42)

        assert state_reader.read_roadmap_state(project_root) is None


# ---------------------------------------------------------------------------
# list_worktrees
# ---------------------------------------------------------------------------

class _FakeCompletedProcess:
    """Minimal stand-in for subprocess.CompletedProcess used by list_worktrees."""

    def __init__(self, stdout: str, stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


_PORCELAIN_OUTPUT = """\
worktree /home/user/project
branch refs/heads/main

worktree /home/user/project/.rddf/wt/feature-x
branch refs/heads/openspec/feature-x

worktree /home/user/project/.rddf/wt/hotfix-y
branch refs/heads/openspec/hotfix-y

worktree /home/user/project/.rddf/wt/detached
detached
"""


class TestListWorktrees:
    def test_returns_list_of_dicts(self, monkeypatch):
        monkeypatch.setattr(
            state_reader.subprocess, "run",
            lambda *a, **kw: _FakeCompletedProcess(_PORCELAIN_OUTPUT),
        )

        result = state_reader.list_worktrees()

        assert isinstance(result, list)
        assert len(result) == 4

    def test_each_entry_has_required_keys(self, monkeypatch):
        monkeypatch.setattr(
            state_reader.subprocess, "run",
            lambda *a, **kw: _FakeCompletedProcess(_PORCELAIN_OUTPUT),
        )

        result = state_reader.list_worktrees()

        for wt in result:
            assert "path" in wt
            assert "branch" in wt
            assert "is_openspec" in wt

    def test_main_worktree_is_not_openspec(self, monkeypatch):
        monkeypatch.setattr(
            state_reader.subprocess, "run",
            lambda *a, **kw: _FakeCompletedProcess(_PORCELAIN_OUTPUT),
        )

        result = state_reader.list_worktrees()

        main_wt = result[0]
        assert main_wt["path"] == "/home/user/project"
        assert main_wt["branch"] == "refs/heads/main"
        assert main_wt["is_openspec"] is False

    def test_openspec_worktree_detected(self, monkeypatch):
        monkeypatch.setattr(
            state_reader.subprocess, "run",
            lambda *a, **kw: _FakeCompletedProcess(_PORCELAIN_OUTPUT),
        )

        result = state_reader.list_worktrees()

        feature_wt = result[1]
        assert feature_wt["path"] == "/home/user/project/.rddf/wt/feature-x"
        assert feature_wt["branch"] == "refs/heads/openspec/feature-x"
        assert feature_wt["is_openspec"] is True

    def test_detached_worktree_has_none_branch(self, monkeypatch):
        """A detached-HEAD worktree has no ``branch`` line; the reader
        should leave ``branch`` as ``None`` and ``is_openspec`` as ``False``."""
        monkeypatch.setattr(
            state_reader.subprocess, "run",
            lambda *a, **kw: _FakeCompletedProcess(_PORCELAIN_OUTPUT),
        )

        result = state_reader.list_worktrees()

        detached_wt = result[3]
        assert detached_wt["path"] == "/home/user/project/.rddf/wt/detached"
        assert detached_wt["branch"] is None
        assert detached_wt["is_openspec"] is False

    def test_returns_empty_on_git_not_found(self, monkeypatch):
        """If git binary is not on PATH (FileNotFoundError), return []."""
        def _raise_fnf(*a, **kw):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(state_reader.subprocess, "run", _raise_fnf)

        assert state_reader.list_worktrees() == []

    def test_returns_empty_on_timeout(self, monkeypatch):
        """If subprocess times out, return [] (never raise)."""
        def _raise_timeout(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="git", timeout=10)

        monkeypatch.setattr(state_reader.subprocess, "run", _raise_timeout)

        assert state_reader.list_worktrees() == []

    def test_returns_empty_on_oserror(self, monkeypatch):
        def _raise_oserror(*a, **kw):
            raise OSError("permission denied")

        monkeypatch.setattr(state_reader.subprocess, "run", _raise_oserror)

        assert state_reader.list_worktrees() == []

    def test_handles_empty_output(self, monkeypatch):
        """If git returns no output (no worktrees), return an empty list."""
        monkeypatch.setattr(
            state_reader.subprocess, "run",
            lambda *a, **kw: _FakeCompletedProcess(""),
        )

        assert state_reader.list_worktrees() == []

    def test_handles_output_without_trailing_blank_line(self, monkeypatch):
        """Porcelain output without a trailing blank line must still flush
        the last record (the implementation explicitly handles this)."""
        no_trailing = (
            "worktree /home/user/project\n"
            "branch refs/heads/main\n"
        )  # no trailing \n\n
        monkeypatch.setattr(
            state_reader.subprocess, "run",
            lambda *a, **kw: _FakeCompletedProcess(no_trailing),
        )

        result = state_reader.list_worktrees()

        assert len(result) == 1
        assert result[0]["path"] == "/home/user/project"
        assert result[0]["is_openspec"] is False


# ---------------------------------------------------------------------------
# list_change_dirs
# ---------------------------------------------------------------------------

class TestListChangeDirs:
    def test_returns_sorted_list_excluding_archive(self, project_root):
        changes_dir = os.path.join(project_root, "openspec", "changes")
        # Create change dirs (out of order to test sorting)
        for name in ["zeta", "alpha", "mid"]:
            os.makedirs(os.path.join(changes_dir, name))
        # Create archive/ subdir (must be excluded)
        os.makedirs(os.path.join(changes_dir, "archive"))
        # Create a stray file (must be excluded - not a directory)
        with open(os.path.join(changes_dir, "stray.md"), "w") as f:
            f.write("not a dir")

        result = state_reader.list_change_dirs(project_root)

        assert result == ["alpha", "mid", "zeta"]
        assert "archive" not in result

    def test_returns_empty_when_changes_dir_missing(self, project_root):
        # openspec/changes/ doesn't exist
        assert state_reader.list_change_dirs(project_root) == []

    def test_returns_empty_when_changes_dir_empty(self, project_root):
        os.makedirs(os.path.join(project_root, "openspec", "changes"))

        assert state_reader.list_change_dirs(project_root) == []

    def test_returns_empty_when_only_archive_present(self, project_root):
        os.makedirs(os.path.join(project_root, "openspec", "changes", "archive"))

        assert state_reader.list_change_dirs(project_root) == []

    def test_excludes_files_but_includes_subdirs(self, project_root):
        changes_dir = os.path.join(project_root, "openspec", "changes")
        os.makedirs(os.path.join(changes_dir, "real-change"))
        # A README file should be excluded
        with open(os.path.join(changes_dir, "README.md"), "w") as f:
            f.write("docs")

        result = state_reader.list_change_dirs(project_root)

        assert result == ["real-change"]
