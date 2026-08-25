# Backward-compat identity-merge shim: real module lives at _lib/hub_issue.py
# per P1-1a (2026-08-25). `skills._lib.hub_issue is _lib.hub_issue` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
import sys as _sys
import _lib.hub_issue as _real
_sys.modules[__name__] = _real
