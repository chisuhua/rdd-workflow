"""Planner/Executor/Verifier multi-agent coordination (v2.0 advanced features).

Implements the multi-agent collaboration described in ADR-0004 § Multi-agent
collaboration. Three roles (PLANNER/EXECUTOR/VERIFIER) each address one
phase of the workflow: planning, action, and validation. Agents communicate
via the event log (shared state) and a local message buffer.

- `Agent`: low-level messaging primitive with send/receive and event-log hooks.
- `AgentCoordinator`: orchestrates three callables (planner/executor/verifier)
  in sequence, recording a STATE_UPDATED event after each step.

Public API:
    AgentRole          — enum: PLANNER | EXECUTOR | VERIFIER
    AgentMessage       — dataclass for one message (role, content, timestamp, metadata)
    Agent              — send(content, metadata) → AgentMessage; receive() → List[AgentMessage]
    AgentCoordinator   — run(goal) → (final_result, quality_score)
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity


# ─────────────────────────────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────────────────────────────


class AgentRole(str, Enum):
    """Three agent roles in the multi-agent collaboration flow."""

    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"


@dataclass
class AgentMessage:
    """A single message produced by an agent."""

    role: AgentRole
    content: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Agent
# ─────────────────────────────────────────────────────────────────────────────


class Agent:
    """Lightweight messaging primitive with optional event-log integration.

    Each Agent owns a local message buffer of messages it has sent. Calling
    `send()` also records a STATE_UPDATED event to the event log (when one
    is provided), so other agents and downstream observers can observe the
    flow via shared state.
    """

    def __init__(self, role: AgentRole, event_log: Optional[EventLog] = None):
        self.role = role
        self._event_log = event_log
        self._sent: List[AgentMessage] = []

    def send(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentMessage:
        """Send a message. Stores locally and (optionally) records an event."""
        msg = AgentMessage(
            role=self.role,
            content=content,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            metadata=dict(metadata) if metadata else {},
        )
        self._sent.append(msg)

        if self._event_log is not None:
            self._event_log.record(
                EventType.STATE_UPDATED,
                Severity.INFO,
                f"{self.role.value} sent message",
                context={
                    "role": self.role.value,
                    "content": msg.content,
                    "metadata": msg.metadata,
                    "timestamp": msg.timestamp,
                },
                metadata={"step": self.role.value},
            )

        return msg

    def receive(self) -> List[AgentMessage]:
        """Return messages this agent has sent (local buffer view).

        Per spec, an agent's view is its own sent messages plus any messages
        in shared state. The local buffer exposes the messages it produced;
        cross-agent visibility is mediated via the event log (queryable by
        other components) and the coordinator's shared message bus.
        """
        return list(self._sent)


# ─────────────────────────────────────────────────────────────────────────────
# Coordinator
# ─────────────────────────────────────────────────────────────────────────────


# Type aliases for the three role callables (document the contract)
PlannerFn = Callable[[str], str]
ExecutorFn = Callable[[str], str]
VerifierFn = Callable[[str], float]


class AgentCoordinator:
    """Orchestrates Planner → Executor → Verifier in sequence.

    Each step records a STATE_UPDATED event to the event log so the
    full multi-agent flow is observable downstream. Returns
    (final_result, quality_score).
    """

    def __init__(
        self,
        event_log: EventLog,
        planner: PlannerFn,
        executor: ExecutorFn,
        verifier: VerifierFn,
    ):
        self._event_log = event_log
        self._planner = planner
        self._executor = executor
        self._verifier = verifier

    def run(self, goal: str) -> Tuple[str, float]:
        """Execute Planner → Executor → Verifier on `goal`.

        Returns:
            (final_result, quality_score). `final_result` is the executor's
            output; `quality_score` is the verifier's score in [0.0, 1.0].
        """
        # Planner
        plan = self._planner(goal)
        self._record_step("planner", goal, plan)

        # Executor
        execution_result = self._executor(plan)
        self._record_step("executor", plan, execution_result)

        # Verifier
        score = self._verifier(execution_result)
        self._record_step("verifier", execution_result, score)

        return execution_result, score

    def _record_step(self, step: str, input_value: Any, output_value: Any) -> None:
        """Record a STATE_UPDATED event for one coordinator step."""
        self._event_log.record(
            EventType.STATE_UPDATED,
            Severity.INFO,
            f"coordinator step: {step}",
            context={
                "step": step,
                "input": input_value,
                "output": output_value,
            },
            metadata={"step": step},
        )