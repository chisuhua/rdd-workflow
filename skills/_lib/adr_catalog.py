# Backward-compat identity-merge shim: real module lives at _lib/adr_catalog.py
# per P1-1a (2026-08-25). `skills._lib.adr_catalog is _lib.adr_catalog` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
import sys as _sys
import _lib.adr_catalog as _real
_sys.modules[__name__] = _real
