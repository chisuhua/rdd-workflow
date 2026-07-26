"""File-backed session persistence with advisory locking.

Extracted from the original RddfSessionCoordinator god class.
"""
from __future__ import annotations

import fcntl
import json
import pathlib

from typing import Any, Callable

from ._types import RddfSessionError, SCHEMA_PATH


class RddfSessionStore:
    """Atomic file I/O for sessions.json with POSIX advisory locking."""

    def __init__(self, sessions_file: str):
        self._sessions_file = pathlib.Path(sessions_file)
        self._lock_file = self._sessions_file.with_suffix(".lock")

    def read_unlocked(self) -> dict:
        """Read sessions.json. Returns empty structure if missing.
        Validates against schema when SCHEMA_PATH exists.
        """
        if not self._sessions_file.exists():
            return {"version": 1, "sessions": []}
        with self._sessions_file.open("r") as f:
            data = json.load(f)
        if SCHEMA_PATH.exists():
            import jsonschema
            with SCHEMA_PATH.open("r") as schema_f:
                schema = json.load(schema_f)
            jsonschema.validate(instance=data, schema=schema)
        return data

    def atomic_write(self, data: dict) -> None:
        """Write sessions.json atomically (write-to-tmp + rename)."""
        from skills._lib.core.atomic_write import atomic_write_json

        atomic_write_json(str(self._sessions_file), data)

    def with_file_lock(self, fn: Callable) -> Any:
        """Acquire advisory file lock, run fn, release.

        POSIX-only (uses fcntl.flock). On Windows, callers should wrap with
        a different locking strategy or run inside WSL.
        """
        self._lock_file.parent.mkdir(parents=True, exist_ok=True)
        with self._lock_file.open("w") as lockf:
            try:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (IOError, OSError) as e:
                raise RddfSessionError(
                    f"Could not acquire lock on {self._lock_file}: {e}"
                ) from e
            try:
                return fn()
            finally:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)