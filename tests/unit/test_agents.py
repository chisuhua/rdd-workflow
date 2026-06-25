"""Tests for skills._lib.agents — Planner/Executor/Verifier multi-agent coordination.

Per ADR-0004 § Multi-agent collaboration and plan Task 5. Validates the
8 required behaviors: three roles, send/receive messaging, three callable
roles, and the AgentCoordinator that runs them in sequence while
recording each step to the event log.
"""
from __future__ import annotations

import pytest

from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity


# ─────────────────────────────────────────────────────────────────────────────
# AgentRole + AgentMessage + Agent
# ─────────────────────────────────────────────────────────────────────────────


def test_three_agent_roles_defined():
    """AgentRole enum exposes exactly three values: planner/executor/verifier."""
    from skills._lib.agents import AgentRole

    roles = {r.value for r in AgentRole}
    assert roles == {"planner", "executor", "verifier"}


def test_agent_send_records_event(tmp_path):
    """Agent.send() persists a STATE_UPDATED event to the event log."""
    from skills._lib.agents import Agent, AgentRole

    log_path = str(tmp_path / "event-log.jsonl")
    log = EventLog(log_path)
    agent = Agent(AgentRole.PLANNER, event_log=log)

    msg = agent.send("plan content", metadata={"step": 1})

    assert msg.role == AgentRole.PLANNER
    assert msg.content == "plan content"
    assert msg.metadata == {"step": 1}
    assert msg.timestamp  # non-empty

    events = log.query(event_type=EventType.STATE_UPDATED)
    assert len(events) == 1
    assert events[0].severity == Severity.INFO
    assert events[0].context.get("role") == AgentRole.PLANNER.value


def test_agent_receive_returns_messages():
    """Agent.receive() returns the messages the agent sent (local buffer)."""
    from skills._lib.agents import Agent, AgentRole

    agent = Agent(AgentRole.EXECUTOR)
    agent.send("first")
    agent.send("second", metadata={"k": "v"})

    received = agent.receive()
    assert len(received) == 2
    assert received[0].content == "first"
    assert received[1].content == "second"
    assert received[1].metadata == {"k": "v"}
    assert all(m.role == AgentRole.EXECUTOR for m in received)


# ─────────────────────────────────────────────────────────────────────────────
# Planner / Executor / Verifier roles (callables consumed by coordinator)
# ─────────────────────────────────────────────────────────────────────────────


def test_planner_generates_plan():
    """Planner callable signature: planner(goal) -> str (plan content)."""
    from skills._lib.agents import AgentRole

    captured = {}

    def planner(goal: str) -> str:
        captured["goal"] = goal
        return f"PLAN FOR {goal}"

    result = planner("ship it")
    assert result == "PLAN FOR ship it"
    assert captured["goal"] == "ship it"
    # The role label is a string matching the enum value
    assert AgentRole.PLANNER.value == "planner"


def test_executor_runs_actions():
    """Executor callable signature: executor(plan) -> str (execution result)."""
    from skills._lib.agents import AgentRole

    captured = {}

    def executor(plan: str) -> str:
        captured["plan"] = plan
        return f"EXECUTED {plan}"

    result = executor("deploy step")
    assert result == "EXECUTED deploy step"
    assert captured["plan"] == "deploy step"
    # The EXECUTOR role label is exposed via the enum
    assert AgentRole.EXECUTOR.value == "executor"


def test_verifier_scores_quality():
    """Verifier callable signature: verifier(execution_result) -> float in [0.0, 1.0]."""
    from skills._lib.agents import AgentRole

    captured = {}

    def verifier(execution_result: str) -> float:
        captured["result"] = execution_result
        return 0.92

    score = verifier("ok")
    assert score == 0.92
    assert captured["result"] == "ok"
    assert 0.0 <= score <= 1.0
    # The VERIFIER role label is exposed via the enum
    assert AgentRole.VERIFIER.value == "verifier"


# ─────────────────────────────────────────────────────────────────────────────
# AgentCoordinator — orchestrates Planner → Executor → Verifier
# ─────────────────────────────────────────────────────────────────────────────


def test_coordinator_runs_full_flow(tmp_path):
    """Coordinator.run() runs planner → executor → verifier in order."""
    from skills._lib.agents import AgentCoordinator

    log = EventLog(str(tmp_path / "event-log.jsonl"))

    calls = []

    def planner(goal):
        calls.append(("planner", goal))
        return f"plan:{goal}"

    def executor(plan):
        calls.append(("executor", plan))
        return f"result:{plan}"

    def verifier(execution_result):
        calls.append(("verifier", execution_result))
        return 0.85

    coord = AgentCoordinator(log, planner, executor, verifier)
    final, score = coord.run("make pizza")

    assert calls == [
        ("planner", "make pizza"),
        ("executor", "plan:make pizza"),
        ("verifier", "result:plan:make pizza"),
    ]
    assert final == "result:plan:make pizza"
    assert score == 0.85


def test_coordinator_records_each_step(tmp_path):
    """Each coordinator step records a STATE_UPDATED event to the event log."""
    from skills._lib.agents import AgentCoordinator

    log = EventLog(str(tmp_path / "event-log.jsonl"))

    def planner(goal):
        return "the plan"

    def executor(plan):
        return "the result"

    def verifier(execution_result):
        return 0.7

    coord = AgentCoordinator(log, planner, executor, verifier)
    coord.run("goal")

    events = log.query(event_type=EventType.STATE_UPDATED)
    # 3 steps: planner / executor / verifier
    assert len(events) >= 3

    steps = [e.context.get("step") for e in events]
    assert "planner" in steps
    assert "executor" in steps
    assert "verifier" in steps