# Backward-compat identity-merge shim: real module lives at _lib/tasks_count.py
# per P1-1a (2026-08-25). `skills._lib.tasks_count is _lib.tasks_count` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
#
# Wave X1 fix: load the real module by exec'ing its source directly, instead of
# `import _lib.tasks_count`. The plain import fails when the caller's sys.path
# includes this shim's directory (e.g. when a caller does `sys.path.insert(0,
# skills/)` — Python then resolves `import _lib` to `skills/_lib/` (this shim)
# and returns a partially-initialised module object without the real module's
# attributes). Historically this affected roadmap_incremental_update.py
# (deleted Sep 2026 per ADR-0048); the exec-based fix remains correct for any
# future caller that does the same sys.path mutation.
import os as _os
import sys as _sys
import types as _types
import importlib.util as _importlib_util

_HERE = _os.path.dirname(_os.path.abspath(__file__))          # skills/_lib
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_HERE))            # repo root (above skills/)
_REAL_PATH = _os.path.join(_REPO_ROOT, "_lib", "tasks_count.py")
_real = _sys.modules.get("_lib.tasks_count")
# Self-detection: when `skills/` is on sys.path, Python resolves
# `import _lib.tasks_count` to THIS shim (skills/_lib/tasks_count.py) and
# registers it under the real name *before* executing it. The lookup above
# would then return ourselves, the `if _real is None` branch would be skipped,
# and `_lib.tasks_count` would stay a partially-initialised shim with no
# functions — every `from _lib.tasks_count import count_tasks` after that fails.
if _real is not None and _os.path.abspath(
    getattr(_real, "__file__", "") or ""
) == _os.path.abspath(__file__):
    _real = None
if _real is None:
    _real = _types.ModuleType("_lib.tasks_count")
    _real.__file__ = _REAL_PATH
    _real.__name__ = "_lib.tasks_count"
    # A ModuleType built by hand has __spec__ = None, which makes
    # importlib.util.find_spec(<public name>) raise ValueError. Give it a
    # real spec so the module is introspectable like any other.
    _real.__spec__ = _importlib_util.spec_from_file_location(
        "skills._lib.tasks_count", _REAL_PATH
    )
    _sys.modules[_real.__name__] = _real
    with open(_REAL_PATH, encoding="utf-8") as _f:
        exec(compile(_f.read(), _REAL_PATH, "exec"), _real.__dict__)
_sys.modules[__name__] = _real