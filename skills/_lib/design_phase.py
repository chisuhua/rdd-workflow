"""Design-first phase — Goal, Verification, Control design before loop starts."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity


@dataclass
class DesignResult:
    """User-confirmed design across 3 dimensions.

    Goal: deliverables + completion_criteria
    Verification: executor + reviewer agent names
    Control: max_iterations + max_retries + oscillation_threshold
    """

    goal: dict = field(
        default_factory=lambda: {"deliverables": [], "completion_criteria": ""}
    )
    verification: dict = field(
        default_factory=lambda: {"executor": "deep", "reviewer": "oracle"}
    )
    control: dict = field(
        default_factory=lambda: {
            "max_iterations": 100,
            "max_retries": 3,
            "oscillation_threshold": 2,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict for state vector storage."""
        return asdict(self)


class DesignPhase:
    """Pre-loop design phase. Runs once before loop starts.

    Allows user to confirm or modify three design dimensions:
    - Goal Design (deliverables + completion criteria)
    - Verification Design (Executor/Reviewer agents)
    - Control Design (max_iterations, max_retries, oscillation threshold)

    Results persist to state vector under loop_state.design.
    """

    DIMENSIONS: tuple[str, ...] = ("goal", "verification", "control")

    DEFAULTS: dict[str, dict[str, Any]] = {
        "goal": {
            "deliverables": [],
            "completion_criteria": "",
        },
        "verification": {
            "executor": "deep",
            "reviewer": "oracle",
        },
        "control": {
            "max_iterations": 100,
            "max_retries": 3,
            "oscillation_threshold": 2,
        },
    }

    def __init__(self, state: StateVector, event_log: EventLog) -> None:
        self.state = state
        self.event_log = event_log

    def list_dimensions(self) -> list[str]:
        """Return the three design dimensions in canonical order."""
        return list(self.DIMENSIONS)

    def default_for(self, dimension: str) -> dict[str, Any]:
        """Return a fresh copy of the default dict for a dimension."""
        return dict(self.DEFAULTS.get(dimension, {}))

    def apply(self, result: DesignResult) -> None:
        """Persist design result to state vector and record event."""
        design_dict = result.to_dict()
        self.state.update_field("loop_state.design", design_dict)
        self.event_log.record(
            EventType.STATE_UPDATED,
            Severity.INFO,
            "design phase applied",
            context=design_dict,
        )
