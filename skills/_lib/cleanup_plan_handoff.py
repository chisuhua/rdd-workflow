# Backward-compat identity-merge shim: real module lives at _lib/cleanup_plan_handoff.py
# per P1-1a (2026-08-25). `skills._lib.cleanup_plan_handoff is _lib.cleanup_plan_handoff` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
import sys as _sys
import _lib.cleanup_plan_handoff as _real
_sys.modules[__name__] = _real
