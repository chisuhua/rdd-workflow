# Backward-compat identity-merge shim: real module lives at _lib/parse_approved.py
# per P1-1a (2026-08-25). `skills._lib.parse_approved is _lib.parse_approved` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
#
# Imported by: skills/propose/scripts/propose_change.py,
# skills/propose/scripts/propose_quality_hook.py.
# Without this shim, the propose quality hook can't enumerate approved proposals
# and silently emits empty results (no error, just no entries).
import os as _os
import sys as _sys
import types as _types

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_HERE))
_REAL_PATH = _os.path.join(_REPO_ROOT, "_lib", "parse_approved.py")
_real = _sys.modules.get("_lib.parse_approved")
if _real is None or getattr(_real, "__file__", None) == __file__:
    _real = _types.ModuleType("_lib.parse_approved")
    _real.__file__ = _REAL_PATH
    _real.__name__ = "_lib.parse_approved"
    _sys.modules[_real.__name__] = _real
    with open(_REAL_PATH, encoding="utf-8") as _f:
        exec(compile(_f.read(), _REAL_PATH, "exec"), _real.__dict__)
_sys.modules[__name__] = _real
