"""SessionCoordinator — lightweight v2.0 sequential session coordination.

Per ADR-0010 (Multi-Session Management), the long-term intent is to store
sessions in the state vector under ``session_info`` (the active session)
and ``sub_sessions`` (its children) — see tasks.md §5.1 and the ADR §"扩展
状态向量 Schema". However, the v2.0 state vector schema
(``state_vector_schema.json``) declares ``additionalProperties: false`` at
both the root and the ``loop_state`` level, so directly calling
``state_vector.update_field("session_info", ...)`` fails validation.

v2.0 (this module) therefore holds session data **in memory** within the
``SessionCoordinator`` instance, backed by a reference to the ``StateVector``
for context (goal, parent loop state). The public API is identical to what
the schema-integrated v2.1 implementation will expose, so callers (the loop
engine, the agents module) can use it today and migrate transparently once
the schema is extended.

**v2.0 is sequential.** Sub-sessions block their parent implicitly: the
parent's loop engine polls ``find_session(child_id).state`` and only
proceeds when the child reaches a terminal state (``COMPLETED`` or
``FAILED``). v2.1 will introduce true parallel execution with explicit
synchronization primitives; the API will remain backwards-compatible.

State machine
-------------
- ``active → paused`` and ``active → completed`` and ``active → failed``
- ``paused → active`` and ``paused → completed``
- ``completed`` and ``failed`` are terminal (no outgoing transitions)
- All other transitions raise :class:`InvalidTransitionError`.
"""
from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional

from skills._lib.event_types import EventType, Severity
from skills._lib.event_log import EventLog
from skills._lib.session_base import (
    InvalidTransitionError,
    Session,
    SessionError,
    SessionState,
    UnknownSessionError,
    _ALLOWED_TRANSITIONS,
    _new_id,
    _now,
)
from skills._lib.state_vector import StateVector

logger = logging.getLogger(__name__)


class SessionCoordinatorError(SessionError):
    """Base error for session coordination failures."""


class SessionCoordinator:
    """Lightweight sequential session coordinator (v2.0).

    See module docstring for storage and concurrency notes. The class is
    thread-safe: all internal mutations are guarded by a single lock, so
    concurrent ``create_session`` / ``update_session_status`` calls from
    the loop engine and the agents module cannot race.
    """

    def __init__(
        self,
        state_vector: StateVector,
        event_log: Optional[EventLog] = None,
    ) -> None:
        # `state_vector` is held for context (read the user's goal, surface
        # the active session in the loop-state view). v2.0 does not write
        # session data through it; see module docstring.
        self._state_vector: StateVector = state_vector
        self._event_log: Optional[EventLog] = event_log
        self._lock: threading.Lock = threading.Lock()
        self._sessions: Dict[str, Session] = {}

    # ----- Read helpers -------------------------------------------------

    @property
    def state_vector(self) -> StateVector:
        """Return the state vector the coordinator is bound to."""
        return self._state_vector

    # ----- Mutation -----------------------------------------------------

    def create_session(
        self, goal: str, parent_session_id: Optional[str] = None
    ) -> Session:
        """Create and register a new session in state ``ACTIVE``.

        Args:
            goal: Free-form human-readable description of what the session
                is trying to achieve. Stored verbatim on the session.
            parent_session_id: Optional id of a parent session; used to
                build the parent/child tree. ``None`` for top-level
                sessions.

        Returns:
            The newly created :class:`Session`.

        Raises:
            UnknownSessionError: if ``parent_session_id`` is given but does
                not match any known session.
        """
        if not isinstance(goal, str):
            raise SessionCoordinatorError(
                f"goal must be str, got {type(goal).__name__}"
            )
        now: str = _now()
        session: Session = Session(
            session_id=_new_id(),
            parent_session_id=parent_session_id,
            goal=goal,
            state=SessionState.ACTIVE,
            started_at=now,
            updated_at=now,
        )
        with self._lock:
            if parent_session_id is not None and parent_session_id not in self._sessions:
                raise UnknownSessionError(
                    f"parent_session_id {parent_session_id!r} does not match any known session"
                )
            self._sessions[session.session_id] = session
        self._emit(EventType.STATE_UPDATED, f"session created: {session.session_id}")
        return session

    def find_session(self, session_id: str) -> Optional[Session]:
        """Look up a session by id. Returns ``None`` if not found."""
        if not isinstance(session_id, str):
            return None
        with self._lock:
            # Return a copy so external mutations don't corrupt internal state.
            s = self._sessions.get(session_id)
            if s is None:
                return None
            return Session(
                session_id=s.session_id,
                parent_session_id=s.parent_session_id,
                goal=s.goal,
                state=s.state,
                started_at=s.started_at,
                updated_at=s.updated_at,
            )

    def update_session_status(
        self, session_id: str, new_state: SessionState
    ) -> None:
        """Transition a session to ``new_state``.

        Args:
            session_id: Id of the session to update.
            new_state: Target state.

        Raises:
            UnknownSessionError: if ``session_id`` is not known.
            InvalidTransitionError: if the transition is not allowed by
                the state machine.
        """
        if isinstance(new_state, str):
            new_state = SessionState(new_state)
        with self._lock:
            session: Optional[Session] = self._sessions.get(session_id)
            if session is None:
                raise UnknownSessionError(
                    f"session_id {session_id!r} is not known to this coordinator"
                )
            allowed: frozenset[SessionState] = _ALLOWED_TRANSITIONS[session.state]
            if new_state not in allowed:
                raise InvalidTransitionError(
                    f"cannot transition session {session_id!r} "
                    f"from {session.state.value!r} to {new_state.value!r}"
                )
            session.state = new_state
            session.updated_at = _now()
        self._emit(
            EventType.STATE_UPDATED,
            f"session {session_id} → {new_state.value}",
        )

    def list_sessions(
        self, parent_session_id: Optional[str] = None
    ) -> List[Session]:
        """Return a snapshot list of sessions, optionally filtered to those
        whose ``parent_session_id`` matches the given value.

        With ``parent_session_id=None``, returns **all** sessions (top-level
        and children alike). To list only top-level sessions, the caller can
        filter on ``parent_session_id is None`` post hoc.
        """
        with self._lock:
            if parent_session_id is None:
                snapshot: List[Session] = list(self._sessions.values())
            else:
                snapshot: List[Session] = [
                    s for s in self._sessions.values()
                    if s.parent_session_id == parent_session_id
                ]
        return [
            Session(
                session_id=s.session_id,
                parent_session_id=s.parent_session_id,
                goal=s.goal,
                state=s.state,
                started_at=s.started_at,
                updated_at=s.updated_at,
            )
            for s in snapshot
        ]

    # ----- Event integration -------------------------------------------

    def _emit(self, event_type: EventType, message: str) -> None:
        """Best-effort event-log emission; never raises."""
        if self._event_log is None:
            return
        try:
            self._event_log.record(
                event_type=event_type,
                severity=Severity.INFO,
                message=message,
            )
        except Exception:
            self._event_log.record(EventType.ERROR_OCCURRED, Severity.WARN, "Session: event log emit failed")
