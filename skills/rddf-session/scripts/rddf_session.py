"""RddfSessionCoordinator — facade over internal modules.

This file is now the public API surface. All implementation lives in
rddf_session_pkg/ submodules (types, store, commands, binding).

Original docstring:
Wraps the v2.0 SessionCoordinator concepts with:
- File-backed persistence to .rddf/state/sessions.json (atomic write via temp+rename)
- OpenCode session binding via owner_opencode_session_id
- 5-minute heartbeat refresh, 30-minute timeout → orphaned
- 4-option soft-prompt conflict detection
- Schema validation via sessions_schema.json

Backward compatibility: All public method signatures, class names, and import
paths are preserved. Consumers continue to ``from skills.rddf_session.scripts
.rddf_session import RddfSessionCoordinator``.
"""
from __future__ import annotations

# Re-export all public types from submodules so consumers can import
# from the same path as before.
from .rddf_session_pkg._types import (  # noqa: F401
    HeartbeatConfig,
    RddfSession,
    RddfSessionError,
    SchemaValidationError,
    ConflictError,
    RddfSessionState,
    SCHEMA_PATH,
    DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    HEARTBEAT_REFRESH_THRESHOLD_SECONDS,
    _VALID_KINDS,
    _VALID_STATES,
    _TERMINAL_STATES,
    _new_id,
    _now,
)
from .rddf_session_pkg._store import RddfSessionStore  # noqa: F401
from .rddf_session_pkg._commands import RddfSessionCommands  # noqa: F401
from .rddf_session_pkg._binding import RddfSessionBinding  # noqa: F401

from typing import Any, Dict, List, Optional


class RddfSessionCoordinator:
    """Persist rddf-session lifecycle to .rddf/state/sessions.json.

    Facade: delegates all operations to internal submodules. All public
    method signatures are preserved for backward compatibility.
    """

    def __init__(self, sessions_file: str,
                 config: Optional[HeartbeatConfig] = None):
        self._store = RddfSessionStore(sessions_file)
        self._commands = RddfSessionCommands(self._store,
                                              config or HeartbeatConfig())
        self._binding = RddfSessionBinding(self._store)

    # ---------- Backward-compatible private property access ----------

    @property
    def _sessions_file(self):
        return self._store._sessions_file

    def _with_file_lock(self, fn):
        return self._store.with_file_lock(fn)

    def _read_unlocked(self) -> dict:
        return self._store.read_unlocked()

    def _atomic_write(self, data: dict) -> None:
        self._store.atomic_write(data)

    # ---------- Commands (delegated) ----------

    def create_session(
        self,
        kind: str,
        owner_opencode_session_id: str,
        goal: Dict[str, Any],
        parent_session_id: Optional[str] = None,
        context_pointer: Optional[str] = None,
    ) -> str:
        return self._commands.create_session(
            kind, owner_opencode_session_id, goal,
            parent_session_id, context_pointer,
        )

    def find_session(self, session_id: str) -> Optional[RddfSession]:
        return self._commands.find_session(session_id)

    def update_session_status(
        self, session_id: str, new_state: str,
        end_reason: Optional[str] = None,
    ) -> None:
        self._commands.update_session_status(session_id, new_state, end_reason)

    def list_sessions(
        self,
        kind: Optional[str] = None,
        owner_opencode_session_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[RddfSession]:
        return self._commands.list_sessions(kind, owner_opencode_session_id, state)

    def attach_change(self, session_id: str, change_name: str) -> None:
        self._commands.attach_change(session_id, change_name)

    def detach_change(self, session_id: str, change_name: str) -> None:
        self._commands.detach_change(session_id, change_name)

    def refresh_heartbeat(self, session_id: str) -> None:
        self._commands.refresh_heartbeat(session_id)

    def check_heartbeat_timeouts(self, readonly: bool = False) -> List[str]:
        return self._commands.check_heartbeat_timeouts(readonly)

    def transfer_ownership(self, session_id: str, new_owner: str) -> None:
        self._commands.transfer_ownership(session_id, new_owner)

    def abandon(self, session_id: str) -> None:
        self._commands.abandon(session_id)

    def archive_history(self, keep: int = 20, archive_orphans: bool = False) -> int:
        return self._commands.archive_history(keep, archive_orphans=archive_orphans)

    # ---------- Polling loop (add-guide-polling-loop-implementation) ----------

    def update_last_seen_offset(self, session_id: str, new_offset: int) -> None:
        """Update goal.last_seen_offset for a stage_guide session (AC-1).

        Used by guide polling loop: after reading events from offset N to
        current end, advance last_seen_offset to N+len(events). Allows
        next poll to skip already-read events.

        Raises RddfSessionError if session is not stage_guide or not found.
        Monotonic invariant: new_offset <= current is silently no-op.
        """
        def _do_update():
            data = self._store.read_unlocked()
            for s in data["sessions"]:
                if s.get("session_id") != session_id:
                    continue
                if s.get("kind") != "stage_guide":
                    raise RddfSessionError(
                        f"Cannot update last_seen_offset on non-stage_guide session "
                        f"(kind={s.get('kind')!r})"
                    )
                current = s.get("goal", {}).get("last_seen_offset", 0)
                if new_offset <= current:
                    return  # monotonic, no rollback
                s.setdefault("goal", {})["last_seen_offset"] = new_offset
                data["updated_at"] = _now()
                self._store.atomic_write(data)
                return
            raise RddfSessionError(f"Unknown session: {session_id}")
        self._store.with_file_lock(_do_update)

    # ---------- Binding (delegated) ----------

    def find_current_binding(
        self, owner_opencode_session_id: str
    ) -> Optional[RddfSession]:
        return self._binding.find_current_binding(owner_opencode_session_id)

    def find_next_recommendation(
        self, owner_opencode_session_id: Optional[str] = None
    ) -> Optional[RddfSession]:
        return self._binding.find_next_recommendation(owner_opencode_session_id)

    def detect_conflict(
        self, kind: str, owner_opencode_session_id: str
    ) -> Optional[RddfSession]:
        return self._binding.detect_conflict(kind, owner_opencode_session_id)