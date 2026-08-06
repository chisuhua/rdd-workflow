# Backward-compat shim: re-export everything from _lib.cli.
import sys
import _lib.cli

sys.modules[__name__] = _lib.cli
