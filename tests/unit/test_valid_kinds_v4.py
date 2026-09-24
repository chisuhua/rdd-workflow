"""Unit tests for the v4 kind-enum extension (complete-guide-orchestrator-flow Step A.1 / D6).

Locks down the 8-case behavioral matrix for:
- 3 new kinds (stage_builder, stage_verify, stage_quick)
- Cross-stage singleton exemption semantics:
  * stage_guide bidirectional exempt (v3 preserved)
  * stage_builder/verify/quick can mix with each other (v4)
  * arch/design/plan/ship singleton among themselves (preserved)
  * arch/design/plan/ship still blocks builder/verify/quick (preserved)
"""
from __future__ import annotations

import shutil

import pytest

from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
from skills.rddf_session.scripts.rddf_session_pkg._types import (
    ConflictError,
    HeartbeatConfig,
    HEARTBEAT_TIMEOUT_BY_KIND,
    _KIND_ALIAS,
    _VALID_KINDS,
)


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Set up a fresh project_root with .rddf/state/ for each test."""
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    sessions_file = str(state_dir / "sessions.json")
    monkeypatch.chdir(tmp_path)
    coord = RddfSessionCoordinator(sessions_file, HeartbeatConfig())
    yield tmp_path, sessions_file, coord
    shutil.rmtree(tmp_path, ignore_errors=True)


def _create(coord, kind, owner="owner_default"):
    intent_map = {
        "stage_arch": "guide-arch",
        "stage_design": "guide-design",
        "stage_plan": "guide-plan",
        "stage_ship": "guide-ship",
        "stage_guide": "guide-orchestrator",
        "stage_builder": "rdd-builder",
        "stage_verify": "rdd-verifier",
        "stage_quick": "rdd-quick",
    }
    return coord.create_session(
        kind=kind,
        owner_opencode_session_id=owner,
        goal={
            "intent": intent_map[kind],
            "subject": "test-subject",
            "expected_outcome": "ok",
        },
    )


# --- Kind registry (Step A.1 / D6) ---

class TestKindRegistry:
    def test_v4_kinds_added(self):
        """Step A.1 / D6: 3 new kinds registered in _VALID_KINDS."""
        assert "stage_builder" in _VALID_KINDS
        assert "stage_verify" in _VALID_KINDS
        assert "stage_quick" in _VALID_KINDS

    def test_v4_aliases_added(self):
        """Step A.1 / D6: 3 new user-friendly aliases."""
        assert _KIND_ALIAS["rdd-builder"] == "stage_builder"
        assert _KIND_ALIAS["rdd-verifier"] == "stage_verify"
        assert _KIND_ALIAS["rdd-quick"] == "stage_quick"

    def test_v4_heartbeats(self):
        """Step A.1 / D6: builder/verify=2h, quick=30min (per Oracle review)."""
        assert HEARTBEAT_TIMEOUT_BY_KIND["stage_builder"] == 2 * 60 * 60
        assert HEARTBEAT_TIMEOUT_BY_KIND["stage_verify"] == 2 * 60 * 60
        assert HEARTBEAT_TIMEOUT_BY_KIND["stage_quick"] == 30 * 60


# --- 8-case cross-stage singleton matrix ---

class TestCrossStageMatrix:
    """8-case behavioral matrix for cross-stage exemption semantics.

    Cases 1, 3, 6: arch singleton blocks builder/verify/quick (preserved v3 rule).
    Cases 2: arch + guide coexist (v3 bidirectional exemption preserved).
    Cases 4, 5, 7, 8: guide/builder/verify/quick form a coexist family (v4 new).
    """

    def test_case1_arch_blocks_builder(self, tmp_project):
        _, _, coord = tmp_project
        _create(coord, "stage_arch", owner="A")
        with pytest.raises(ConflictError, match="stage_arch"):
            _create(coord, "stage_builder", owner="B")

    def test_case2_arch_and_guide_coexist(self, tmp_project):
        _, _, coord = tmp_project
        sid_a = _create(coord, "stage_arch", owner="A")
        sid_g = _create(coord, "stage_guide", owner="B")
        assert sid_a != sid_g

    def test_case3_arch_blocks_design(self, tmp_project):
        """arch/design/plan/ship remain mutually exclusive among themselves."""
        _, _, coord = tmp_project
        _create(coord, "stage_arch", owner="A")
        with pytest.raises(ConflictError, match="stage_arch"):
            _create(coord, "stage_design", owner="B")

    def test_case4_guide_and_builder_coexist(self, tmp_project):
        _, _, coord = tmp_project
        sid_g = _create(coord, "stage_guide", owner="G")
        sid_b = _create(coord, "stage_builder", owner="B")
        assert sid_g != sid_b

    def test_case5_builder_and_verify_coexist(self, tmp_project):
        _, _, coord = tmp_project
        sid_b = _create(coord, "stage_builder", owner="B")
        sid_v = _create(coord, "stage_verify", owner="V")
        assert sid_b != sid_v

    def test_case6_existing_arch_blocks_new_builder(self, tmp_project):
        """Symmetric to case1: arch active + new builder = BLOCK."""
        _, _, coord = tmp_project
        _create(coord, "stage_arch", owner="A")
        with pytest.raises(ConflictError, match="stage_arch"):
            _create(coord, "stage_builder", owner="B")

    def test_case7_guide_and_quick_coexist(self, tmp_project):
        _, _, coord = tmp_project
        sid_g = _create(coord, "stage_guide", owner="G")
        sid_q = _create(coord, "stage_quick", owner="Q")
        assert sid_g != sid_q

    def test_case8_all_four_guide_family_kinds_coexist(self, tmp_project):
        _, _, coord = tmp_project
        sids = [
            _create(coord, "stage_guide", owner="G1"),
            _create(coord, "stage_builder", owner="B1"),
            _create(coord, "stage_verify", owner="V1"),
            _create(coord, "stage_quick", owner="Q1"),
        ]
        assert len(set(sids)) == 4  # all distinct


# --- Alias resolution ---

class TestAliasResolution:
    """Verify _KIND_ALIAS maps user-friendly names to canonical stage_* names."""

    def test_rdd_builder_resolves(self):
        from skills.rddf_session.scripts.rddf_session_pkg._types import _normalize_kind
        assert _normalize_kind("rdd-builder") == "stage_builder"

    def test_rdd_verifier_resolves(self):
        from skills.rddf_session.scripts.rddf_session_pkg._types import _normalize_kind
        assert _normalize_kind("rdd-verifier") == "stage_verify"

    def test_rdd_quick_resolves(self):
        from skills.rddf_session.scripts.rddf_session_pkg._types import _normalize_kind
        assert _normalize_kind("rdd-quick") == "stage_quick"

    def test_passthrough_for_canonical(self):
        from skills.rddf_session.scripts.rddf_session_pkg._types import _normalize_kind
        assert _normalize_kind("stage_builder") == "stage_builder"


# --- Parent kind mapping (rddf_session_hooks.sh:284) ---

def _read_parent_kind_map_from_sh():
    """Read parent_kind_map from rddf_session_hooks.sh (since it's a bash heredoc)."""
    import re
    from pathlib import Path
    hooks_path = Path(__file__).resolve().parents[2] / "skills" / "rddf-session" / "scripts" / "rddf_session_hooks.sh"
    text = hooks_path.read_text()
    m = re.search(r"parent_kind_map\s*=\s*\{([^}]+)\}", text)
    assert m, "parent_kind_map not found in rddf_session_hooks.sh"
    pairs = {}
    for k, v in re.findall(r'"(\w+)":\s*"(\w+)"', m.group(1)):
        pairs[k] = v
    return pairs


class TestParentKindMap:
    """Verify the 3 new kinds have a parent assigned (v4 extension)."""

    def test_stage_builder_parent(self):
        """Builder is a child of planner (stage_design)."""
        pairs = _read_parent_kind_map_from_sh()
        assert pairs.get("stage_builder") == "stage_design"

    def test_stage_verify_parent(self):
        """Verifier is a child of builder."""
        pairs = _read_parent_kind_map_from_sh()
        assert pairs.get("stage_verify") == "stage_builder"

    def test_stage_quick_parent(self):
        """Quick is a child of guide (transient child of orchestrator)."""
        pairs = _read_parent_kind_map_from_sh()
        assert pairs.get("stage_quick") == "stage_guide"