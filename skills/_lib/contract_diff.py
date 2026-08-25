# Backward-compat identity-merge shim: real module lives at _lib/contract_diff.py
# per P1-1a (2026-08-25). `skills._lib.contract_diff is _lib.contract_diff` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
import sys as _sys
import _lib.contract_diff as _real
_sys.modules[__name__] = _real
