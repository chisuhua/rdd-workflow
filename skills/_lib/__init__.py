"""skills._lib - worktree local modules + global fallback.

This __init__.py runs first when `import skills._lib.X` is executed.
It sets up sys.path to prefer the worktree's skills/_lib/ over the
global install (~/.agents/skills/_lib/) when running in a worktree context.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType

# Project root is 3 levels up from skills/_lib/
_THIS_DIR = Path(__file__).resolve().parent  # skills/_lib/
_PROJECT_ROOT = _THIS_DIR.parent.parent  # project root

# Build the worktree's skills/_lib path
_WORKTREE_LIB = _PROJECT_ROOT / "skills" / "_lib"

# If we're in a worktree (skills/_lib/ exists locally), set up the module
# to use the worktree's path first
if _WORKTREE_LIB.exists() and str(_WORKTREE_LIB) != str(Path.home() / ".agents" / "skills" / "_lib"):
    # Replace this module's __path__ to point to worktree's _lib/
    if "skills._lib" in sys.modules:
        _mod = sys.modules["skills._lib"]
        if not hasattr(_mod, '__path__') or str(_WORKTREE_LIB) not in (str(p) for p in getattr(_mod, '__path__', [])):
            _mod.__path__ = [str(_WORKTREE_LIB)]
    else:
        _mod = ModuleType("skills._lib")
        _mod.__path__ = [str(_WORKTREE_LIB)]
        _mod.__file__ = str(_THIS_DIR / "__init__.py")
        sys.modules["skills._lib"] = _mod

    # Also ensure project root is in sys.path for 'import skills' to work
    _project_root_str = str(_PROJECT_ROOT)
    if _project_root_str not in sys.path:
        sys.path.insert(0, _project_root_str)

    # Clear any cached imports from global install for skills._lib
    for _key in list(sys.modules.keys()):
        if _key.startswith("skills._lib"):
            del sys.modules[_key]

# Delegate to global install shim (which may have already set up some state)
_GLOBAL_LIB = Path.home() / ".agents" / "skills" / "_lib"
if str(_THIS_DIR) != str(_GLOBAL_LIB):
    # Import from global install
    if str(_GLOBAL_LIB.parent) not in sys.path:
        sys.path.insert(0, str(_GLOBAL_LIB.parent))
    try:
        import _lib
        # Re-export everything from global install
        for _name in dir(_lib):
            if not _name.startswith("_"):
                globals()[_name] = getattr(_lib, _name)
    except ImportError:
        pass
