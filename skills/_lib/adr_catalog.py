# Backward-compat identity-merge shim: real module lives at _lib/adr_catalog.py
# per P1-1a (2026-08-25). `skills._lib.adr_catalog is _lib.adr_catalog` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
#
# Wave X1 fix: load the real module by exec'ing its source directly, instead of
# `import _lib.adr_catalog`. The plain import fails when the caller's sys.path
# includes this shim's directory (e.g. when roadmap_incremental_update.py does
# `sys.path.insert(0, skills/)` — Python then resolves `import _lib` to
# `skills/_lib/` (this shim) and returns a partially-initialised module object
# without the real module's attributes).
import os as _os
import sys as _sys
import types as _types

_HERE = _os.path.dirname(_os.path.abspath(__file__))          # skills/_lib
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_HERE))            # repo root (above skills/)
_REAL_PATH = _os.path.join(_REPO_ROOT, "_lib", "adr_catalog.py")
_real = _sys.modules.get("_lib.adr_catalog")
if _real is None:
    _real = _types.ModuleType("_lib.adr_catalog")
    _real.__file__ = _REAL_PATH
    _real.__name__ = "_lib.adr_catalog"
    _sys.modules[_real.__name__] = _real
    with open(_REAL_PATH, encoding="utf-8") as _f:
        exec(compile(_f.read(), _REAL_PATH, "exec"), _real.__dict__)
_sys.modules[__name__] = _real