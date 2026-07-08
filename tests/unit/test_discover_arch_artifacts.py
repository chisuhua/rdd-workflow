"""Unit tests for skills/_lib/discover-arch-artifacts.sh (ADR-0016 Layer 1).

Tests rely on subprocess driving the shell script because:
- Bash globals across `$(...)` have propagation gotchas (Momus CRITICAL#2)
- The library is sourced-only, not directly importable
- All actual discovery runs through bash

Each test creates an isolated fixture under /tmp and invokes the script
via subprocess so globals (DISCOVERED_*) can be observed in stdout.
"""
import os
import subprocess
import textwrap
from pathlib import Path

DISCOVER_SH = (
    Path(__file__).resolve().parent.parent.parent
    / "skills"
    / "_lib"
    / "discover-arch-artifacts.sh"
)
TMP_ROOT = Path("/tmp/adr_discover_test")


def _make_fixture(name: str) -> Path:
    """Create a unique fixture under /tmp/<random>/<name>.

    Uses a unique root per test invocation (pid + nanoseconds) so concurrent
    tests don't share the same directory and stale fixtures don't accumulate.
    """
    import time
    root = TMP_ROOT / f"{os.getpid()}_{int(time.time() * 1000000)}_{name}"
    root.mkdir(parents=True, exist_ok=False)
    return root


def _run_in_subshell(project_root: Path, function: str, env_extra: dict | None = None) -> tuple[int, str, str, dict]:
    """Run a discover function in a subshell with controlled env.

    Returns (returncode, stdout, stderr, env_after).

    The script is sourced and the function is invoked. Globals are
    introspected by `declare -p` after invocation.
    """
    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(project_root)
    # Unset all relevant SPEC_WORKFLOW_* vars to start clean
    for var in ["SPEC_WORKFLOW_ADR_DIR", "SPEC_WORKFLOW_ROADMAP_PATH",
                "SPEC_WORKFLOW_ARCHITECTURE_DIR", "SPEC_WORKFLOW_ADR_PATTERN"]:
        env.pop(var, None)
    if env_extra:
        env.update(env_extra)

    cmd = textwrap.dedent(f"""
        set +e
        cd "{project_root}"
        source "{DISCOVER_SH}"
        {function} >/dev/null
        declare -p | grep -E '^(declare|export) [^=]*DISCOVERED_'
        echo "---RESULT---"
        {function}
    """)
    proc = subprocess.run(
        ["bash", "-c", cmd],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.returncode, proc.stdout, proc.stderr, env


def test_discover_adr_dir_returns_default_when_nothing_found():
    """When no candidate exists, return 'docs/adr' as convention default."""
    p = _make_fixture("default_repo")
    rc, out, err, _ = _run_in_subshell(p, "discover_adr_dir")
    result = out.split("---RESULT---")[-1].strip()
    assert result == "docs/adr", f"Expected docs/adr, got [{result}]"


def test_discover_adr_dir_finds_first_candidate():
    """When 'docs/adr' exists, return it (highest priority)."""
    p = _make_fixture("first_candidate")
    (p / "docs" / "adr").mkdir(parents=True)
    rc, out, err, _ = _run_in_subshell(p, "discover_adr_dir")
    result = out.split("---RESULT---")[-1].strip()
    assert result == "docs/adr", f"Expected docs/adr, got [{result}]"


def test_discover_adr_dir_finds_alternative_layout():
    """When 'docs/adr' missing but 'doc/adr' exists, return 'doc/adr'."""
    p = _make_fixture("alt_layout")
    (p / "doc" / "adr").mkdir(parents=True)
    rc, out, err, _ = _run_in_subshell(p, "discover_adr_dir")
    result = out.split("---RESULT---")[-1].strip()
    assert result == "doc/adr", f"Expected doc/adr, got [{result}]"


def test_discover_roadmap_returns_default_when_missing():
    """Roadmap fallback to 'roadmap.md' root."""
    p = _make_fixture("missing_roadmap")
    rc, out, err, _ = _run_in_subshell(p, "discover_roadmap")
    result = out.split("---RESULT---")[-1].strip()
    assert result == "roadmap.md", f"Expected roadmap.md, got [{result}]"


def test_discover_roadmap_finds_alternative_layout():
    """Find roadmap in planning/ when root missing."""
    p = _make_fixture("alt_roadmap")
    (p / "planning").mkdir()
    (p / "planning" / "roadmap.md").touch()
    rc, out, err, _ = _run_in_subshell(p, "discover_roadmap")
    result = out.split("---RESULT---")[-1].strip()
    assert result == "planning/roadmap.md", f"Expected planning/roadmap.md, got [{result}]"


def test_discover_architecture_dir_returns_default_when_missing():
    """Architecture fallback to 'docs/architecture'."""
    p = _make_fixture("missing_arch")
    rc, out, err, _ = _run_in_subshell(p, "discover_architecture_dir")
    result = out.split("---RESULT---")[-1].strip()
    assert result == "docs/architecture", f"Expected docs/architecture, got [{result}]"


def test_discover_adr_pattern_returns_default():
    """Default pattern is 'ADR-*.md'."""
    p = _make_fixture("default_pattern")
    rc, out, err, _ = _run_in_subshell(p, "discover_adr_pattern")
    result = out.split("---RESULT---")[-1].strip()
    assert result == "ADR-*.md", f"Expected ADR-*.md, got [{result}]"


def test_env_var_override_takes_precedence():
    """SPEC_WORKFLOW_ADR_DIR env var beats all candidates (Momus CRITICAL#1)."""
    p = _make_fixture("env_test")
    (p / "docs" / "adr").mkdir(parents=True)
    # env var points to NON-EXISTENT path; should still win
    rc, out, err, _ = _run_in_subshell(
        p, "discover_adr_dir",
        env_extra={"SPEC_WORKFLOW_ADR_DIR": "custom/adrs"},
    )
    result = out.split("---RESULT---")[-1].strip()
    assert result == "custom/adrs", (
        f"Env var override failed: expected custom/adrs, got [{result}]"
    )


def test_discover_adr_pattern_via_env_var():
    """SPEC_WORKFLOW_ADR_PATTERN env var overrides pattern."""
    p = _make_fixture("env_pattern")
    rc, out, err, _ = _run_in_subshell(
        p, "discover_adr_pattern",
        env_extra={"SPEC_WORKFLOW_ADR_PATTERN": "DEC-*.md"},
    )
    result = out.split("---RESULT---")[-1].strip()
    assert result == "DEC-*.md", f"Expected DEC-*.md, got [{result}]"


def test_globals_propagated_to_caller_shell():
    """DISCOVERED_*_FOUND and DISCOVERED_*_TRIED must be visible in caller's shell
    (Momus CRITICAL#2 — used to be lost via $(...) subshell propagation).
    """
    p = _make_fixture("globals_test")
    (p / "docs" / "adr").mkdir(parents=True)
    rc, out, err, _ = _run_in_subshell(p, "discover_adr_dir")
    # Strip the result line, look at declare -p output
    declare_output = out.split("---RESULT---")[0]
    assert 'DISCOVERED_ADR_DIR_FOUND="true"' in declare_output, (
        f"Expected DISCOVERED_ADR_DIR_FOUND=\"true\" in declare output: {declare_output}"
    )
    assert 'DISCOVERED_ADR_DIR_TRIED="1"' in declare_output, (
        f"Expected DISCOVERED_ADR_DIR_TRIED=\"1\" in declare output: {declare_output}"
    )
    assert 'DISCOVERED_ADR_DIR="docs/adr"' in declare_output, (
        f"Expected DISCOVERED_ADR_DIR=\"docs/adr\" in declare output: {declare_output}"
    )
