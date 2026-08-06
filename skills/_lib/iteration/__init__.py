# Backward-compat shim: re-export everything from _lib.iteration.
import sys
import _lib.iteration

sys.modules[__name__] = _lib.iteration
