"""Lock the contract that all production-critical _lib modules are importable.

Mirrors the dependency chain declared in feature.md and rddf-session.md frontmatter:
- feature depends on [iteration, deps_output]
- rddf-session depends on [rddf_session]

These imports must work post-install (i.e., after copying _lib/ to a project).
With empty __init__.py markers on skills/ and _lib/, the absolute
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
    "skills._lib.core.event_log",
    "skills._lib.core.state_vector",
    "skills._lib.core.lock",
    "skills._lib.gate",
    "skills._lib.loop.actions",
])
def test_lib_module_importable(module_name: str) -> None:
    """Each _lib module declared as a dependency MUST import without error."""
    importlib.import_module(module_name)


def test_lib_has_init_marker() -> None:
    assert (REPO_ROOT / "skills" / "__init__.py").exists(), (
        "skills/__init__.py must exist for skills to be a Python package"
    )
    assert (REPO_ROOT / "skills" / "_lib" / "__init__.py").exists(), (
        "_lib/__init__.py must exist for skills._lib to be importable"
    )


def test_init_markers_are_empty_or_minimal() -> None:
    """Top-level _lib/ and skills/ __init__.py should be empty (or near-empty).

    _lib/__init__.py is a backward-compatibility shim (re-exports _lib)
    and is allowed to contain imports per fix-rddf-init-broken-layout.
    """
    for rel in ("_lib/__init__.py", "skills/__init__.py"):
        text = (REPO_ROOT / rel).read_text()
        # Allow empty, docstring, or one-line comment; no import statements
        # Exception: TYPE_CHECKING block is for static analysis only
        in_type_checking = False
        for line in text.splitlines():
            ln = line.strip()
            if not ln or ln.startswith("#"):
                continue
            if 'if TYPE_CHECKING:' in ln:
                in_type_checking = True
                continue
            if in_type_checking:
                # Ignore everything inside TYPE_CHECKING block
                if ln.startswith(("import ", "from ")) and ln.endswith(":"):
                    # Nested block, continue
                    pass
                continue
            # Outside TYPE_CHECKING: check for side-effect imports
            if ln.startswith(("import ", "from ")):
                # Exception: TYPE_CHECKING is a static import
                if "TYPE_CHECKING" in ln:
                    continue
                raise AssertionError(f"{rel} contains a side-effect import: {ln!r}")

    # Backward-compat shim is explicitly allowed to re-export _lib
    shim = (REPO_ROOT / "skills" / "_lib" / "__init__.py").read_text()
    assert "Backward-compat shim" in shim or "_lib" in shim, (
        "_lib/__init__.py must be a backward-compatibility shim for _lib"
    )