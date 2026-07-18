"""Tests for skills/_lib/event_types.py — EventType, Severity enums and Event dataclass."""
import pytest
from skills._lib.core.event_types import EventType, Severity, Event


def test_event_type_values_are_unique():
    """Every EventType member must have a distinct string value (no collisions)."""
    values = [member.value for member in EventType]
    assert len(values) == len(set(values)), (
        f"EventType has duplicate values: {[v for v in values if values.count(v) > 1]}"
    )
    # All event types must be non-empty snake_case strings.
    for v in values:
        assert isinstance(v, str)
        assert v
        assert v == v.lower(), f"EventType value not lowercase: {v!r}"
        assert " " not in v, f"EventType value contains space: {v!r}"


def test_severity_ordering_and_membership():
    """Severity must contain exactly DEBUG < INFO < WARN < ERROR (by source order)."""
    members = list(Severity)
    assert [m.name for m in members] == ["DEBUG", "INFO", "WARN", "ERROR"]
    # Severity is a str enum: equality with raw strings must work.
    assert Severity.INFO == "info"
    assert Severity.ERROR == "error"


def test_event_dataclass_roundtrip():
    """Event.to_dict() then Event.from_dict() must reproduce all fields."""
    original = Event(
        event_type=EventType.LOOP_STARTED,
        severity=Severity.INFO,
        message="starting loop",
        id="evt-001",
        context={"goal": "ship v2"},
        metadata={"iteration": 1},
    )
    serialized = original.to_dict()

    assert serialized["event_type"] == "loop_started"
    assert serialized["severity"] == "info"
    assert serialized["message"] == "starting loop"
    assert serialized["id"] == "evt-001"
    assert serialized["context"] == {"goal": "ship v2"}
    assert serialized["metadata"] == {"iteration": 1}
    assert "timestamp" in serialized and serialized["timestamp"]

    restored = Event.from_dict(serialized)
    assert restored.event_type == original.event_type
    assert restored.severity == original.severity
    assert restored.message == original.message
    assert restored.id == original.id
    assert restored.context == original.context
    assert restored.metadata == original.metadata


def test_event_defaults_are_independent_per_instance():
    """Mutable defaults (context, metadata) must not be shared across Event instances."""
    e1 = Event(event_type=EventType.WARNING_ISSUED, severity=Severity.WARN, message="w1")
    e2 = Event(event_type=EventType.WARNING_ISSUED, severity=Severity.WARN, message="w2")
    e1.context["k"] = "v"
    e1.metadata["k"] = "v"
    assert e2.context == {}, "Event.context is shared between instances (mutable default bug)"
    assert e2.metadata == {}, "Event.metadata is shared between instances (mutable default bug)"