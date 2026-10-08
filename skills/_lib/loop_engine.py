# Backward-compat identity-merge shim: real module lives at _lib/loop_engine.py
# per P1-1a (2026-08-25). `skills._lib.loop_engine is _lib.loop_engine` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
#
# Imported by: skills/loop_engine.py (top-level compatibility shim),
# skills/propose/scripts/propose_change.py, skills/propose/scripts/propose_quality_hook.py.
# Without this shim, the v2.0 Loop engine is unreachable from the skills layer
# after the module was promoted to top-level _lib/, breaking all propose flows.
import os as _os
import sys as _sys
import types as _types

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_HERE))
_REAL_PATH = _os.path.join(_REPO_ROOT, "_lib", "loop_engine.py")
_real = _sys.modules.get("_lib.loop_engine")
if _real is None:
    _real = _types.ModuleType("_lib.loop_engine")
    _real.__file__ = _REAL_PATH
    _real.__name__ = "_lib.loop_engine"
    _sys.modules[_real.__name__] = _real
    with open(_REAL_PATH, encoding="utf-8") as _f:
        exec(compile(_f.read(), _REAL_PATH, "exec"), _real.__dict__)
_sys.modules[__name__] = _real
