"""Locate the two proposal index files for the doctor checks.

Canonical location rule: `_lib/core/rddf_paths.py`. A `rdd-doctor/` copy
without `_lib/` must still run (doctor_main's lazy-import contract), so the
import is guarded and the same precedence is spelled out inline as a fallback:

- `<root>/.rddf/<name>` when it exists (canonical)
- `<root>/<name>` when that legacy copy exists
- `<root>/.rddf/<name>` otherwise

The candidate roots cover both layouts the checks can run from: a repo
checkout (`skills/rdd-doctor/scripts` → repo root) and a global install
(`~/.agents/skills/rdd-doctor/scripts` → `~/.agents/skills`, which holds
`_lib/`). They are *appended* to `sys.path`, never inserted — a consumer
project's own `_lib/` must keep precedence.
"""
from __future__ import annotations

import sys
from pathlib import Path

for _root in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[3]):
    if str(_root) not in sys.path:
        sys.path.append(str(_root))

try:  # pragma: no cover - exercised only in a full checkout / install tree
    from _lib.core.rddf_paths import resolve as _resolve

    def resolve_index_file(project_root: Path, name: str) -> Path:
        return Path(_resolve(str(project_root), name))

except Exception:  # pragma: no cover - standalone rdd-doctor/ copy

    def resolve_index_file(project_root: Path, name: str) -> Path:
        canonical = project_root / ".rddf" / name
        legacy = project_root / name
        if canonical.is_file():
            return canonical
        if legacy.is_file():
            return legacy
        return canonical
