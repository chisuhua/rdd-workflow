"""skills._lib - worktree local modules + global fallback.

Provides a unified view of the _lib package by setting __path__ to include the
shim layer (`skills/_lib/`), the real implementation layer (repo-root `_lib/`)
and the global install fallback. Python's standard import machinery uses
__path__ to locate submodules, so this is sufficient — no ModuleType hackery
needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent  # skills/_lib/
_GLOBAL_LIB = Path.home() / ".agents" / "skills" / "_lib"
_PROJECT_ROOT = _THIS_DIR.parent.parent
_LOCAL_LIB = _PROJECT_ROOT / "_lib"

__path__ = [str(_THIS_DIR)]
# Repo-root `_lib/` is the real implementation layer. Without it, `skills._lib.X`
# for a module that has no identity-merge shim in `skills/_lib/` resolves only
# through the machine-global install (`~/.agents/skills/_lib`, a symlink to this
# repo) ⇒ ModuleNotFoundError on a fresh checkout (CI). Order matters: the
# physical shims in `skills/_lib/` stay FIRST so their identity merge wins.
if _LOCAL_LIB.is_dir() and str(_LOCAL_LIB) != str(_THIS_DIR):
    __path__.append(str(_LOCAL_LIB))
if (
    str(_GLOBAL_LIB) != str(_THIS_DIR)
    and str(_GLOBAL_LIB) not in __path__
    and _GLOBAL_LIB.exists()
):
    __path__.append(str(_GLOBAL_LIB))

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
