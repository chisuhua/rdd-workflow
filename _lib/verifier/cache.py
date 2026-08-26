"""SHA-fingerprint verdict cache for rdd-verifier.

Per ADR-0034 §7.2 + Oracle review §C: avoids double LLM calls when
archive_gate_check runs after rdd-verifier (same codebase commit = cache hit).

Cache file: `.rddf/state/.ac-verdict-<change>.json` (gitignored, schema v1).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _cache_path(project_root: Path, change_name: str) -> Path:
    return project_root / ".rddf" / "state" / f".ac-verdict-{change_name}.json"


def verdict_cache(
    project_root: Path,
    change_name: str,
    codebase_commit: str,
    verdict: list,
    ran_by: str,
) -> Path:
    """Write verdict cache for a change. Returns the cache file path.

    Args:
        project_root: Path to project root (must contain .rddf/state/).
        change_name: OpenSpec change name.
        codebase_commit: git SHA at the time of verification.
        verdict: list of verdict items from ac-verifier.
        ran_by: "rdd-verifier" or "archive_gate_check".

    Returns:
        Path to the written cache file.

    Raises:
        OSError: if .rddf/state/ cannot be created.
    """
    path = _cache_path(Path(project_root), change_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = {
        "version": 1,
        "change": change_name,
        "codebase_commit": codebase_commit,
        "verdict": verdict,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "ran_by": ran_by,
    }
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return path


def read_verdict_cache(project_root: Path, change_name: str) -> Optional[dict]:
    """Read verdict cache. Returns None if missing or corrupt (treat as cache miss)."""
    path = _cache_path(Path(project_root), change_name)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def is_cache_fresh(project_root: Path, change_name: str, current_commit: str) -> bool:
    """Check if cached verdict matches current codebase commit.

    Returns False if cache is missing, corrupt, or stale.
    """
    cached = read_verdict_cache(project_root, change_name)
    if cached is None:
        return False
    return cached.get("codebase_commit") == current_commit