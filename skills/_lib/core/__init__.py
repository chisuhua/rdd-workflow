# Backward-compat shim: re-export everything from _lib.core.
import sys
import _lib.core

sys.modules[__name__] = _lib.core
