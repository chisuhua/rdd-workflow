"""skills._lib.loop backward-compat shim.

Per commit c3a90fe (flatten package layout), the full implementation lives
under the repo-root `_lib/loop/` package. This shim widens __path__ to
include that package so `from skills._lib.loop.X import Y` resolves the
same as `from _lib.loop.X import Y` regardless of caller layout.

Without this shim, bash subprocess invocations that import
`skills._lib.loop.sanitizer` etc. fail with `cannot access submodule
'loop'` because the empty shim `__init__.py` here was overriding the
real package.
"""
from __future__ import annotations

import os

# Path-widening: route `skills._lib.loop.X` lookups to the flatten-layout
# `_lib/loop/X.py` files when not found in `skills/_lib/loop/`.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_DIR)))
_FLATTEN_LOOP = os.path.join(_REPO_ROOT, "_lib", "loop")
if _FLATTEN_LOOP not in __path__:
    __path__.append(_FLATTEN_LOOP)
