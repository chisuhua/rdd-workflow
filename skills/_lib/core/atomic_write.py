"""Atomic file write utilities — single shared implementation.

Wave 8 / fix-debt-audit-2026-07-14 / Wave 3.1: consolidate 4+ independent
``_atomic_write`` implementations that were drifting across the
codebase. Replaces:
  - skills/_lib/validate_report.py::_atomic_write
  - skills/_lib/deps_output.py::_atomic_write
  - skills/_lib/iteration.py::_atomic_write
  - skills/_lib/rddf_session.py::RddfSessionCoordinator._atomic_write

``state_vector.save`` still uses a custom tempfile.mkstemp flow because
it requires a ``FileLock`` around the rename; the FileLock is not part
of this helper (caller responsibility). If the caller does not need
locking, prefer ``atomic_write_json`` directly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Union

__all__ = ["atomic_write_json", "atomic_write_text"]


def atomic_write_json(
    path: Union[str, Path],
    data: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> None:
    """Atomically write ``data`` as JSON to ``path``.

    The file is created at ``path + ".tmp"`` in the same directory, fsynced,
    then renamed over ``path``. Creates parent directories as needed.

    Atomicity guarantee: a concurrent reader will see either the old
    file or the new file, never a half-written one. Does NOT acquire
    any file lock; callers that need mutual exclusion across writers
    should layer a FileLock around this call.
    """
    path = str(path)
    target_dir = os.path.dirname(path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def atomic_write_text(
    path: Union[str, Path],
    content: str,
    *,
    encoding: str = "utf-8",
) -> None:
    """Atomically write text content to ``path`` (no JSON serialization)."""
    path = str(path)
    target_dir = os.path.dirname(path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding=encoding) as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)