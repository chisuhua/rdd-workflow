"""Session lifecycle commands (CRUD + transitions).

Extracted from the original RddfSessionCoordinator god class.
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib

from typing import Any, Dict, List, Optional

from ._types import (
    HeartbeatConfig,
    RddfSession,
    RddfSessionError,
    _new_id,
    _now,
    _VALID_KINDS,
    _VALID_STATES,
    _TERMINAL_STATES,
    _normalize_kind,
)
from ._store import RddfSessionStore


class RddfSessionCommands:
    """Business logic for each rddf-session subcommand."""

    def __init__(self, store: RddfSessionStore, config: HeartbeatConfig):
        self._store = store
        self._config = config

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
        ConflictError).
        """
        if kind not in _VALID_KINDS:
            raise RddfSessionError(
                f"Invalid kind: {kind}. Must be one of {_VALID_KINDS}"
            )
        kind = _normalize_kind(kind)  # Normalize to canonical form
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
            data = self._store.read_unlocked()
            for existing in data["sessions"]:
                if existing["kind"] == kind and existing["state"] == "active":
                    if existing["owner_opencode_session_id"] != owner_opencode_session_id:
                        from ._types import ConflictError
                        raise ConflictError(
                            f"Active {kind} session {existing['session_id']} "
                            f"owned by {existing['owner_opencode_session_id']}; "
                            f"caller {owner_opencode_session_id} must resolve via "
                            f"4-option soft prompt"
                        )
                    return existing["session_id"]

            # Stage-level singleton: cross-stage concurrent runs race on
            # unlocked project singletons (proposal-approved.md, handoffs).
            # RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes restores legacy behavior.
            if os.environ.get("RDDF_ALLOW_CROSS_STAGE_PARALLEL", "").lower() not in ("yes", "true", "1"):
                for existing in data["sessions"]:
                    if existing["state"] == "active" and existing["kind"] != kind:
                        from ._types import ConflictError
                        raise ConflictError(
                            f"Active {existing['kind']} session {existing['session_id']} "
                            f"blocks new {kind} session (stage-level singleton). "
                            f"Resolve via skill_use('rddf-session','resume'|'abandon'), "
                            f"or set RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes to opt into "
                            f"cross-stage parallelism"
                        )

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
            self._store.atomic_write(data)
            return session.session_id

        return self._store.with_file_lock(_do_create)

    def find_session(self, session_id: str) -> Optional[RddfSession]:
        """Look up session by id. Returns a copy or None if not found."""
        def _do_find():
            data = self._store.read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    return RddfSession(**s)
            return None
        return self._store.with_file_lock(_do_find)

    def update_session_status(
        self, session_id: str, new_state: str, end_reason: Optional[str] = None
    ) -> None:
        """Transition session to new_state."""
        if new_state not in _VALID_STATES:
            raise RddfSessionError(
                f"Invalid state: {new_state}. Must be one of {_VALID_STATES}"
            )

        def _do_update():
            data = self._store.read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    is_orphaned_to_active = (s["state"] == "orphaned" and new_state == "active")
                    if s["state"] in _TERMINAL_STATES and not is_orphaned_to_active:
                        raise RddfSessionError(
                            f"Cannot transition from terminal state {s['state']!r}"
                        )
                    s["state"] = new_state
                    if new_state in _TERMINAL_STATES:
                        s["ended_at"] = _now()
                        s["end_reason"] = end_reason
                        data["updated_at"] = s["ended_at"]
                    else:
                        if is_orphaned_to_active:
                            s["ended_at"] = None
                            s["end_reason"] = None
                        s["last_heartbeat"] = _now()
                        data["updated_at"] = s["last_heartbeat"]
                    self._store.atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._store.with_file_lock(_do_update)

    def list_sessions(self, kind: Optional[str] = None) -> List[RddfSession]:
        """Return all sessions, sorted by started_at desc."""
        if kind is not None and kind not in _VALID_KINDS:
            raise RddfSessionError(
                f"Invalid kind filter: {kind}. Must be one of {_VALID_KINDS}"
            )

        def _do_list():
            data = self._store.read_unlocked()
            sessions = [RddfSession(**s) for s in data["sessions"]]
            if kind:
                sessions = [s for s in sessions if s.kind == kind]
            sessions.sort(key=lambda s: s.started_at, reverse=True)
            return sessions
        return self._store.with_file_lock(_do_list)

    def attach_change(self, session_id: str, change_name: str) -> None:
        """Add change_name to session's attached_changes (idempotent)."""
        def _do_attach():
            data = self._store.read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if change_name not in s["attached_changes"]:
                        s["attached_changes"].append(change_name)
                        s["last_heartbeat"] = _now()
                        data["updated_at"] = s["last_heartbeat"]
                        self._store.atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._store.with_file_lock(_do_attach)

    def detach_change(self, session_id: str, change_name: str) -> None:
        """Remove change_name from session's attached_changes (idempotent)."""
        def _do_detach():
            data = self._store.read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if change_name in s["attached_changes"]:
                        s["attached_changes"].remove(change_name)
                        s["last_heartbeat"] = _now()
                        data["updated_at"] = s["last_heartbeat"]
                        self._store.atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._store.with_file_lock(_do_detach)

    def refresh_heartbeat(self, session_id: str) -> None:
        """Update last_heartbeat to now. Only valid for active sessions."""
        def _do_refresh():
            data = self._store.read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if s["state"] != "active":
                        raise RddfSessionError(
                            f"Cannot refresh heartbeat on non-active session "
                            f"(state={s['state']!r})"
                        )
                    s["last_heartbeat"] = _now()
                    data["updated_at"] = s["last_heartbeat"]
                    self._store.atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._store.with_file_lock(_do_refresh)

    def check_heartbeat_timeouts(self) -> List[str]:
        """Mark active sessions with last_heartbeat > timeout as orphaned."""
        newly_orphaned: List[str] = []

        def _do_check():
            nonlocal newly_orphaned
            data = self._store.read_unlocked()
            now = datetime.datetime.now(datetime.timezone.utc)
            for s in data["sessions"]:
                if s["state"] != "active":
                    continue
                last_hb = datetime.datetime.fromisoformat(s["last_heartbeat"])
                if (now - last_hb).total_seconds() > self._config.timeout_seconds:
                    s["state"] = "orphaned"
                    s["ended_at"] = _now()
                    s["end_reason"] = "heartbeat-timeout"
                    newly_orphaned.append(s["session_id"])
            if newly_orphaned:
                data["updated_at"] = _now()
                self._store.atomic_write(data)
        self._store.with_file_lock(_do_check)
        return newly_orphaned

    def transfer_ownership(self, session_id: str, new_owner: str) -> None:
        """Transfer ownership to a new opencode session."""
        def _do_transfer():
            data = self._store.read_unlocked()
            for s in data["sessions"]:
                if s["session_id"] == session_id:
                    if s["state"] != "active":
                        raise RddfSessionError(
                            f"Cannot transfer non-active session (state={s['state']!r})"
                        )
                    s["owner_opencode_session_id"] = new_owner
                    s["last_heartbeat"] = _now()
                    data["updated_at"] = s["last_heartbeat"]
                    self._store.atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._store.with_file_lock(_do_transfer)

    def abandon(self, session_id: str) -> None:
        """Mark session as abandoned by current owner."""
        def _do_abandon():
            data = self._store.read_unlocked()
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
                    self._store.atomic_write(data)
                    return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._store.with_file_lock(_do_abandon)

    def archive_history(
        self, keep: int = 20, archive_orphans: bool = False
    ) -> int:
        """Move old terminal sessions to .archive.json.

        Non-orphan terminal sessions (completed / failed / abandoned) are
        kept up to ``keep`` most-recent by ``ended_at``. When
        ``archive_orphans`` is True, sessions in the ``orphaned`` state
        are archived regardless of the keep budget. Active sessions are
        never archived. The state machine is unchanged: ``orphaned``
        remains in ``_TERMINAL_STATES``.
        """
        archive_path = self._store._sessions_file.with_suffix(".archive.json")
        if archive_path.exists():
            archive_data = json.loads(archive_path.read_text())
        else:
            archive_data = {"version": 1, "sessions": []}

        def _do_archive():
            nonlocal archive_data
            data = self._store.read_unlocked()
            active = [s for s in data["sessions"] if s["state"] not in _TERMINAL_STATES]
            orphaned = [s for s in data["sessions"] if s["state"] == "orphaned"]
            terminal_non_orphan = [
                s for s in data["sessions"]
                if s["state"] in _TERMINAL_STATES and s["state"] != "orphaned"
            ]
            terminal_non_orphan.sort(
                key=lambda s: s.get("ended_at") or "", reverse=True
            )
            kept_terminal = terminal_non_orphan[:keep]
            to_archive = terminal_non_orphan[keep:]
            if archive_orphans:
                to_archive.extend(orphaned)
            else:
                kept_terminal.extend(orphaned)

            archive_data["sessions"].extend(to_archive)
            archive_data["updated_at"] = _now()
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            with archive_path.open("w") as f:
                json.dump(archive_data, f, indent=2)

            data["sessions"] = active + kept_terminal
            data["updated_at"] = _now()
            self._store.atomic_write(data)
            return len(to_archive)
        return self._store.with_file_lock(_do_archive)
