# Backward-compat identity-merge shim: real module lives at _lib/core/lock.py
# per P1-1a (2026-08-25). `skills._lib.core.lock is _lib.core.lock` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
#
# Submodule of the skills/_lib.core package (per c3a90fe __path__ widening);
# without this shim, `from skills._lib.core.lock import X` fails to resolve
# when the caller's sys.path makes `import skills._lib.core` resolve to the
# skills-side package rather than the flatten-layout _lib/core/.
#
# Imported by: skills/_lib/iteration/store.py, skills/deps/scripts/deps_output.py,
# skills/feature/scripts/feature_view.py.
import os as _os
import sys as _sys
import types as _types

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_HERE)))
_REAL_PATH = _os.path.join(_REPO_ROOT, "_lib", "core", "lock.py")
_real = _sys.modules.get("_lib.core.lock")
if _real is None:
    _real = _types.ModuleType("_lib.core.lock")
    _real.__file__ = _REAL_PATH
    _real.__name__ = "_lib.core.lock"
    _sys.modules[_real.__name__] = _real
    with open(_REAL_PATH, encoding="utf-8") as _f:
        exec(compile(_f.read(), _REAL_PATH, "exec"), _real.__dict__)
_sys.modules[__name__] = _real
