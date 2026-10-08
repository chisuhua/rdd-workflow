# Backward-compat identity-merge shim: real module lives at _lib/core/atomic_write.py
# per P1-1a (2026-08-25). `skills._lib.core.atomic_write is _lib.core.atomic_write` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
#
# Submodule of the skills/_lib.core package (per c3a90fe __path__ widening);
# without this shim, `from skills._lib.core.atomic_write import X` fails to
# resolve when the caller's sys.path makes `import skills._lib.core` resolve
# to the skills-side package rather than the flatten-layout _lib/core/.
#
# Imported by: skills/_lib/iteration/store.py, skills/deps/scripts/deps_output.py,
# skills/rddf-session/scripts/rddf_session_pkg/_store.py.
import os as _os
import sys as _sys
import types as _types

_HERE = _os.path.dirname(_os.path.abspath(__file__))  # skills/_lib/core
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_HERE)))  # repo root
_REAL_PATH = _os.path.join(_REPO_ROOT, "_lib", "core", "atomic_write.py")

# Identity-merge: see skills/_lib/core/lock.py for the rationale on
# `if _real is None or _real.__file__ == __file__`.
_real = _sys.modules.get("_lib.core.atomic_write")
if _real is None or getattr(_real, "__file__", None) == __file__:
    _real = _types.ModuleType("_lib.core.atomic_write")
    _real.__file__ = _REAL_PATH
    _real.__name__ = "_lib.core.atomic_write"
    _sys.modules[_real.__name__] = _real
    with open(_REAL_PATH, encoding="utf-8") as _f:
        exec(compile(_f.read(), _REAL_PATH, "exec"), _real.__dict__)
_sys.modules[__name__] = _real
