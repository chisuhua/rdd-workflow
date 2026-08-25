# Backward-compat identity-merge shim: real module lives at _lib/cross_repo_state.py
# per P1-1a (2026-08-25). `skills._lib.cross_repo_state is _lib.cross_repo_state` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
import sys as _sys
import _lib.cross_repo_state as _real
_sys.modules[__name__] = _real
