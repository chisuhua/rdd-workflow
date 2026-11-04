# Backward-compat identity-merge shim: real module lives at _lib/_python_resolve_project_root.py
import sys as _sys
import _lib._python_resolve_project_root as _real
_sys.modules[__name__] = _real
