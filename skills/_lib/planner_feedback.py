# Backward-compat identity-merge shim: real module lives at _lib/planner_feedback.py
# per Stage 3 Change 2 (ADR-0042). `skills._lib.planner_feedback is _lib.planner_feedback` returns True
# so isinstance() and module-level state (caches, locks, registries) are shared.
import sys as _sys
import _lib.planner_feedback as _real
_sys.modules[__name__] = _real
