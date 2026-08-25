# Backward-compat identity-merge shim: real module lives at _lib/gh_hub_client.py
# per P1-1a (2026-08-25). `skills._lib.gh_hub_client is _lib.gh_hub_client` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
import sys as _sys
import _lib.gh_hub_client as _real
_sys.modules[__name__] = _real
