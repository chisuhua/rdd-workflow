"""Event types and severity enum for the workflow event log.

17 event types cover the full lifecycle: loop engine starts/scans/iterates,
planning/execution phases, gate transitions, errors, and lifecycle events.
"""
from __future__ import annotations
import enum
import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


class EventType(str, enum.Enum):
    """Closed set of workflow event types."""
    LOOP_STARTED = "loop_started"
    LOOP_ITERATION_STARTED = "loop_iteration_started"
    LOOP_ITERATION_COMPLETED = "loop_iteration_completed"
    LOOP_COMPLETED = "loop_completed"
    SCAN_COMPLETED = "scan_completed"
    PROPOSAL_GENERATED = "proposal_generated"
    PLAN_GENERATED = "plan_generated"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_UNIT_COMPLETED = "execution_unit_completed"
    EXECUTION_COMPLETED = "execution_completed"
    GATE_TRANSITION = "gate_transition"
    GATE_FAILED = "gate_failed"
    GATE_FORCED = "gate_forced"
    STATE_UPDATED = "state_updated"
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    USER_INPUT_REQUESTED = "user_input_requested"


class Severity(str, enum.Enum):
    """Event severity for filtering and routing."""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class Event:
    """A single workflow event. Serialized to JSONL on write."""
    event_type: EventType
    severity: Severity
    message: str
    id: str = ""  # populated by EventLog.generate_id()
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    context: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "message": self.message,
            "context": self.context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(
            id=d.get("id", ""),
            event_type=EventType(d["event_type"]),
            severity=Severity(d["severity"]),
            timestamp=d.get("timestamp", ""),
            message=d.get("message", ""),
            context=d.get("context", {}),
            metadata=d.get("metadata", {}),
        )
