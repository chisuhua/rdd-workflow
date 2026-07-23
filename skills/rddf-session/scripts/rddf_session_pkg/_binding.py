"""Session-to-OpenCode-session binding (ADR-0017 §3).

Extracted from the original RddfSessionCoordinator god class.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional

from ._types import RddfSession, RddfSessionError, _VALID_KINDS, _now
from ._store import RddfSessionStore


class RddfSessionBinding:
    """Session binding management: owner tracking, conflict detection, recovery."""

    def __init__(self, store: RddfSessionStore):
        self._store = store

    def find_current_binding(
        self, owner_opencode_session_id: str
    ) -> Optional[RddfSession]:
        """Return the active rddf-session owned by this OpenCode session.

        Returns None if no active session is bound. If multiple active
        sessions exist for the same owner, returns the most recently
        started one.
        """
        def _do():
            data = self._store.read_unlocked()
            matches = [
                RddfSession(**s) for s in data["sessions"]
                if s["state"] == "active"
                and s["owner_opencode_session_id"] == owner_opencode_session_id
            ]
            if not matches:
                return None
            matches.sort(key=lambda s: s.started_at, reverse=True)
            return matches[0]
        return self._store.with_file_lock(_do)

    def find_next_recommendation(
        self, owner_opencode_session_id: Optional[str] = None
    ) -> Optional[RddfSession]:
        """Return the most recently started orphaned rddf-session.

        Algorithm:
          1. Filter sessions by state == "orphaned".
          2. Sort by started_at descending.
          3. Return first match.
        """
        def _do():
            data = self._store.read_unlocked()
            candidates = [
                RddfSession(**s) for s in data["sessions"]
                if s["state"] == "orphaned"
            ]
            if not candidates:
                return None
            candidates.sort(key=lambda s: s.started_at, reverse=True)
            return candidates[0]
        return self._store.with_file_lock(_do)

    def detect_conflict(
        self, kind: str, owner_opencode_session_id: str
    ) -> Optional[RddfSession]:
        """Return active session of `kind` if owned by a DIFFERENT opencode session.

        Returns None if no active session of `kind`, or if the active session
        is owned by the same opencode session id. Caller should invoke the
        4-option soft-prompt when this returns a non-None value.
        """
        if kind not in _VALID_KINDS:
            raise RddfSessionError(
                f"Invalid kind: {kind}. Must be one of {_VALID_KINDS}"
            )

        def _do_detect():
            data = self._store.read_unlocked()
            for s in data["sessions"]:
                if s["kind"] == kind and s["state"] == "active":
                    if s["owner_opencode_session_id"] != owner_opencode_session_id:
                        return RddfSession(**s)
            return None
        return self._store.with_file_lock(_do_detect)