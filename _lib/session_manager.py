"""SessionManager — parallel session execution (ADR-0010 v2.1).

ProcessPoolExecutor for true parallelism, multiprocessing.Queue for IPC,
state-vector persistence. Backward compatible with v2.0 SessionCoordinator.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from multiprocessing import Queue as MPQueue
from typing import Dict, List, Optional

from skills._lib.core.event_log import EventLog
from skills._lib.core.event_types import EventType, Severity
from skills._lib.session_base import (
    InvalidTransitionError,
    Session,
    SessionError,
    SessionState,
    _ALLOWED_TRANSITIONS,
    _new_id,
    _now,
)
from skills._lib.core.state_vector import StateVector

logger = logging.getLogger(__name__)


class SessionManagerError(SessionError):
    """Generic runtime error from SessionManager operations."""


@dataclass
class ManagedSession(Session):
 """Session with change assignments (v2.1 extension)."""
 assigned_changes: List[str]


class SessionManager:
    """Full parallel session manager (v2.1).

    mode='parallel' uses ProcessPoolExecutor for true parallelism.
    mode='sequential' (default) is in-process — backward compatible.
    """

    def __init__(
        self,
        state_vector: StateVector,
        event_log: Optional[EventLog] = None,
        mode: str = "sequential",
    ):
        """Initialize SessionManager with persistence and parallel infrastructure.

        Args:
            state_vector: Shared StateVector instance for session persistence.
            event_log: Shared EventLog instance for audit trail.
            max_workers: ProcessPoolExecutor worker count (default 4).
            dependencies: Optional DependencyScheduler for change ordering.
        """
        self.state_vector = state_vector
        self._event_log = event_log
        self._lock = threading.Lock()
        self._sessions: Dict[str, ManagedSession] = {}
        self._queue: MPQueue = MPQueue()
        self.mode = mode
        self.process_pool = ProcessPoolExecutor(max_workers=4) if mode == "parallel" else None

    def create_session(
        self,
        goal: str,
        mode: str = "loop",
        parent_session: Optional[str] = None,
        assigned_changes: Optional[List[str]] = None,
    ) -> str:
        """Create and persist a new session.

        Args:
            goal: Human-readable goal.
            parent_session: Optional parent session ID.
            assigned_changes: Change names to assign.

        Returns:
            Session ID of newly created session.
        """
        sid = _new_id()
        now = _now()
        session = ManagedSession(
            session_id=sid,
            parent_session_id=parent_session,
            goal=goal,
            state=SessionState.ACTIVE,
            assigned_changes=assigned_changes or [],
            started_at=now,
            updated_at=now,
        )
        with self._lock:
            self._sessions[sid] = session
        self._emit(EventType.STATE_UPDATED, f"session created: {sid}")
        self._sync_to_state_vector()
        return sid

    def find_session(self, session_id: str) -> Optional[Session]:
        """Look up a session by ID.

        Returns:
            Session if found, None otherwise.
        """
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[Session]:
        """Return all sessions.

        Returns:
            List of all Session objects.
        """
        return list(self._sessions.values())

    def update_session_status(self, session_id: str, new_state: str) -> None:
        """Transition a session to a new state.

        Args:
            session_id: Target session ID.
            new_state: Desired target state (string value of SessionState).

        Raises:
            InvalidTransitionError: If the transition is not allowed.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionManagerError(f"Unknown session: {session_id}")
            target = SessionState(new_state)
            allowed = _ALLOWED_TRANSITIONS.get(session.state, set())
            if target not in allowed:
                raise InvalidTransitionError(
                    f"Cannot transition from {session.state.value} to {new_state}"
                )
            session.state = target
            session.updated_at = _now()
        self._emit(EventType.STATE_UPDATED, f"session {session_id} -> {new_state}")
        self._sync_to_state_vector()

    def _sync_to_state_vector(self) -> None:
        """Persist session data to StateVector. Best-effort (logs on failure)."""
        try:
            active = [s for s in self._sessions.values() if s.state == SessionState.ACTIVE]
            stats = {
                "total_sessions_created": len(self._sessions),
                "active_sessions": len(active),
                "completed_sessions": sum(1 for s in self._sessions.values() if s.state == SessionState.COMPLETED),
                "failed_sessions": sum(1 for s in self._sessions.values() if s.state == SessionState.FAILED),
            }
            self.state_vector.update_field("session_management", {
                "current_session": next((s.__dict__ for s in self._sessions.values()), None),
                "active_sessions": [s.__dict__ for s in active],
                "session_statistics": stats,
            })
        except Exception as e:
            logger.warning("SessionManager: sync to state vector failed: %s", e)

    def _emit(self, event_type: EventType, message: str) -> None:
        """Record event to EventLog. Best-effort (logs on failure)."""
        if self._event_log:
            try:
                self._event_log.record(
                    event_type=event_type,
                    severity=Severity.INFO,
                    message=message,
                )
            except Exception as e:
                logger.warning("SessionManager: event log emit failed: %s", e)
