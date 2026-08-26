"""Resolve implementation commit from openspec/<change> branch tip.

Per fix-rdd-verifier-lifecycle-dashboard Task 5:
- Returns the SHA of the openspec/<change> branch tip when present
- Returns None when branch missing, detached HEAD, or not a git repo
- Never raises
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def resolve_implementation_commit(project_root: Path, change_name: str) -> Optional[str]:
    """Return implementation commit SHA or None (fail closed)."""
    branch = f"openspec/{change_name}"
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--verify", "--quiet", branch],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None
