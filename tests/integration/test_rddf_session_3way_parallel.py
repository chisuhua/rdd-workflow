"""3-way parallel rddf-session acceptance test.

Verifies:
1. 3 sessions can be created and coexist (no singleton block).
2. Each session's attached_changes are disjoint.
3. Final sessions.json is consistent (exactly the 3 created).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from skills.rddf_session.scripts.rddf_session_pkg._store import RddfSessionStore
from skills.rddf_session.scripts.rddf_session import (
    RddfSessionCoordinator,
    HeartbeatConfig,
    RddfSessionError,
)


@pytest.fixture
def sessions_file(tmp_path: Path) -> str:
    return str(tmp_path / "sessions.json")


@pytest.fixture
def coord(sessions_file: str, monkeypatch):
    """Coordinator that allows parallel same-stage sessions (test opt-in).

    The singleton gate blocks multiple active sessions of the same stage.
    For this test we create sessions of *different* kinds (arch/design/plan),
    but the gate also blocks cross-stage parallelism unless opted in via
    RDDF_ALLOW_CROSS_STAGE_PARALLEL=yes (per ADR-0017 §3).
    """
    monkeypatch.setenv("RDDF_ALLOW_CROSS_STAGE_PARALLEL", "yes")
    return RddfSessionCoordinator(sessions_file, HeartbeatConfig(
        timeout_seconds=60, refresh_threshold_seconds=30,
    ))


def test_three_parallel_sessions_coexist(sessions_file, coord):
    """3 sessions of different kinds (arch/design/plan) all active together."""
    ids = [
        coord.create_session(kind="stage_arch", owner_opencode_session_id="owner_a", goal={"intent": "guide-arch"}),
        coord.create_session(kind="stage_design", owner_opencode_session_id="owner_b", goal={"intent": "guide-design"}),
        coord.create_session(kind="stage_plan", owner_opencode_session_id="owner_c", goal={"intent": "guide-plan"}),
    ]
    assert len(set(ids)) == 3, "3 distinct session ids expected"

    sessions = coord.list_sessions()
    active = [s for s in sessions if s.state == "active"]
    assert len(active) == 3, f"expected 3 active, got {len(active)}"


def test_attached_changes_disjoint(sessions_file, coord):
    """Each parallel session must carry disjoint change sets."""
    s1 = coord.create_session(kind="stage_arch", owner_opencode_session_id="owner_a", goal={"intent": "guide-arch"})
    s2 = coord.create_session(kind="stage_design", owner_opencode_session_id="owner_b", goal={"intent": "guide-design"})
    s3 = coord.create_session(kind="stage_plan", owner_opencode_session_id="owner_c", goal={"intent": "guide-plan"})

    coord.attach_change(s1, "change-A")
    coord.attach_change(s2, "change-B")
    coord.attach_change(s3, "change-C")

    sets = [
        set(coord.find_session(s1).attached_changes or []),
        set(coord.find_session(s2).attached_changes or []),
        set(coord.find_session(s3).attached_changes or []),
    ]
    total = sum(len(s) for s in sets)
    union = set().union(*sets)
    assert total == len(union), "attached_changes must be disjoint across sessions"

    store = RddfSessionStore(sessions_file)
    data = store.read_unlocked()
    assert len(data["sessions"]) == 3, "sessions.json must contain exactly 3 sessions"
