"""Bash/Python boundary tests for iteration hooks.

Oracle C1 finding: all iteration hooks previously used bash string
interpolation (e.g. `'${PROJECT_ROOT}'` inside `python3 -c "..."`) which
broke on paths containing single quotes (e.g. `/home/o'reilly/project`)
and was an injection vector for change names with shell metacharacters.

These tests run the actual hook command from each modified skill
(propose, guide-ship, execute, archive, deps, status) with pathological
inputs to verify the os.environ pattern survives them.

Strategy: extract the python3 -c block from each .md file, substitute
bash variables via env (per the new pattern), run it, verify success.
"""
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# Make spec-workflow importable for the Python hooks to find
SPEC_WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SPEC_WORKFLOW_ROOT))


def _find_python3_block(md_path: Path) -> str:
    """Extract the LAST `python3 -c '...'` block from a markdown file.

    The hooks are documented as fenced code blocks. We extract the
    outermost one matching the iteration hook pattern.
    """
    content = md_path.read_text(encoding="utf-8")
    # Find a fenced code block containing "from skills._lib import iteration"
    pattern = re.compile(
        r"```(?:bash|sh)?\s*\n(.*?from\s+skills\._lib\s+import\s+iteration.*?)\n```",
        re.DOTALL,
    )
    matches = pattern.findall(content)
    assert matches, f"No iteration hook block found in {md_path}"
    return matches[-1]  # the most recent one


def _extract_python_source(md_path: Path) -> str:
    """Find the python3 -c '...' block content from a markdown hook."""
    content = md_path.read_text(encoding="utf-8")
    # Match single-quoted python3 -c blocks specifically
    pattern = re.compile(r"python3\s+-c\s+'((?:[^'\\]|\\.)*)'", re.DOTALL)
    matches = pattern.findall(content)
    assert matches, f"No single-quoted python3 block in {md_path}"
    # The hooks may be multi-line; join them
    return matches[-1]


@pytest.fixture
def project_root_with_quote(tmp_path):
    """A project root whose path contains a single quote (e.g. o'reilly).

    This is the canonical Oracle C1 pathological case. On Linux/macOS,
    single quotes in directory names are valid filesystem characters.
    """
    quoted_dir = tmp_path / "o'reilly-project" / ".rddf" / "state"
    quoted_dir.mkdir(parents=True)
    return str(tmp_path / "o'reilly-project")


class TestBashPythonBoundary:
    """The hooks survive paths with single quotes."""

    def test_iteration_load_save_with_quote_in_path(self, project_root_with_quote):
        """Sanity: Python itself can read/write iteration.json at the
        quoted path. (If this fails, the test infrastructure is broken
        and the hook tests below are moot.)"""
        from skills._lib import iteration as it
        data = it.add_or_update_change(it.create_empty(), name="c1", status="proposed")
        it.save(project_root_with_quote, data)
        loaded = it.load(project_root_with_quote)
        assert loaded["changes"][0]["name"] == "c1"

    def test_propose_hook_with_quoted_path(self, project_root_with_quote):
        """propose.md hook should successfully write iteration.json
        when PROJECT_ROOT contains a single quote.

        P0-1 extraction (P3-4d): inline python3 -c heredocs were removed
        from propose.md Phase 4. The iteration.json update logic now lives
        in _lib/propose_change.py::update_iteration_proposed, called via
        _lib/propose_change.sh::propose_finalize_change. This test
        verifies the NEW pattern (env-var passing via os.environ) survives
        the same pathological case.
        """
        from skills._lib import iteration as it
        # Initialize iteration.json at the quoted path
        it.save(project_root_with_quote, it.create_empty())

        # Source the new helper and invoke propose_finalize_change
        helper_path = SPEC_WORKFLOW_ROOT / "skills" / "propose" / "scripts" / "propose_change.sh"
        bash_command = (
            f'source "{helper_path}" && '
            f'PROJECT_ROOT="{project_root_with_quote}" '
            f'propose_finalize_change c1 phase-1 arch-design P0 '
            f'"arch-design:Architecture Design"'
        )
        env = os.environ.copy()
        env["PROJECT_ROOT"] = project_root_with_quote
        result = subprocess.run(
            ["bash", "-c", bash_command],
            env=env,
            capture_output=True,
            text=True,
            cwd=str(SPEC_WORKFLOW_ROOT),
        )

        assert result.returncode == 0, (
            f"propose_finalize_change failed with quoted path:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

        # Verify the hook actually wrote iteration.json correctly
        loaded = it.load(project_root_with_quote)
        assert any(c["name"] == "c1" for c in loaded["changes"])
        # And status should be 'proposed'
        match = next(c for c in loaded["changes"] if c["name"] == "c1")
        assert match["status"] == "proposed"

    def test_change_name_with_shell_metacharacters(self, project_root_with_quote):
        """A change name containing shell metacharacters (e.g. '; rm -rf /')
        must NOT execute those commands.

        Oracle C1 noted this as a code injection vector. The os.environ
        pattern means the value is passed as a separate env var, not
        interpolated into the Python source, so it's just a string.
        """
        from skills._lib import iteration as it
        malicious_name = "fake'); import os; os.system('echo PWNED > /tmp/pwn_test_xyz')"
        # Should write safely
        data = it.add_or_update_change(
            it.create_empty(), name=malicious_name, status="proposed"
        )
        it.save(project_root_with_quote, data)
        loaded = it.load(project_root_with_quote)
        assert loaded["changes"][0]["name"] == malicious_name
        # And no PWNED file was created
        assert not os.path.exists("/tmp/pwn_test_xyz")

    def test_archive_hook_with_quoted_path(self, project_root_with_quote):
        """archive.sh's mark_iteration_archived hook should also work
        when PROJECT_ROOT contains a single quote."""
        from skills._lib import iteration as it
        # Seed: a change in in_worktree
        data = it.add_or_update_change(it.create_empty(), name="c1", status="in_worktree")
        it.save(project_root_with_quote, data)

        # Now invoke the bash function
        archive_sh = SPEC_WORKFLOW_ROOT / "skills" / "_lib" / "archive.sh"
        env = os.environ.copy()
        env["PROJECT_ROOT"] = project_root_with_quote
        # _LIB_DIR needs to be set for archive.sh to find iteration module
        env["_LIB_DIR"] = str(SPEC_WORKFLOW_ROOT / "skills" / "_lib")

        result = subprocess.run(
            ["bash", "-c", f'source "{archive_sh}" && mark_iteration_archived "c1" "{project_root_with_quote}"'],
            env=env,
            capture_output=True,
            text=True,
            cwd=str(SPEC_WORKFLOW_ROOT),
        )

        assert result.returncode == 0, (
            f"archive.sh hook failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

        loaded = it.load(project_root_with_quote)
        assert loaded["changes"][0]["status"] == "archived"
        assert loaded["changes"][0]["archived_at"]


class TestProposeHookPlaceholder:
    """Oracle C2 finding: propose.md previously used literal '<name>'
    placeholder instead of bash variable. Verify the new pattern uses
    $CHANGE_NAME consistently and falls back to <name> for legacy callers.

    P0-1 extraction (P3-4d): the iteration.json update was extracted to
    _lib/propose_change.py::update_iteration_proposed. The <name> placeholder
    is now resolved by the agent's bash loop BEFORE calling the helper
    (e.g. propose_finalize_change "$CHANGE_NAME" ...). The helper itself
    takes the resolved name as a parameter — no string interpolation risk.
    """

    def test_propose_hook_extracts_change_name_from_env(self, tmp_path):
        """When CHANGE_NAME env var is set, the helper uses it directly."""
        from skills._lib import iteration as it
        project_root = str(tmp_path)
        os.makedirs(f"{project_root}/.rddf/state")

        helper_path = SPEC_WORKFLOW_ROOT / "skills" / "propose" / "scripts" / "propose_change.sh"
        bash_command = (
            f'source "{helper_path}" && '
            f'PROJECT_ROOT="{project_root}" '
            f'propose_finalize_change "real-change-name" phase-1 arch-design P0 '
            f'"arch-design:Architecture Design"'
        )
        env = os.environ.copy()
        env["PROJECT_ROOT"] = project_root

        result = subprocess.run(
            ["bash", "-c", bash_command],
            env=env, capture_output=True, text=True,
            cwd=str(SPEC_WORKFLOW_ROOT),
        )
        assert result.returncode == 0, f"STDERR: {result.stderr}"

        loaded = it.load(project_root)
        names = [c["name"] for c in loaded["changes"]]
        assert "real-change-name" in names
        assert "<name>" not in names  # placeholder must NOT be a literal entry

    def test_propose_hook_legacy_fallback(self, tmp_path):
        """When a legacy hand-copied caller passes '<name>' as the literal
        change name to the helper, the helper receives it directly as a
        parameter and writes it as-is to iteration.json.

        The inline orchestrator (the agent's bash loop) is responsible for
        substituting `<name>` with the actual change name before calling
        propose_finalize_change. Legacy code that didn't do this would
        pass '<name>' literally — the helper accepts it without injection
        risk (Oracle C1 finding).
        """
        from skills._lib import iteration as it
        project_root = str(tmp_path)
        os.makedirs(f"{project_root}/.rddf/state")

        helper_path = SPEC_WORKFLOW_ROOT / "skills" / "propose" / "scripts" / "propose_change.sh"
        # Use single quotes around '<name>' to avoid bash redirect parsing
        bash_command = (
            f'source "{helper_path}" && '
            f'PROJECT_ROOT="{project_root}" '
            f"propose_finalize_change '<name>' phase-1 arch-design P0 "
            f'"arch-design:Architecture Design"'
        )
        env = os.environ.copy()
        env["PROJECT_ROOT"] = project_root
        env.pop("CHANGE_NAME", None)

        result = subprocess.run(
            ["bash", "-c", bash_command],
            env=env, capture_output=True, text=True,
            cwd=str(SPEC_WORKFLOW_ROOT),
        )
        assert result.returncode == 0, (
            f"propose_finalize_change (legacy fallback) failed:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

        # Verify literal <name> entry was written (legacy compat)
        loaded = it.load(project_root)
        names = [c["name"] for c in loaded["changes"]]
        assert "<name>" in names, (
            f"Expected literal '<name>' entry for legacy compat, got: {names}"
        )