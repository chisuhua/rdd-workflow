"""Tests for sessions schema v3 + _VALID_KINDS dual-add + stage_guide exemption.

Per feat-guide-orchestrator-session-event-bus (ADR-0055 v3, Oracle + Metis revised).
"""
from __future__ import annotations

from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
from skills.rddf_session.scripts.rddf_session_pkg._types import (
    HEARTBEAT_TIMEOUT_BY_KIND,
    _KIND_ALIAS,
    _VALID_KINDS,
)


def test_stage_guide_kind_accepted_in_valid_kinds():
    """Oracle B2: stage_guide in _VALID_KINDS (belt-and-suspenders pattern)."""
    assert "stage_guide" in _VALID_KINDS


def test_guide_orchestrator_kind_accepted_in_valid_kinds():
    """Oracle B2: guide-orchestrator in _VALID_KINDS (belt-and-suspenders pattern)."""
    assert "guide-orchestrator" in _VALID_KINDS


def test_kind_alias_normalizes_guide_orchestrator():
    """Metis B5: _KIND_ALIAS['guide-orchestrator'] == 'stage_guide'."""
    assert _KIND_ALIAS.get("guide-orchestrator") == "stage_guide"


def test_stage_guide_create_session_succeeds(tmp_path):
    """AC-1: create_session(kind='stage_guide') succeeds with goal.last_seen_offset=0."""
    sessions_file = tmp_path / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))
    sid = coord.create_session(
        kind="stage_guide",
        owner_opencode_session_id="ses_test",
        goal={"intent": "guide-orchestrator", "last_seen_offset": 0},
    )
    assert sid.startswith("rds_")

    # Round-trip
    session = coord.find_session(sid)
    assert session is not None
    assert session.kind == "stage_guide"
    assert session.owner_opencode_session_id == "ses_test"
    assert session.goal.get("intent") == "guide-orchestrator"
    assert session.goal.get("last_seen_offset") == 0


def test_stage_guide_allows_parallel_stage_arch(tmp_path):
    """Oracle B1: stage_guide + stage_arch can coexist (bidirectional)."""
    sessions_file = tmp_path / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))
    sid_guide = coord.create_session(
        kind="stage_guide",
        owner_opencode_session_id="ses_A",
        goal={"intent": "guide-orchestrator", "last_seen_offset": 0},
    )
    sid_arch = coord.create_session(
        kind="stage_arch",
        owner_opencode_session_id="ses_B",
        goal={"intent": "guide-arch"},
    )
    assert sid_guide != sid_arch
    sessions = coord.list_sessions()
    kinds = {s.kind for s in sessions}
    assert {"stage_guide", "stage_arch"}.issubset(kinds)


def test_stage_guide_extended_timeout():
    """AC-3: stage_guide has 8h heartbeat timeout; stages keep 30min."""
    assert HEARTBEAT_TIMEOUT_BY_KIND["stage_guide"] >= 8 * 60 * 60
    for stage_kind in ("stage_arch", "stage_design", "stage_plan", "stage_ship"):
        assert HEARTBEAT_TIMEOUT_BY_KIND[stage_kind] == 30 * 60


def test_list_sessions_owner_scoped_filter(tmp_path, monkeypatch):
    """AC-17: list_sessions accepts owner_opencode_session_id filter.

    H7: stage_guide is GLOBAL singleton — only one active at a time, regardless
    of owner. Same-kind same-owner conflict check is independent (lines 69-79).
    Use distinct kinds per owner to avoid same-kind diff-owner conflict.
    Allow cross-stage parallelism to enable multiple stages per owner.
    """
    monkeypatch.setenv("RDDF_ALLOW_CROSS_STAGE_PARALLEL", "yes")
    sessions_file = tmp_path / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))
    # ses_A has stage_guide + stage_arch + stage_design (3 distinct kinds)
    coord.create_session(
        kind="stage_guide", owner_opencode_session_id="ses_A",
        goal={"intent": "guide-orchestrator", "last_seen_offset": 0},
    )
    coord.create_session(
        kind="stage_arch", owner_opencode_session_id="ses_A",
        goal={"intent": "guide-arch"},
    )
    coord.create_session(
        kind="stage_design", owner_opencode_session_id="ses_A",
        goal={"intent": "guide-design"},
    )
    # ses_B has stage_plan + stage_ship (2 distinct kinds, no overlap with ses_A)
    coord.create_session(
        kind="stage_plan", owner_opencode_session_id="ses_B",
        goal={"intent": "guide-plan"},
    )
    coord.create_session(
        kind="stage_ship", owner_opencode_session_id="ses_B",
        goal={"intent": "guide-ship"},
    )
    a_sessions = coord.list_sessions(owner_opencode_session_id="ses_A")
    assert len(a_sessions) == 3
    assert all(s.owner_opencode_session_id == "ses_A" for s in a_sessions)
    b_sessions = coord.list_sessions(owner_opencode_session_id="ses_B")
    assert len(b_sessions) == 2
    assert all(s.owner_opencode_session_id == "ses_B" for s in b_sessions)


def test_list_sessions_state_filter(tmp_path):
    """AC-17: list_sessions accepts state filter."""
    sessions_file = tmp_path / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))
    coord.create_session(
        kind="stage_guide", owner_opencode_session_id="ses_A",
        goal={"intent": "guide-orchestrator", "last_seen_offset": 0},
    )
    active = coord.list_sessions(state="active")
    assert len(active) == 1
    completed = coord.list_sessions(state="completed")
    assert len(completed) == 0


def test_check_heartbeat_timeouts_readonly_does_not_mutate(tmp_path):
    """AC-18: check_heartbeat_timeouts(readonly=True) does NOT modify sessions.json."""
    sessions_file = tmp_path / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))
    coord.create_session(
        kind="stage_guide", owner_opencode_session_id="ses_A",
        goal={"intent": "guide-orchestrator", "last_seen_offset": 0},
    )
    before = sessions_file.read_text()
    orphaned = coord.check_heartbeat_timeouts(readonly=True)
    after = sessions_file.read_text()
    assert before == after, "readonly=True must not write sessions.json"
    # stage_guide with fresh heartbeat: should NOT be in orphaned list
    assert orphaned == []


def test_check_heartbeat_timeouts_explicit_config_wins_over_per_kind(tmp_path):
    """Regression: explicit HeartbeatConfig.timeout_seconds overrides per-kind table.

    Before fix: PR1 made HEARTBEAT_TIMEOUT_BY_KIND primary, so tests using
    short timeout_seconds (0.3s) for stage_plan were ignored because the kind
    table has stage_plan=1800s. Fixed by inverting priority: explicit config >
    per-kind > module default.
    """
    import time
    from skills.rddf_session.scripts.rddf_session import HeartbeatConfig

    sessions_file = tmp_path / "sessions.json"
    config = HeartbeatConfig(timeout_seconds=0.3, refresh_threshold_seconds=0.15)
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file), config=config)
    sid = coord.create_session(
        kind="stage_plan", owner_opencode_session_id="ses_A",
        goal={"intent": "guide-plan", "subject": "regression-test"},
    )
    time.sleep(0.6)
    orphaned = coord.check_heartbeat_timeouts()
    assert sid in orphaned, (
        "Explicit HeartbeatConfig(timeout_seconds=0.3) must be honored even "
        "when HEARTBEAT_TIMEOUT_BY_KIND['stage_plan'] is larger"
    )


def test_check_heartbeat_timeouts_per_kind_default_when_config_default(tmp_path):
    """AC-3: when HeartbeatConfig uses default timeout, per-kind applies.

    Verifies stage_guide gets 8h default when HeartbeatConfig() is constructed
    without arguments (config.timeout_seconds == DEFAULT_HEARTBEAT_TIMEOUT_SECONDS).
    """
    import time
    from skills.rddf_session.scripts.rddf_session import HeartbeatConfig

    sessions_file = tmp_path / "sessions.json"
    config = HeartbeatConfig()  # default timeout_seconds=1800
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file), config=config)
    sid = coord.create_session(
        kind="stage_guide", owner_opencode_session_id="ses_A",
        goal={"intent": "guide-orchestrator", "last_seen_offset": 0},
    )
    # After 2 seconds (way past 30min default, but well under 8h stage_guide default),
    # stage_guide should NOT be marked orphaned.
    time.sleep(2.0)
    orphaned = coord.check_heartbeat_timeouts()
    assert sid not in orphaned, (
        "stage_guide with default config should use 8h per-kind timeout, "
        "not 30min module default"
    )