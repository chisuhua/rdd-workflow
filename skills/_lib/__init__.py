"""skills._lib - worktree local modules + global fallback.

Provides a unified view of the _lib package by setting __path__ to include
both the worktree's local copy (if present) and the global install
fallback. Python's standard import machinery uses __path__ to locate
submodules, so this is sufficient — no ModuleType hackery needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent  # skills/_lib/
_GLOBAL_LIB = Path.home() / ".agents" / "skills" / "_lib"

__path__ = [str(_THIS_DIR)]
if str(_GLOBAL_LIB) != str(_THIS_DIR) and _GLOBAL_LIB.exists():
    __path__.append(str(_GLOBAL_LIB))

_PROJECT_ROOT = _THIS_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
