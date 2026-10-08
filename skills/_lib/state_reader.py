# Backward-compat identity-merge shim: real module lives at _lib/state_reader.py
# per P1-1a (2026-08-25). `skills._lib.state_reader is _lib.state_reader` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
#
# Wave X1 fix: load the real module by exec'ing its source directly, instead of
# `import _lib.state_reader`. The plain import fails when the caller's sys.path
# includes this shim's directory (e.g. when a caller does `sys.path.insert(0,
# skills/)` — Python then resolves `import _lib` to `skills/_lib/` (this shim)
# and returns a partially-initialised module object without the real module's
# attributes). Historically this affected roadmap_incremental_update.py
# (deleted Sep 2026 per ADR-0048); the exec-based fix remains correct for any
# future caller that does the same sys.path mutation.
#
# Per add-monitor-watch-triage (2026-10-08): monitor_cmd, cleanup_cmd, status_cmd,
# iteration_strict_cmd, workflow_synthesizer, and feature_cli all import from
# skills._lib.state_reader. This shim fixes the production CLI invocation path
# that broke when state_reader was promoted to a top-level _lib module without
# the corresponding identity-merge shim.
import os as _os
import sys as _sys
import types as _types

_HERE = _os.path.dirname(_os.path.abspath(__file__))          # skills/_lib
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_HERE))            # repo root (above skills/)
_REAL_PATH = _os.path.join(_REPO_ROOT, "_lib", "state_reader.py")
_real = _sys.modules.get("_lib.state_reader")
if _real is None or getattr(_real, "__file__", None) == __file__:
    _real = _types.ModuleType("_lib.state_reader")
    _real.__file__ = _REAL_PATH
    _real.__name__ = "_lib.state_reader"
    _sys.modules[_real.__name__] = _real
    with open(_REAL_PATH, encoding="utf-8") as _f:
        exec(compile(_f.read(), _REAL_PATH, "exec"), _real.__dict__)
_sys.modules[__name__] = _real