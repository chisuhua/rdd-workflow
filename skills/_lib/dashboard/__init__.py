# Backward-compat shim: re-export everything from _lib.dashboard.
import sys
import _lib.dashboard

sys.modules[__name__] = _lib.dashboard
