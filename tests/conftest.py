"""Pytest configuration: ensure the project root is on sys.path.

Tests under tests/unit/ import from `skills._lib.*`. Because there is no
`skills/__init__.py` and `skills` is not an installed package, pytest must
locate the `skills` directory on sys.path. The project root (parent of this
`tests/` directory) is added so that `import skills._lib.xxx` resolves to
`/workspace/project/spec-workflow/skills/_lib/xxx.py`.
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT_STR = str(_PROJECT_ROOT)

if _PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT_STR)
