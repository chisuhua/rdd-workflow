# Backward-compat shim for the old `from skills._lib import X` import path.
# Re-exports everything from the global install at ~/.agents/skills/_lib
# (created by `install.sh --global`; symlink to rdd-workflow source).
# Kept for >=6 months per fix-rddf-init-broken-layout proposal.
import sys
from pathlib import Path

_GLOBAL_LIB = Path.home() / ".agents" / "skills" / "_lib"
if str(_GLOBAL_LIB.parent) not in sys.path:
    sys.path.insert(0, str(_GLOBAL_LIB.parent))

import _lib  # noqa: E402

sys.modules[__name__] = _lib
