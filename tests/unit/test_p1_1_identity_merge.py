"""P1-1 regression test: lock identity-merge for migrated cross-repo modules.

The 10 modules migrated from skills/_lib/ to _lib/ in P1-1a MUST share module
identity so that isinstance(), module-level state (caches, locks, registries),
and singleton patterns work correctly. Without this, code that imports via
`from _lib.cross_repo_state import State` vs
`from skills._lib.cross_repo_state import State` ends up with two distinct
module objects, splitting state silently.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


# 10 modules migrated in P1-1a (2026-08-25)
MIGRATED_MODULES = [
    "adr_catalog",
    "cleanup_plan_handoff",
    "contract_diff",
    "cross_repo_audit",
    "cross_repo_deps",
    "cross_repo_deps_cache",
    "cross_repo_gate",
    "cross_repo_state",
    "gh_hub_client",
    "hub_issue",
]


@pytest.mark.parametrize("module_name", MIGRATED_MODULES)
def test_module_identity_merged(module_name: str) -> None:
    """`skills._lib.X is _lib.X` MUST be True for all P1-1a migrated modules."""
    # Force fresh import (avoid cached modules from earlier tests)
    canonical = importlib.import_module(f"_lib.{module_name}")
    shim = importlib.import_module(f"skills._lib.{module_name}")

    # Identity check: must be the same module object
    assert canonical is shim, (
        f"Module identity split detected for {module_name}!\n"
        f"  _lib.{module_name} id={id(canonical)} file={canonical.__file__}\n"
        f"  skills._lib.{module_name} id={id(shim)} file={shim.__file__}\n"
        f"This breaks isinstance() checks and module-level state sharing.\n"
        f"Verify skills/_lib/{module_name}.py uses sys.modules[__name__] = _lib.X pattern."
    )

    # Sanity: __file__ should point to the canonical _lib/ location, not skills/_lib/
    assert canonical.__file__ is not None
    # The shim's __file__ after sys.modules alias is canonical's __file__
    assert shim.__file__ == canonical.__file__


def test_hub_issue_gh_hub_client_shared() -> None:
    """hub_issue imports GhHubClient — must be the SAME class object."""
    hub = importlib.import_module("skills._lib.hub_issue")
    gh = importlib.import_module("_lib.gh_hub_client")

    # The GhHubClient class referenced by hub_issue must be gh.GhHubClient
    assert hub.GhHubClient is gh.GhHubClient, (
        "GhHubClient class is not the same object between hub_issue and "
        "gh_hub_client — identity split not fully fixed."
    )


def test_cross_repo_gate_uses_internal_canonical_imports() -> None:
    """cross_repo_gate lazy imports should reference _lib.X, not skills._lib.X.

    After P1-1a migration, internal cross-imports must use the canonical
    `_lib.X` namespace. Legacy `from skills._lib.cross_repo_deps import ...`
    references must be removed from the moved source.
    """
    src = REPO_ROOT / "_lib" / "cross_repo_gate.py"
    content = src.read_text()
    # Strip comments and docstrings to avoid false positives on prose like
    # "Wraps kahn_topological_sort from skills._lib.cross_repo_deps".
    import re
    code_lines = []
    in_docstring = False
    for line in content.split("\n"):
        stripped = line.strip()
        if in_docstring:
            if '"""' in stripped or "'''" in stripped:
                in_docstring = False
            continue
        if stripped.startswith("#"):
            continue
        if '"""' in stripped or "'''" in stripped:
            if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                in_docstring = True
            continue
        code_lines.append(line)
    code = "\n".join(code_lines)
    assert "from skills._lib." not in code, (
        f"cross_repo_gate.py still has legacy `from skills._lib.X` imports "
        f"in code (not docstring/comment).\n"
        f"After P1-1a migration, internal cross-imports must use `_lib.X`."
    )
