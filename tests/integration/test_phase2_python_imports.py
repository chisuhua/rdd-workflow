#!/usr/bin/env python3
# tests/integration/test_phase2_python_imports.py
#
# Phase 2 regression test: lock the Python module layout per ADR-0021 Decision 1.
# After Phase 2:
#   - 11 moved .py files: must NOT exist at skills._lib.X (old path)
#                          MUST exist at skills.<skill>.scripts.X (new path)
#   - 13 shared .py files: must exist at skills._lib.X (unchanged)

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


MOVED_MODULES = [
    # (module_path_old, module_path_new, original_filename)
    ("skills._lib.rddf_session", "skills.rddf_session.scripts.rddf_session", "rddf_session.py"),
    ("skills._lib.deps_output", "skills.deps.scripts.deps_output", "deps_output.py"),
    ("skills._lib.feature_view", "skills.feature.scripts.feature_view", "feature_view.py"),
    ("skills._lib.feature_cli", "skills.feature.scripts.feature_cli", "feature_cli.py"),
    ("skills._lib.propose_change", "skills.propose.scripts.propose_change", "propose_change.py"),
    ("skills._lib.write_arch_handoff", "skills.guide_arch.scripts.write_arch_handoff", "write_arch_handoff.py"),
    ("skills._lib.plan_deps_candidates", "skills.guide_plan.scripts.plan_deps_candidates", "plan_deps_candidates.py"),
    ("skills._lib.plan_done_gate", "skills.guide_plan.scripts.plan_done_gate", "plan_done_gate.py"),
    ("skills._lib.update_roadmap_progress", "skills.execute.scripts.update_roadmap_progress", "update_roadmap_progress.py"),
    ("skills._lib.execute_step7", "skills.execute.scripts.execute_step7", "execute_step7.py"),
    ("skills._lib.validate_baseline", "skills.propose.scripts.validate_baseline", "validate_baseline.py"),
]

SHARED_MODULES = [
    "skills._lib.iteration",
    "skills._lib.gate",
    "skills._lib.session_manager",
    "skills._lib.roadmap_state",
]

# Phase 3 (skills-reorg-phase3-core): _lib/ reorganized into core/ + loop/
CORE_MODULES = [
    "skills._lib.core.event_log",
    "skills._lib.core.event_types",
    "skills._lib.core.state_vector",
    "skills._lib.core.defaults",
    "skills._lib.core.lock",
    "skills._lib.core.atomic_write",
]
LOOP_MODULES = [
    "skills._lib.loop.actions",
    "skills._lib.loop.detectors",
    "skills._lib.loop.agents",
    "skills._lib.loop.human_nodes",
    "skills._lib.loop.interaction_modes",
    "skills._lib.loop.memory",
    "skills._lib.loop.tribunal",
    "skills._lib.loop.sanitizer",
    "skills._lib.loop.step_pipeline",
    "skills._lib.loop.flowchart",
    "skills._lib.loop.flow_customizer",
    "skills._lib.loop.design_phase",
    "skills._lib.loop.loop_state",
    "skills._lib.loop.plugin_loader",
    "skills._lib.loop.event_queue",
]
TOPLEVEL_MODULES = [
    "skills._lib.iteration",
    "skills._lib.gate",
    "skills._lib.session_manager",
    "skills._lib.roadmap_state",
    "skills._lib.roadmap_sprint",
    "skills._lib.config",
    "skills._lib.event_context",
    "skills._lib.session",
    "skills._lib.session_base",
    "skills._lib.arch_quality_gate",
    "skills._lib.change_alignment",
    "skills._lib.dependency_scheduler",
    "skills._lib.rate_limiter",
    "skills._lib.trigger_engine",
    "skills._lib.trigger_registry",
    "skills._lib.triggers",
    "skills._lib.validate_delta_targets",
    "skills._lib.validate_report",
]


@pytest.mark.parametrize("old_path,new_path,filename", MOVED_MODULES)
def test_phase2_moved_module_exists_at_new_path(old_path, new_path, filename):
    """Each moved file MUST be importable from the new path (ADR-0021 Decision 1)."""
    spec = importlib.util.find_spec(new_path)
    assert spec is not None, (
        f"FAIL: {new_path} not importable — "
        f"{filename} should exist at skills/<skill>/scripts/{filename}"
    )


@pytest.mark.parametrize("old_path,new_path,filename", MOVED_MODULES)
def test_phase2_moved_module_not_at_old_path(old_path, new_path, filename):
    """Each moved file MUST NOT exist at old skills._lib.X path."""
    spec = importlib.util.find_spec(old_path)
    assert spec is None, (
        f"FAIL: {old_path} still importable — "
        f"{filename} should have been moved out of _lib/"
    )


@pytest.mark.parametrize("shared_path", SHARED_MODULES)
def test_phase2_shared_module_still_in_lib(shared_path):
    """Shared .py files MUST still be importable from skills._lib.X (unchanged)."""
    spec = importlib.util.find_spec(shared_path)
    assert spec is not None, (
        f"FAIL: {shared_path} not importable — "
        f"shared modules must stay in skills/_lib/"
    )


def test_phase2_rddf_session_hooks_in_rddf_session_scripts():
    """N3 fix per ADR-0021 Decision 2: rddf_session_hooks.sh moved to rddf-session/scripts/.

    The hooks.sh is a bash file but it inlines Python that imports rddf_session.
    After Phase 2, rddf_session_hooks.sh source line in SKILL.md points to
    ../rddf-session/scripts/rddf_session_hooks.sh.
    """
    rddf_hooks_path = REPO_ROOT / "skills" / "rddf-session" / "scripts" / "rddf_session_hooks.sh"
    assert rddf_hooks_path.exists(), (
        f"FAIL: {rddf_hooks_path} does not exist — "
        f"rddf_session_hooks.sh must move with rddf_session.py (ADR-0021 Decision 2)"
    )
    # Verify the hooks file references the new rddf_session import path
    text = rddf_hooks_path.read_text()
    assert "from skills.rddf_session.scripts.rddf_session import" in text, (
        "FAIL: rddf_session_hooks.sh still uses old import path — "
        "should be: from skills.rddf_session.scripts.rddf_session import ..."
    )


# ── Phase 3 tests (skills-reorg-phase3-core) ──────────────────────────────


@pytest.mark.parametrize("core_path", CORE_MODULES)
def test_phase3_core_modules_importable(core_path):
    """Phase 3 core modules MUST be importable from skills._lib.core.X."""
    spec = importlib.util.find_spec(core_path)
    assert spec is not None, (
        f"FAIL: {core_path} not importable — "
        f"core module should be in skills/_lib/core/"
    )


@pytest.mark.parametrize("loop_path", LOOP_MODULES)
def test_phase3_loop_modules_importable(loop_path):
    """Phase 3 loop modules MUST be importable from skills._lib.loop.X."""
    spec = importlib.util.find_spec(loop_path)
    assert spec is not None, (
        f"FAIL: {loop_path} not importable — "
        f"loop module should be in skills/_lib/loop/"
    )


@pytest.mark.parametrize("toplevel_path", TOPLEVEL_MODULES)
def test_phase3_toplevel_modules_importable(toplevel_path):
    """Phase 3 top-level modules MUST be importable from skills._lib.X."""
    spec = importlib.util.find_spec(toplevel_path)
    assert spec is not None, (
        f"FAIL: {toplevel_path} not importable — "
        f"top-level module should be in skills/_lib/"
    )


OLD_FLAT_PATHS = [
    "skills._lib.state_vector",
    "skills._lib.event_log",
    "skills._lib.lock",
    "skills._lib.atomic_write",
    "skills._lib.event_types",
    "skills._lib.actions",
    "skills._lib.detectors",
    "skills._lib.agents",
    "skills._lib.human_nodes",
    "skills._lib.interaction_modes",
    "skills._lib.memory",
    "skills._lib.tribunal",
    "skills._lib.sanitizer",
    "skills._lib.step_pipeline",
    "skills._lib.flowchart",
    "skills._lib.flow_customizer",
    "skills._lib.design_phase",
    "skills._lib.loop_state",
    "skills._lib.plugin_loader",
    "skills._lib.event_queue",
]


@pytest.mark.parametrize("old_path", OLD_FLAT_PATHS)
def test_phase3_moved_modules_not_at_old_flat_path(old_path):
    """Phase 3: modules in core/ or loop/ MUST NOT be importable from old flat skills._lib.X path."""
    spec = importlib.util.find_spec(old_path)
    assert spec is None, (
        f"FAIL: {old_path} still importable — "
        f"module was moved to skills/_lib/core/ or skills/_lib/loop/"
    )