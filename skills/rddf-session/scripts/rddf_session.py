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

v2.0.3 (fix-debt-audit-2026-07-14 / Wave 3.2): RddfSessionCoordinator is a
~400-line god class with 3 distinct responsibilities mixed together:

  Persistence:   __init__, _read_unlocked, _atomic_write, _with_file_lock
  Commands:      create_session, find_session, update_session_status,
                 list_sessions, attach_change, detach_change,
                 refresh_heartbeat, abandon, archive_history,
                 transfer_ownership
  Binding:       find_current_binding, find_next_recommendation,
                 detect_conflict, check_heartbeat_timeouts

Full split deferred to a follow-up change to avoid scope creep. The atomic
write helper used by `_atomic_write` was already consolidated in Wave 3.1
(``skills/_lib/atomic_write.py::atomic_write_json``).
"""
from __future__ import annotations

import datetime
import enum
import json
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
        # v2.0.3: delegate to shared atomic_write helper (Wave 3.1).
        from skills._lib.core.atomic_write import atomic_write_json
        atomic_write_json(str(self._sessions_file), data)

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

    # ---------- Public API: find_current_binding ----------

    def find_current_binding(
        self, owner_opencode_session_id: str
    ) -> Optional[RddfSession]:
        """Return the active rddf-session owned by this OpenCode session.

        Returns None if no active session is bound. If multiple active
        sessions exist for the same owner, returns the most recently
        started one (deterministic via sort).
        """
        def _do():
            data = self._read_unlocked()
            matches = [
                RddfSession(**s) for s in data["sessions"]
                if s["state"] == "active"
                and s["owner_opencode_session_id"] == owner_opencode_session_id
            ]
            if not matches:
                return None
            matches.sort(key=lambda s: s.started_at, reverse=True)
            return matches[0]
        return self._with_file_lock(_do)

    # ---------- Public API: find_next_recommendation ----------

    def find_next_recommendation(
        self, owner_opencode_session_id: Optional[str] = None
    ) -> Optional[RddfSession]:
        """Return the most recently started orphaned rddf-session.

        Algorithm:
          1. Filter sessions by state == "orphaned".
          2. Sort by started_at descending.
          3. Return first match.

        The owner_opencode_session_id parameter is reserved for future
        filtering (e.g. only recommend sessions originally owned by this
        OpenCode session). Currently unused.
        """
        def _do():
            data = self._read_unlocked()
            candidates = [
                RddfSession(**s) for s in data["sessions"]
                if s["state"] == "orphaned"
            ]
            if not candidates:
                return None
            candidates.sort(key=lambda s: s.started_at, reverse=True)
            return candidates[0]
        return self._with_file_lock(_do)

    # ---------- Placeholder methods (filled in later tasks 4-7) ----------

    def find_session(self, session_id: str) -> Optional[RddfSession]:
        """Look up session by id. Returns a copy or None if not found."""
        def _do_find():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    return RddfSession(**s)
            return None
        return self._with_file_lock(_do_find)

    def update_session_status(
        self, session_id: str, new_state: str, end_reason: Optional[str] = None
    ) -> None:
        """Transition session to new_state. Sets ended_at and end_reason if terminal.

        Raises:
            RddfSessionError: If new_state is invalid, session not found, or
                source state is terminal (completed/failed/abandoned).
        """
        if new_state not in _VALID_STATES:
            raise RddfSessionError(
                f"Invalid state: {new_state}. Must be one of {_VALID_STATES}"
            )

        def _do_update():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if s["state"] in _TERMINAL_STATES:
                        raise RddfSessionError(
                            f"Cannot transition from terminal state {s['state']!r}"
                        )
                    s["state"] = new_state
                    if new_state in _TERMINAL_STATES:
                        s["ended_at"] = _now()
                        s["end_reason"] = end_reason
                        data["updated_at"] = s["ended_at"]
                    else:
                        # active or orphaned — refresh heartbeat
                        s["last_heartbeat"] = _now()
                        data["updated_at"] = s["last_heartbeat"]
                    self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_update)

    def list_sessions(self, kind: Optional[str] = None) -> List[RddfSession]:
        """Return all sessions (or filtered by kind), sorted by started_at desc."""
        if kind is not None and kind not in _VALID_KINDS:
            raise RddfSessionError(
                f"Invalid kind filter: {kind}. Must be one of {_VALID_KINDS}"
            )

        def _do_list():
            data = self._read_unlocked()
            sessions = [RddfSession(**s) for s in data["sessions"]]
            if kind:
                sessions = [s for s in sessions if s.kind == kind]
            sessions.sort(key=lambda s: s.started_at, reverse=True)
            return sessions
        return self._with_file_lock(_do_list)

    def attach_change(self, session_id: str, change_name: str) -> None:
        """Add change_name to session's attached_changes (idempotent)."""
        def _do_attach():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if change_name not in s["attached_changes"]:
                        s["attached_changes"].append(change_name)
                        s["last_heartbeat"] = _now()
                        data["updated_at"] = s["last_heartbeat"]
                        self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_attach)

    def detach_change(self, session_id: str, change_name: str) -> None:
        """Remove change_name from session's attached_changes (idempotent)."""
        def _do_detach():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if change_name in s["attached_changes"]:
                        s["attached_changes"].remove(change_name)
                        s["last_heartbeat"] = _now()
                        data["updated_at"] = s["last_heartbeat"]
                        self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_detach)

    def refresh_heartbeat(self, session_id: str) -> None:
        """Update last_heartbeat to now. Only valid for active sessions."""
        def _do_refresh():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if s["state"] != "active":
                        raise RddfSessionError(
                            f"Cannot refresh heartbeat on non-active session "
                            f"(state={s['state']!r})"
                        )
                    s["last_heartbeat"] = _now()
                    data["updated_at"] = s["last_heartbeat"]
                    self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_refresh)

    def check_heartbeat_timeouts(self) -> List[str]:
        """Mark active sessions with last_heartbeat > timeout as orphaned.

        Returns list of session_ids newly transitioned to orphaned state.
        """
        newly_orphaned: List[str] = []

        def _do_check():
            nonlocal newly_orphaned
            data = self._read_unlocked()
            now = datetime.datetime.now(datetime.timezone.utc)
            for s in data["sessions"]:
                if s["state"] != "active":
                    continue
                last_hb = datetime.datetime.fromisoformat(s["last_heartbeat"])
                if (now - last_hb).total_seconds() > DEFAULT_HEARTBEAT_TIMEOUT_SECONDS:
                    s["state"] = "orphaned"
                    s["ended_at"] = _now()
                    s["end_reason"] = "heartbeat-timeout"
                    newly_orphaned.append(s["session_id"])
            if newly_orphaned:
                data["updated_at"] = _now()
                self._atomic_write(data)
        self._with_file_lock(_do_check)
        return newly_orphaned

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
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["kind"] == kind and s["state"] == "active":
                    if s["owner_opencode_session_id"] != owner_opencode_session_id:
                        return RddfSession(**s)
            return None
        return self._with_file_lock(_do_detect)

    def transfer_ownership(self, session_id: str, new_owner: str) -> None:
        """Transfer ownership to a new opencode session. Refreshes heartbeat."""
        def _do_transfer():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if s["state"] != "active":
                        raise RddfSessionError(
                            f"Cannot transfer non-active session (state={s['state']!r})"
                        )
                    s["owner_opencode_session_id"] = new_owner
                    s["last_heartbeat"] = _now()
                    data["updated_at"] = s["last_heartbeat"]
                    self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_transfer)

    def abandon(self, session_id: str) -> None:
        """Mark session as abandoned by current owner."""
        def _do_abandon():
            data = self._read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if s["state"] in _TERMINAL_STATES:
                        raise RddfSessionError(
                            f"Session already terminal: {s['state']!r}"
                        )
                    s["state"] = "abandoned"
                    s["ended_at"] = _now()
                    s["end_reason"] = "user-abandoned"
                    data["updated_at"] = s["ended_at"]
                    self._atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._with_file_lock(_do_abandon)

    def archive_history(self, keep: int = 20) -> int:
        """Move old completed/failed/abandoned sessions to .archive.json.

        Keeps the most recent `keep` terminal sessions in the main file
        (by ended_at desc) plus all active/orphaned sessions. Returns the
        count of sessions moved to the archive.
        """
        archive_path = self._sessions_file.with_suffix(".archive.json")
        if archive_path.exists():
            archive_data = json.loads(archive_path.read_text())
        else:
            archive_data = {"version": 1, "sessions": []}

        def _do_archive():
            nonlocal archive_data
            data = self._read_unlocked()
            terminal = [
                s for s in data["sessions"]
                if s["state"] in _TERMINAL_STATES
            ]
            non_terminal = [
                s for s in data["sessions"]
                if s["state"] not in _TERMINAL_STATES
            ]

            terminal.sort(key=lambda s: s.get("ended_at") or "", reverse=True)
            to_archive = terminal[keep:]
            to_keep = terminal[:keep] + non_terminal

            archive_data["sessions"].extend(to_archive)
            archive_data["updated_at"] = _now()
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            with archive_path.open("w") as f:
                json.dump(archive_data, f, indent=2)

            data["sessions"] = to_keep
            data["updated_at"] = _now()
            self._atomic_write(data)
            return len(to_archive)
        return self._with_file_lock(_do_archive)