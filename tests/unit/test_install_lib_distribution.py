"""Lock the contract that all production-critical _lib modules are importable.

Mirrors the dependency chain declared in feature.md and rddf-session.md frontmatter:
- feature depends on [iteration, deps_output]
- rddf-session depends on [rddf_session]

These imports must work post-install (i.e., after copying _lib/ to a project).
With empty __init__.py markers on skills/ and skills/_lib/, the absolute
import `from skills._lib.X import Y` resolves as long as the project root is on
sys.path (which tests/conftest.py ensures for the test runtime).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_repo_root_on_path() -> None:
    """Mirror what install.sh would do: keep project root on sys.path."""
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


@pytest.fixture(autouse=True)
def _repo_root_on_path() -> None:
    _ensure_repo_root_on_path()


@pytest.mark.parametrize("module_name", [
    "skills._lib.iteration",
    "skills._lib.deps_output",
    "skills._lib.rddf_session",
    "skills._lib.state_vector",
    "skills._lib.event_log",
    "skills._lib.lock",
    "skills._lib.feature_view",
    "skills._lib.gate",
])
def test_lib_module_importable(module_name: str) -> None:
    """Each _lib module declared as a dependency MUST import without error."""
    importlib.import_module(module_name)


def test_lib_has_init_marker() -> None:
    assert (REPO_ROOT / "skills" / "__init__.py").exists(), (
        "skills/__init__.py must exist for skills to be a Python package"
    )
    assert (REPO_ROOT / "skills" / "_lib" / "__init__.py").exists(), (
        "skills/_lib/__init__.py must exist for skills._lib to be importable"
    )


def test_init_markers_are_empty_or_minimal() -> None:
    """__init__.py should be empty (or near-empty) — no side-effect imports."""
    for rel in ("skills/__init__.py", "skills/_lib/__init__.py"):
        text = (REPO_ROOT / rel).read_text()
        # Allow empty, docstring, or one-line comment; no import statements
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
        for ln in lines:
            assert not ln.startswith(("import ", "from ")), (
                f"{rel} contains a side-effect import: {ln!r}"
            )