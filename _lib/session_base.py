"""Shared session infrastructure for v2.0 and v2.1 session managers.

Contains common SessionState, transition rules, ID/time generators,
base Session dataclass, and error classes used by both SessionCoordinator
(v2.0) and SessionManager (v2.1).
"""

from __future__ import annotations

import datetime
import enum
import uuid
from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional


class SessionState(str, enum.Enum):
    """Lifecycle states of a workflow session."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# Allowed transitions per source state. Terminal states map to an empty set.
_ALLOWED_TRANSITIONS: Dict[SessionState, FrozenSet[SessionState]] = {
    SessionState.ACTIVE: frozenset(
        {SessionState.PAUSED, SessionState.COMPLETED, SessionState.FAILED}
    ),
    SessionState.PAUSED: frozenset({SessionState.ACTIVE, SessionState.COMPLETED}),
    SessionState.COMPLETED: frozenset(),
    SessionState.FAILED: frozenset(),
}


def _new_id() -> str:
    """Generate a unique session id of the form ``sess_<12 hex chars>``."""
    return f"sess_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    """Return current UTC time as an ISO 8601 string (with timezone)."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@dataclass
class Session:
    """A single workflow session — identified by ``session_id``, optionally
    linked to a ``parent_session_id``, holding a free-form ``goal`` string,
    and tracked through its lifecycle via :class:`SessionState`."""

    session_id: str
    parent_session_id: Optional[str]
    goal: str
    state: SessionState
    started_at: str
    updated_at: str


class SessionError(Exception):
    """Base error for session-related failures."""


class InvalidTransitionError(SessionError):
    """Raised when a session state transition is not permitted."""


class UnknownSessionError(SessionError):
    """Raised when an operation references an unknown session ID."""