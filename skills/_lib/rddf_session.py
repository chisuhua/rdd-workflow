"""RddfSessionCoordinator — user-perspective workflow session persistence (ADR-0017).

Wraps the v2.0 SessionCoordinator concepts with:
- File-backed persistence to .rddf/state/sessions.json (atomic write via temp+rename)
- OpenCode session binding via owner_opencode_session_id
- 5-minute heartbeat refresh, 30-minute timeout → orphaned
- 4-option soft-prompt conflict detection
- Schema validation via sessions_schema.json

Backward compatibility: does NOT modify SessionCoordinator / SessionManager APIs.
The rddf-session is a user-layer abstraction overlay.

Platform note: this module uses fcntl.flock for advisory file locking, which is
POSIX-only. On Windows the lock call will raise AttributeError; callers running
on Windows should use a different locking mechanism (e.g. msvcrt).
"""
from __future__ import annotations

import datetime
import enum
import json
import os
import pathlib
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "sessions_schema.json"
DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 30 * 60  # 30 minutes
HEARTBEAT_REFRESH_THRESHOLD_SECONDS = 5 * 60  # 5 minutes
LOCK_TIMEOUT_SECONDS = 5.0

_VALID_KINDS = ("stage_arch", "stage_plan", "stage_ship")
_VALID_STATES = ("active", "completed", "failed", "orphaned", "abandoned")
_TERMINAL_STATES = frozenset(("completed", "failed", "abandoned"))


class RddfSessionState(str, enum.Enum):
    """Lifecycle states of an rddf-session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ORPHANED = "orphaned"
    ABANDONED = "abandoned"


class RddfSessionError(Exception):
    """Base error for rddf-session operations."""


class SchemaValidationError(RddfSessionError):
    """Raised when sessions.json fails schema validation."""


class ConflictError(RddfSessionError):
    """Raised on cross-opencode-session conflict (caller must invoke 4-option prompt)."""


def _new_id() -> str:
    """Generate rds_<12 hex chars>."""
    return f"rds_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    """ISO 8601 UTC timestamp with timezone."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@dataclass
class RddfSession:
    """A single rddf-session record (mirrors ADR-0017 schema)."""

    session_id: str
    kind: str
    owner_opencode_session_id: Optional[str]
    parent_session_id: Optional[str] = None
    goal: Dict[str, Any] = field(default_factory=dict)
    state: str = "active"
    attached_changes: List[str] = field(default_factory=list)
    context_pointer: Optional[str] = None
    started_at: str = ""
    last_heartbeat: str = ""
    ended_at: Optional[str] = None
    end_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class RddfSessionCoordinator:
    """Persist rddf-session lifecycle to .rddf/state/sessions.json."""

    def __init__(self, sessions_file: str):
        self._sessions_file = pathlib.Path(sessions_file)
        self._lock_file = self._sessions_file.with_suffix(".lock")

    # ---------- File I/O ----------

    def _read_unlocked(self) -> dict:
        """Read sessions.json. Returns empty structure if missing."""
        if not self._sessions_file.exists():
            return {"version": 1, "sessions": []}
        with self._sessions_file.open("r") as f:
            return json.load(f)

    def _atomic_write(self, data: dict) -> None:
        """Write sessions.json atomically (write-to-tmp + rename)."""
        self._sessions_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._sessions_file.with_suffix(".json.tmp")
        with tmp_path.open("w") as f:
            json.dump(data, f, indent=2, sort_keys=False)
        os.replace(tmp_path, self._sessions_file)

    def _with_file_lock(self, fn):
        """Acquire advisory file lock, run fn, release.

        POSIX-only (uses fcntl.flock). On Windows, callers should wrap with
        a different locking strategy or run inside WSL.
        """
        import fcntl  # POSIX-only
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

    # ---------- Public API: create_session ----------

    def create_session(
        self,
        kind: str,
        owner_opencode_session_id: str,
        goal: Dict[str, Any],
        parent_session_id: Optional[str] = None,
        context_pointer: Optional[str] = None,
    ) -> str:
        """Create a new rddf-session and persist.

        Returns the new (or existing same-owner) session_id. Fails if an active
        session of the same kind exists with a DIFFERENT owner (raises
        ConflictError — caller should invoke 4-option soft prompt).
        """
        if kind not in _VALID_KINDS:
            raise RddfSessionError(
                f"Invalid kind: {kind}. Must be one of {_VALID_KINDS}"
            )
        if not isinstance(goal, dict):
            raise RddfSessionError(
                f"goal must be dict, got {type(goal).__name__}"
            )
        if parent_session_id is not None and not (
            isinstance(parent_session_id, str)
            and parent_session_id.startswith("rds_")
            and len(parent_session_id) == 16
        ):
            raise RddfSessionError(
                f"parent_session_id must be rds_<12 hex>, got {parent_session_id!r}"
            )

        def _do_create():
            data = self._read_unlocked()
            # Check for active conflict (same kind + active state)
            for existing in data["sessions"]:
                if existing["kind"] == kind and existing["state"] == "active":
                    if existing["owner_opencode_session_id"] != owner_opencode_session_id:
                        raise ConflictError(
                            f"Active {kind} session {existing['session_id']} "
                            f"owned by {existing['owner_opencode_session_id']}; "
                            f"caller {owner_opencode_session_id} must resolve via "
                            f"4-option soft prompt"
                        )
                    # Same owner — reuse existing session id
                    return existing["session_id"]

            # Create new session
            now = _now()
            session = RddfSession(
                session_id=_new_id(),
                kind=kind,
                owner_opencode_session_id=owner_opencode_session_id,
                parent_session_id=parent_session_id,
                goal=goal,
                state="active",
                context_pointer=context_pointer,
                started_at=now,
                last_heartbeat=now,
            )
            data["sessions"].append(session.to_dict())
            data["updated_at"] = now
            self._atomic_write(data)
            return session.session_id

        return self._with_file_lock(_do_create)

    # ---------- Placeholder methods (filled in later tasks 4-7) ----------

    def find_session(self, session_id: str) -> Optional[RddfSession]:
        raise NotImplementedError("Implemented in Task 4")

    def update_session_status(
        self, session_id: str, new_state: str, end_reason: Optional[str] = None
    ) -> None:
        raise NotImplementedError("Implemented in Task 4")

    def list_sessions(self, kind: Optional[str] = None) -> List[RddfSession]:
        raise NotImplementedError("Implemented in Task 4")

    def attach_change(self, session_id: str, change_name: str) -> None:
        raise NotImplementedError("Implemented in Task 5")

    def detach_change(self, session_id: str, change_name: str) -> None:
        raise NotImplementedError("Implemented in Task 5")

    def refresh_heartbeat(self, session_id: str) -> None:
        raise NotImplementedError("Implemented in Task 5")

    def check_heartbeat_timeouts(self) -> List[str]:
        raise NotImplementedError("Implemented in Task 6")

    def detect_conflict(
        self, kind: str, owner_opencode_session_id: str
    ) -> Optional[RddfSession]:
        raise NotImplementedError("Implemented in Task 6")

    def transfer_ownership(self, session_id: str, new_owner: str) -> None:
        raise NotImplementedError("Implemented in Task 7")

    def abandon(self, session_id: str) -> None:
        raise NotImplementedError("Implemented in Task 7")

    def archive_history(self, keep: int = 20) -> int:
        raise NotImplementedError("Implemented in Task 7")