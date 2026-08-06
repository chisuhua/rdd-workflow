# Backward-compat shim for the old `from skills._lib import X` import path.
# Re-exports everything from the new top-level `_lib` package by aliasing
# this module to `_lib` in sys.modules. Kept for >=6 months per
# fix-rddf-init-broken-layout proposal.
import sys
import _lib

sys.modules[__name__] = _lib
