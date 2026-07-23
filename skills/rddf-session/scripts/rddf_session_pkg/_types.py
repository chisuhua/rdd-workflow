"""Type definitions and constants for rddf-session.

Extracted from the original RddfSessionCoordinator god class
(split-rddf-god-class change).
"""
from __future__ import annotations

import datetime
import enum
import json
import os
import uuid

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "sessions_schema.json"
DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 30 * 60  # 30 minutes
HEARTBEAT_REFRESH_THRESHOLD_SECONDS = 5 * 60  # 5 minutes
LOCK_TIMEOUT_SECONDS = 5.0

# v2.1: Accept both naming conventions for better UX
# - stage_arch / stage_plan / stage_ship (internal canonical)
# - guide-arch / guide-plan / guide-ship (user-friendly, matches skill names)
_VALID_KINDS = ("stage_arch", "stage_plan", "stage_ship", "guide-arch", "guide-plan", "guide-ship")
_KIND_ALIAS = {
    "guide-arch": "stage_arch",
    "guide-plan": "stage_plan",
    "guide-ship": "stage_ship",
}


def _normalize_kind(kind: str) -> str:
    """Normalize kind to canonical internal form."""
    return _KIND_ALIAS.get(kind, kind)


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


@dataclass
class HeartbeatConfig:
    """Configurable heartbeat timeout threshold, parsed from env vars.

    Defaults match the module-level constants. Use ``from_env()`` to
    override from ``RDDF_HEARTBEAT_TIMEOUT_SECONDS`` and
    ``RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS`` environment variables.
    """

    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS
    refresh_threshold_seconds: int = HEARTBEAT_REFRESH_THRESHOLD_SECONDS

    @staticmethod
    def from_env() -> "HeartbeatConfig":
        timeout = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS
        threshold = HEARTBEAT_REFRESH_THRESHOLD_SECONDS

        raw = os.environ.get("RDDF_HEARTBEAT_TIMEOUT_SECONDS", "")
        if raw:
            try:
                parsed = int(raw)
                if parsed > 0:
                    timeout = parsed
            except ValueError:
                pass  # illegal value → fall back to default

        raw = os.environ.get("RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS", "")
        if raw:
            try:
                parsed = int(raw)
                if parsed > 0:
                    threshold = parsed
            except ValueError:
                pass

        return HeartbeatConfig(timeout_seconds=timeout, refresh_threshold_seconds=threshold)