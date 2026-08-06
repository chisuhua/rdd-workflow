"""Pytest configuration: ensure the project root is on sys.path.

Tests under tests/unit/ import from `skills._lib.*`, `skills._lib.core.*`,
and `skills._lib.loop.*`. Because there is no `skills/__init__.py` and
`skills` is not an installed package, pytest must locate the `skills`
directory on sys.path. The project root (parent of this `tests/` directory)
is added so that `import skills._lib.xxx` resolves to
`/workspace/project/rdd-workflow/_lib/xxx.py`,
`import skills._lib.core.xxx` resolves to `…/_lib/core/xxx.py`, and
`import skills._lib.loop.xxx` resolves to `…/_lib/loop/xxx.py`.

Phase 3 (skills-reorg-phase3-core): _lib/ reorganized into core/ (6 runtime
kernel modules) + loop/ (15 v2.0 loop engine modules). Top-level cross-cutting
modules stay at _lib/. Import paths now use skills._lib.core.xxx and
skills._lib.loop.xxx in addition to skills._lib.xxx.
"""
import sys
import types
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT_STR = str(_PROJECT_ROOT)

if _PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT_STR)

# Phase 2 dash-bridge: map skills.<underscore> to skills/<dash>/ directories
_DASH_SKILLS = [
    ("guide-arch", "guide_arch"),
    ("guide-design", "guide_design"),
    ("guide-plan", "guide_plan"),
    ("guide-ship", "guide_ship"),
    ("rddf-session", "rddf_session"),
]

for _dash, _us in _DASH_SKILLS:
    for _level in ("", ".scripts"):
        _mod_name = f"skills.{_us}{_level}"
        if _mod_name not in sys.modules:
            _mod = types.ModuleType(_mod_name)
            _level_dir = _level.lstrip(".") if _level else _level
            _mod.__path__ = [os.path.join(_PROJECT_ROOT_STR, "skills", _dash, _level_dir) if _level_dir else os.path.join(_PROJECT_ROOT_STR, "skills", _dash)]
            sys.modules[_mod_name] = _mod
