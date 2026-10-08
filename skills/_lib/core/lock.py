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
# skills/feature/scripts/feature_view.py, skills/rdd-arch/scripts/write_arch_handoff.py.
import os as _os
import sys as _sys
import types as _types

_HERE = _os.path.dirname(_os.path.abspath(__file__))  # skills/_lib/core
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_HERE)))  # repo root
_REAL_PATH = _os.path.join(_REPO_ROOT, "_lib", "core", "lock.py")

# Identity-merge: ensure sys.modules["_lib.core.lock"] holds the real
# module's contents. The check `if _real is None` is NOT enough because
# when this shim is first loaded via `import _lib.core.lock` (rather than
# `import skills._lib.core.lock`), Python adds the shim itself to
# sys.modules BEFORE the shim body runs — so `sys.modules.get("_lib.core.lock")`
# returns the shim, not None, and the exec block would be skipped.
# The robust check is: re-exec whenever sys.modules doesn't already have
# the real module (i.e. either missing or pointing back at this shim).
_real = _sys.modules.get("_lib.core.lock")
if _real is None or getattr(_real, "__file__", None) == __file__:
    _real = _types.ModuleType("_lib.core.lock")
    _real.__file__ = _REAL_PATH
    _real.__name__ = "_lib.core.lock"
    _sys.modules[_real.__name__] = _real
    with open(_REAL_PATH, encoding="utf-8") as _f:
        exec(compile(_f.read(), _REAL_PATH, "exec"), _real.__dict__)
_sys.modules[__name__] = _real
