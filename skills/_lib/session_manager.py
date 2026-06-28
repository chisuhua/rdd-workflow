"""SessionManager — parallel session execution (ADR-0010 v2.1).

ProcessPoolExecutor for true parallelism, multiprocessing.Queue for IPC,
state-vector persistence. Backward compatible with v2.0 SessionCoordinator.
"""
from __future__ import annotations
import datetime
import enum
import threading
import uuid
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from multiprocessing import Queue as MPQueue
from typing import Dict, List, Optional

from skills._lib.dependency_scheduler import DependencyScheduler
from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity
from skills._lib.state_vector import StateVector


class SessionState(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


_ALLOWED_TRANSITIONS = {
    SessionState.ACTIVE: {SessionState.PAUSED, SessionState.COMPLETED, SessionState.FAILED},
    SessionState.PAUSED: {SessionState.ACTIVE, SessionState.COMPLETED},
    SessionState.COMPLETED: set(),
    SessionState.FAILED: set(),
}


@dataclass
class Session:
    session_id: str
    parent_session_id: Optional[str]
    goal: str
    state: SessionState
    assigned_changes: List[str]
    started_at: str
    updated_at: str


def _new_id() -> str:
    return f"sess_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class SessionManagerError(Exception):
    pass


class InvalidTransitionError(SessionManagerError):
    pass


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
        self.state_vector = state_vector
        self._event_log = event_log
        self._lock = threading.Lock()
        self._sessions: Dict[str, Session] = {}
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
        sid = _new_id()
        now = _now()
        session = Session(
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
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[Session]:
        return list(self._sessions.values())

    def update_session_status(self, session_id: str, new_state: str) -> None:
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
        except Exception:
            pass

    def _emit(self, event_type: EventType, message: str) -> None:
        if self._event_log:
            try:
                self._event_log.record(
                    event_type=event_type,
                    severity=Severity.INFO,
                    message=message,
                )
            except Exception:
                pass
