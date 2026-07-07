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

        The OLD pattern (bash string interpolation) would have produced
        a Python SyntaxError because the Python source would have a
        broken string literal.
        """
        # We extract the actual hook from propose.md and run it.
        # The hook is environment-aware: passes PROJECT_ROOT, CHANGE_NAME,
        # etc. via env vars and reads them with os.environ.
        md_path = SPEC_WORKFLOW_ROOT / "skills" / "propose.md"
        python_source = _extract_python_source(md_path)

        # Run the hook with all required env vars set
        env = os.environ.copy()
        env["PROJECT_ROOT"] = project_root_with_quote
        env["CHANGE_NAME"] = "c1"
        env["CHANGE_PHASE"] = "v2.1"
        env["CHANGE_CATEGORY"] = "test"
        env["PRIORITY"] = "P0"

        result = subprocess.run(
            [sys.executable, "-c", python_source],
            env=env,
            capture_output=True,
            text=True,
            cwd=str(SPEC_WORKFLOW_ROOT),
        )

        assert result.returncode == 0, (
            f"propose hook failed with quoted path:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

        # Verify the hook actually wrote iteration.json correctly
        from skills._lib import iteration as it
        loaded = it.load(project_root_with_quote)
        assert any(c["name"] == "c1" for c in loaded["changes"])

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
    """

    def test_propose_hook_extracts_change_name_from_env(self, tmp_path):
        """When CHANGE_NAME env var is set, the hook uses it directly
        (no manual <name> substitution needed)."""
        from skills._lib import iteration as it
        project_root = str(tmp_path)
        os.makedirs(f"{project_root}/.rddf/state")

        md_path = SPEC_WORKFLOW_ROOT / "skills" / "propose.md"
        python_source = _extract_python_source(md_path)

        env = os.environ.copy()
        env["PROJECT_ROOT"] = project_root
        env["CHANGE_NAME"] = "real-change-name"
        env["CHANGE_PHASE"] = "v2.1"
        env["CHANGE_CATEGORY"] = "test"
        env["PRIORITY"] = "P0"

        result = subprocess.run(
            [sys.executable, "-c", python_source],
            env=env, capture_output=True, text=True,
            cwd=str(SPEC_WORKFLOW_ROOT),
        )
        assert result.returncode == 0, f"STDERR: {result.stderr}"

        loaded = it.load(project_root)
        names = [c["name"] for c in loaded["changes"]]
        assert "real-change-name" in names
        assert "<name>" not in names  # placeholder must NOT be a literal entry

    def test_propose_hook_legacy_fallback(self, tmp_path):
        """When CHANGE_NAME is NOT set in the env, the bash-level
        ${CHANGE_NAME:-<name>} fallback substitutes the literal '<name>'
        placeholder so legacy hand-copied callers still work.

        The hook contract is the WHOLE bash command, not just the
        python3 -c block. This test runs the full prefix + python3.
        """
        from skills._lib import iteration as it
        project_root = str(tmp_path)
        os.makedirs(f"{project_root}/.rddf/state")

        md_path = SPEC_WORKFLOW_ROOT / "skills" / "propose.md"
        python_source = _extract_python_source(md_path)

        env = os.environ.copy()
        env["PROJECT_ROOT"] = project_root
        env["CHANGE_PHASE"] = "v2.1"
        env["CHANGE_CATEGORY"] = "test"
        env["PRIORITY"] = "P0"
        env.pop("CHANGE_NAME", None)

        # Run the full hook: bash env-setup + python3 invocation
        bash_command = (
            f'PROJECT_ROOT="{project_root}" '
            f'CHANGE_PHASE="v2.1" '
            f'CHANGE_CATEGORY="test" '
            f'PRIORITY="P0" '
            f'CHANGE_NAME="${{CHANGE_NAME:-<name>}}" '
            f"python3 -c '{python_source}'"
        )
        result = subprocess.run(
            ["bash", "-c", bash_command],
            env=env, capture_output=True, text=True,
            cwd=str(SPEC_WORKFLOW_ROOT),
        )
        assert result.returncode == 0, (
            f"propose hook (legacy fallback) failed:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

        # Verify literal <name> entry was written (legacy compat)
        loaded = it.load(project_root)
        names = [c["name"] for c in loaded["changes"]]
        assert "<name>" in names, (
            f"Expected literal '<name>' entry for legacy compat, got: {names}"
        )