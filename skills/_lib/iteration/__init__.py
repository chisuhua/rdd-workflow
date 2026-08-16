"""Iteration state management (v7 cross_repo_dependencies).

Backward-compat shim re-exports from _lib.iteration for existing code.
Add cross_repo_dependencies field support for Hub-and-Spoke federation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union

PathLike = Union[str, Path]


def load_iteration_v6_compat(data: dict) -> dict:
    """Migrate v6 → v7 (add cross_repo_dependencies default)."""
    data = dict(data)
    data["version"] = 7
    for change in data.get("changes", {}).values():
        change.setdefault("cross_repo_dependencies", [])
    return data


def save_iteration_v7(path: PathLike, data: dict) -> None:
    """Write iteration data in v7 format."""
    Path(path).write_text(json.dumps(data, indent=2))
