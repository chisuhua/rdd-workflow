# Backward-compat identity-merge shim: real module lives at _lib/cli/rdd_arch_cmd.py
# per Stage 3 Change 4 (ADR-0042). `skills._lib.cli.rdd_arch_cmd is _lib.cli.rdd_arch_cmd`
# returns True so isinstance() and module-level state (caches, locks, registries) are shared.
import sys as _sys
import _lib.cli.rdd_arch_cmd as _real
_sys.modules[__name__] = _real
