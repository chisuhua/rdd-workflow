# Backward-compat shim: re-export everything from _lib.loop.
import sys
import _lib.loop

sys.modules[__name__] = _lib.loop
