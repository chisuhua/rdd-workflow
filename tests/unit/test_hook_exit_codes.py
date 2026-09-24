"""Regression test for the rddf_session_hook_* tail-return bash bug.

Per KNOWN_FAILURES.txt (pre-fix):
- `rddf_session_hook_heartbeat` (and close/attach/detach) used pattern:
    ```
    local _exit=$?
    [ "$_exit" -ne 0 ] && return "$_exit"
    ```
  When python heredoc exits 0 (success), `[ 0 -ne 0 ]` is FALSE; `[` exits 1;
  `&&` short-circuits; bash function returns the LAST command's exit, which
  is `[`'s 1. Net: hook fails with exit 1 on SUCCESS.

This test locks the fix (use `if [ ... ]; then return; fi` so the last
command is the test, which exits 0 on false).

Locks the bash fix in `rddf_session_hooks.sh` for: entry, heartbeat,
attach, detach (4 instances; close already used a different pattern
verified by inspection).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_SH = REPO_ROOT / "skills" / "rddf-session" / "scripts" / "rddf_session_hooks.sh"


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Fresh project_root + .rddf/state/ + git init (owner resolution needs it)."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=False)
    yield tmp_path


def _run_hook_bash(hook_name: str, *args: str, owner: str = "hb_owner") -> subprocess.CompletedProcess:
    """Run a hook via bash subprocess; inherit env + RDDF_OWNER."""
    env = os.environ.copy()
    env["OPENCODE_SESSION_ID"] = owner
    env["RDDF_OWNER"] = owner
    env["RDDF_OWNER_FROM"] = "shell-pid"
    cmd = ["bash", "-c",
           f'source "{HOOKS_SH}" && {hook_name} {" ".join(args)}']
    return subprocess.run(cmd, capture_output=True, text=True, env=env,
                         cwd=str(REPO_ROOT))


# --- The bug: bash tail-return leaks exit 1 on success ---

class TestHookExitCodesAreZeroOnSuccess:
    """All hooks should exit 0 when their operation succeeds (or fails loudly).

    Pre-fix: hooks returned exit 1 because of `[ ... -ne 0 ] && return`
    tail-return pattern; the bash function inherits the `[` test's exit
    code (1 for false condition).
    """

    def test_heartbeat_returns_0_after_entry(self, tmp_project):
        """entry + heartbeat: heartbeat should exit 0 (pre-fix it returned 1)."""
        entry = _run_hook_bash("rddf_session_hook_entry",
                               "stage_arch", "guide-arch", "subj", "ok",
                               owner="hb_test_1")
        assert entry.returncode == 0, (
            f"entry failed unexpectedly: stderr={entry.stderr!r}"
        )
        hb = _run_hook_bash("rddf_session_hook_heartbeat",
                            "stage_arch", owner="hb_test_1")
        assert hb.returncode == 0, (
            f"heartbeat should exit 0 on success (pre-fix bug: returned 1). "
            f"stdout={hb.stdout!r} stderr={hb.stderr!r}"
        )

    def test_attach_returns_0(self, tmp_project):
        """attach hook should exit 0 on success."""
        _run_hook_bash("rddf_session_hook_entry",
                       "stage_arch", "guide-arch", "subj", "ok",
                       owner="hb_test_attach")
        result = _run_hook_bash("rddf_session_hook_attach",
                                "stage_arch", "fake-change-name",
                                owner="hb_test_attach")
        # attach may legitimately fail if change doesn't exist; we only
        # assert NOT exit 1 from the bash tail bug. allow 0/2 (good +
        # change-missing are both fine).
        assert result.returncode in (0, 2), (
            f"attach should exit 0 (success) or 2 (change missing), not "
            f"{result.returncode} (pre-fix bug: returned 1). "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    def test_detach_returns_0(self, tmp_project):
        """detach hook should exit 0 on success."""
        _run_hook_bash("rddf_session_hook_entry",
                       "stage_arch", "guide-arch", "subj", "ok",
                       owner="hb_test_detach")
        result = _run_hook_bash("rddf_session_hook_detach",
                                "stage_arch", "fake-change-name",
                                owner="hb_test_detach")
        assert result.returncode in (0, 2), (
            f"detach should exit 0 or 2, not {result.returncode} "
            f"(pre-fix bug). stderr={result.stderr!r}"
        )

    def test_close_returns_0(self, tmp_project):
        """close hook should exit 0 on success."""
        entry = _run_hook_bash("rddf_session_hook_entry",
                               "stage_arch", "guide-arch", "subj", "ok",
                               owner="hb_test_close")
        assert entry.returncode == 0
        result = _run_hook_bash("rddf_session_hook_close",
                                "stage_arch", "ok", "guide-arch",
                                owner="hb_test_close")
        assert result.returncode == 0, (
            f"close should exit 0 on success (pre-fix bug: returned 1). "
            f"stderr={result.stderr!r}"
        )


# --- Source-level: confirm the fix is in place (defensive regression) ---

class TestTailReturnPatternFixed:
    """The old buggy pattern must not appear anywhere in the file."""

    BUGGY_PATTERN = '[ "$_exit" -ne 0 ] && return "$_exit"'

    def test_no_buggy_tail_return_pattern(self):
        text = HOOKS_SH.read_text()
        assert self.BUGGY_PATTERN not in text, (
            f"Buggy tail-return pattern found in {HOOKS_SH.name}. "
            f"Replace with `if [ ... ]; then return; fi` so the LAST "
            f"command (the test) exits 0 on the false branch."
        )

    def test_at_least_four_if_return_patterns(self):
        """4 hooks (entry / heartbeat / attach / detach) should use the
        fixed `if [ ... ]; then return; fi` pattern."""
        text = HOOKS_SH.read_text()
        count = text.count('if [ "$_exit" -ne 0 ]; then')
        assert count >= 4, (
            f"Expected ≥4 `if` patterns (entry/heartbeat/attach/detach), "
            f"found {count}. Verify the fix is applied to all hooks."
        )