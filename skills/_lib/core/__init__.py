"""skills._lib.core backward-compat shim.

Per commit c3a90fe (flatten package layout), the full implementation lives
under the repo-root `_lib/core/` package. This shim widens __path__ to
include that package AND re-exports its public symbols so
`from skills._lib.core.X import Y` works the same as
`from _lib.core.X import Y` regardless of which layout the caller uses.

Without this shim, bash subprocess invocations that import
`skills._lib.core.lock` etc. fail with `cannot access submodule 'core'`
because the empty shim `__init__.py` here was overriding the real package.
"""
from __future__ import annotations

import os

# Path-widening: route `skills._lib.core.X` lookups to the flatten-layout
# `_lib/core/X.py` files when not found in `skills/_lib/core/`.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_DIR)))
_FLATTEN_CORE = os.path.join(_REPO_ROOT, "_lib", "core")
if _FLATTEN_CORE not in __path__:
    __path__.append(_FLATTEN_CORE)
