"""CI lint: every skills._lib.X import must have a corresponding shim.

Per add-shim-coverage-lint (2026-10-08): prevent the state_reader
incident (module promoted to top-level _lib/ without backward-compat
shim, breaking production CLI invocations for months).

The actual safety property: if any code under skills/** or _lib/** does
`from skills._lib.X import Y` (or `import skills._lib.X`), the file
`skills/_lib/X.py` (or for dotted names `skills/_lib/X/Y.py` for
`skills._lib.X.Y`) MUST exist. Otherwise the import will fail when the
caller's sys.path makes `import _lib.X` resolve to the missing shim
location.

Coverage rules:
  1. For every `from skills._lib.X` or `import skills._lib.X` found
     under skills/**.py and _lib/**/*.py, the corresponding
     `skills/_lib/<X-as-path>.py` MUST exist.
  2. Conversely, every shim under `skills/_lib/` must point to a real
     module under `_lib/` (orphan detection).

Skip:
  - Files inside `__pycache__/`
  - `skills/_lib/__init__.py` (package init, not a shim)
  - The skill-side compat alias `skills/loop_engine.py` (top-level shim
    that itself uses the skills/_lib/loop_engine.py shim)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB = _REPO_ROOT / "_lib"
_SKILLS_LIB = _REPO_ROOT / "skills" / "_lib"

# Match `from skills._lib.X import Y` and `import skills._lib.X` where
# X is a dotted module path. Anchored at the start of a line (after
# optional whitespace) so docstring/comment mentions like
# `from skills._lib.X import Y` in a docstring are NOT matched.
_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+skills\._lib\.([\w.]+)\s+import|import\s+skills\._lib\.([\w.]+))",
    re.MULTILINE,
)

# Files that are themselves shims/aliases (must not be checked, otherwise
# they recursively require themselves).
_SKIPPED_CONSUMERS = {
    "skills/loop_engine.py",  # top-level compat shim
    "skills/_lib/__init__.py",  # package init
}


def _consumer_files() -> list[Path]:
    """All skills-layer .py files that may import from skills._lib.

    Only skills-layer consumers can trigger the shim-resolution bug:
    when a skills/ script does `sys.path.insert(0, skills/)` or
    `sys.path.insert(0, <repo>)`, Python resolves `import _lib.X` to
    `skills/_lib/X.py` (the shim directory), and if the shim is missing,
    the real module fails to load.

    Consumers inside _lib/ always have _lib/ on sys.path, so the shim
    resolution issue does NOT apply — they're excluded.
    """
    out: list[Path] = []
    for f in (_REPO_ROOT / "skills").rglob("*.py"):
        if "__pycache__" in f.parts:
            continue
        out.append(f)
    return out


def _imported_module_files() -> set[str]:
    """Return the set of `skills._lib.X` module names referenced anywhere."""
    out: set[str] = set()
    for consumer in _consumer_files():
        rel = consumer.relative_to(_REPO_ROOT).as_posix()
        if rel in _SKIPPED_CONSUMERS:
            continue
        try:
            text = consumer.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in _IMPORT_RE.finditer(text):
            top = m.group(1) or m.group(2)
            if top:
                out.add(top)
    return out


def _shim_exists_for(dotted: str) -> bool:
    """Check both module and package shim forms.

    A dotted import `from skills._lib.core.atomic_write import X` can be
    satisfied by EITHER `skills/_lib/core/atomic_write.py` (module shim,
    exec-based like state_reader.py) OR a package shim — for which
    `skills/_lib/core/atomic_write/__init__.py` would also work. For
    the top-level `skills._lib.iteration`, the package shim is at
    `skills/_lib/iteration/__init__.py` (a real identity-merge shim
    using __path__ widening + spec_from_file_location).
    """
    as_path = _SKILLS_LIB / f"{dotted.replace('.', '/')}.py"
    if as_path.exists():
        return True
    # Try package shim: skills/_lib/X/__init__.py
    parts = dotted.split(".")
    last = parts[-1]
    pkg_shim = _SKILLS_LIB / "/".join(parts[:-1]) / last / "__init__.py" if len(parts) > 1 else _SKILLS_LIB / last / "__init__.py"
    if pkg_shim.exists():
        return True
    return False


def _real_for(dotted: str) -> Path:
    """Map `core.atomic_write` -> _lib/core/atomic_write.py"""
    return _LIB / f"{dotted.replace('.', '/')}.py"


def test_every_skills_lib_import_has_shim():
    """Every `from skills._lib.X import ...` must have a shim at skills/_lib/X.py."""
    missing: list[str] = []
    module_set = _imported_module_files()
    for dotted in sorted(module_set):
        if not _shim_exists_for(dotted):
            # Compute the most likely shim path for the error message
            as_path = _SKILLS_LIB / f"{dotted.replace('.', '/')}.py"
            missing.append(
                f"skills._lib.{dotted}: missing shim at {as_path.relative_to(_REPO_ROOT).as_posix()}"
            )
    assert not missing, (
        "Missing skills._lib shims for actively-imported modules. Production "
        "CLI paths that do `sys.path.insert(0, skills/)` will fail to load "
        "these modules (see commit 03eeb15: state_reader incident).\n\n"
        "Remediation: copy the 28-line template from "
        "skills/_lib/state_reader.py, replace 'state_reader' with the "
        "module name, and commit.\n\n" +
        "\n".join(missing)
    )


def test_no_orphan_shims():
    """Every skills/_lib/X.py shim must point to a real _lib/X.py module.

    Note: many skills/_lib/ files are pre-promotion copies (not identity-merge
    shims) — they coexist with their _lib/ counterpart and both are real code.
    We only flag files whose corresponding real module is missing.
    """
    if not _SKILLS_LIB.is_dir():
        return
    orphan: list[str] = []
    module_set = _imported_module_files()
    for shim in _SKILLS_LIB.rglob("*.py"):
        if "__pycache__" in shim.parts:
            continue
        if shim.name in {"__init__.py", "_python_resolve_project_root.py"}:
            continue
        rel = shim.relative_to(_SKILLS_LIB).as_posix()
        dotted = rel.replace("/", ".").removesuffix(".py")
        # If the dotted form is in the imported-module set, the real module must exist
        if dotted not in module_set:
            continue
        real = _real_for(dotted)
        if not real.exists():
            orphan.append(
                f"{shim.relative_to(_REPO_ROOT).as_posix()}: imports reference it "
                f"but no real module at {real.relative_to(_REPO_ROOT).as_posix()}"
            )
    assert not orphan, (
        "Orphan shims (imported but no real module exists). Remove the "
        "shim or restore the real module.\n\n" + "\n".join(orphan)
    )


def test_module_shims_are_identity_merge():
    """Every shim in skills/_lib/ that has a real counterpart MUST be identity-merge.

    Scope: only files that are referenced by `from skills._lib.X` importers
    AND have a real module at `_lib/X.py`. Pre-promotion code copies
    (no real module counterpart) are excluded — they're not shims.

    Subpackages that use `__path__` widening (e.g. `skills/_lib/iteration/`,
    `skills/_lib/core/`) are excluded — their submodules are reached via
    the real package's path, not via the skills-side copies.

    This is the actual contract that prevents the state_reader incident: a
    shim is useless unless `from skills._lib.X import Y` and
    `from _lib.X import Y` resolve to the same module object (so isinstance
    and module-level caches are shared).
    """
    # Subpackages using __path__ widening (their __init__.py does the routing)
    widening_pkgs = {"iteration", "core", "loop", "schedulers", "verifier", "plugins"}
    bad: list[str] = []
    module_set = _imported_module_files()
    for dotted in sorted(module_set):
        # Skip submodules of widening packages (they're dead code; the
        # real modules win via __path__ widening in the package __init__)
        parts = dotted.split(".")
        if len(parts) > 1 and parts[0] in widening_pkgs:
            continue
        as_path = _SKILLS_LIB / f"{dotted.replace('.', '/')}.py"
        if not as_path.exists():
            continue
        real = _real_for(dotted)
        if not real.exists():
            continue
        try:
            text = as_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "_sys.modules[__name__] = _real" not in text and \
           "sys.modules[__name__]" not in text:
            bad.append(
                f"{as_path.relative_to(_REPO_ROOT).as_posix()}: imported as "
                f"skills._lib.{dotted} with real module at "
                f"{real.relative_to(_REPO_ROOT).as_posix()}, but is not an "
                f"identity-merge shim (no `sys.modules[__name__] = _real`)"
            )
    assert not bad, (
        "Module shims must perform identity-merge. Without this, the shim "
        "loads a SECOND copy of the module and isinstance() / module-level "
        "state break (the state_reader incident pattern).\n\n" +
        "\n".join(bad)
    )
