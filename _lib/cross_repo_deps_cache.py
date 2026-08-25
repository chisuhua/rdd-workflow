"""TTL cache for cross_repo_deps (24h default)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

PathLike = Union[str, Path]
CACHE_TTL_SECONDS = 24 * 60 * 60


def _read(path: PathLike) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def _write(path: PathLike, data: Dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(data, indent=2))


def load_cache(path: PathLike, spokes_key: str) -> Optional[Dict[str, Any]]:
    cache = _read(path)
    entry = cache.get(spokes_key)
    if entry is None:
        return None
    return entry.get("data")


def save_cache(path: PathLike, spokes_key: str, data: Dict[str, Any]) -> None:
    cache = _read(path)
    cache[spokes_key] = {"timestamp": time.time(), "data": data}
    _write(path, cache)


def is_cache_valid(path: PathLike, spokes_key: str) -> bool:
    cache = _read(path)
    entry = cache.get(spokes_key)
    if entry is None:
        return False
    age = time.time() - entry.get("timestamp", 0)
    return age < CACHE_TTL_SECONDS
