# Backward-compat identity-merge shim: real module lives at _lib/arch_quality_gate.py
# per P1-1a (2026-08-25). `skills._lib.arch_quality_gate is _lib.arch_quality_gate` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
#
# Imported by: _lib/change_alignment.py, _lib/dashboard/__init__.py, _lib/gate.py,
# skills/rdd-arch/scripts/arch_quality_report.sh (via add-skill-layer).
# Without this shim, any caller that does `import skills._lib.arch_quality_gate`
# after promoting the module to top-level _lib/ will get a partially-initialised
# module object (Python resolves `import _lib` to `skills/_lib/` when that
# directory is on sys.path), causing AttributeError on first use.
import os as _os
import sys as _sys
import types as _types

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_HERE))
_REAL_PATH = _os.path.join(_REPO_ROOT, "_lib", "arch_quality_gate.py")
_real = _sys.modules.get("_lib.arch_quality_gate")
if _real is None or getattr(_real, "__file__", None) == __file__:
    _real = _types.ModuleType("_lib.arch_quality_gate")
    _real.__file__ = _REAL_PATH
    _real.__name__ = "_lib.arch_quality_gate"
    _sys.modules[_real.__name__] = _real
    with open(_REAL_PATH, encoding="utf-8") as _f:
        exec(compile(_f.read(), _REAL_PATH, "exec"), _real.__dict__)
_sys.modules[__name__] = _real
