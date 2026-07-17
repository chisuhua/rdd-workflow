"""Pytest configuration: ensure the project root is on sys.path.

Tests under tests/unit/ import from `skills._lib.*`. Because there is no
`skills/__init__.py` and `skills` is not an installed package, pytest must
locate the `skills` directory on sys.path. The project root (parent of this
`tests/` directory) is added so that `import skills._lib.xxx` resolves to
`/workspace/project/spec-workflow/skills/_lib/xxx.py`.

Phase 2 (skills-reorg-phase2-single-skill): skill directories with hyphens
(guide-arch, guide-plan, guide-ship, rddf-session) cannot be imported as
Python packages because hyphens are not valid Python identifiers.
The tool transforms import paths to use underscores (e.g. skills.guide_arch),
so we bridge the underscored names to the dashed directories.
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
