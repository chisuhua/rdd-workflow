"""Tests for recommended_route field per ADR-0048 (2026-09-09) §Decision 2.

ADR-0048 promoted recommended_route from optional (fix-v4-rdd-planner-scope-
over-assignment AC-13 optional) to required. This file locks:

  1. planner_state_schema.json: recommended_route in required[] + enum simple|complex|unknown
  2. planner_handoff_schema.json: recommended_route in required[] + enum
  3. _lib/planner_state.py: _default_state() returns recommended_route="unknown"
  4. _lib/planner_handoff.py: write_planner_handoff accepts recommended_route kwarg
  5. planner_stage_exit.sh: passes RECOMMENDED_ROUTE env var + double-gate check
  6. _lib/planner_sync.py: _compute_recommended_route heuristic
  7. _lib/cli/planner_cmd.py: status output shows recommended_route
  8. _lib/builder_deps.py: read_planner_recommended_route helper
  9. _lib/builder_handoff.py: approval_status enum allows dispatched_to_quick
 10. _lib/builder_handoff.py: dispatch_quick_at + dispatch_quick_outcome fields
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path("/workspace/project/rdd-workflow")


# ---------------------------------------------------------------------------
# 1. planner_state_schema.json: recommended_route required
# ---------------------------------------------------------------------------

class TestPlannerStateSchemaV11:
    def test_schema_version_still_v1(self):
        schema = json.loads((REPO_ROOT / "_lib/schemas/planner_state_schema.json").read_text())
        # version is declared via properties.version.const (not top-level field).
        assert schema["properties"]["version"]["const"] == 1, \
            "planner-state schema version should remain 1 (schema is additive, ADR-0048)"

    def test_recommended_route_in_required(self):
        schema = json.loads((REPO_ROOT / "_lib/schemas/planner_state_schema.json").read_text())
        assert "recommended_route" in schema.get("required", []), \
            "ADR-0048 §Decision 2: recommended_route must be REQUIRED in planner_state_schema"

    def test_recommended_route_enum(self):
        schema = json.loads((REPO_ROOT / "_lib/schemas/planner_state_schema.json").read_text())
        rec = schema["properties"]["recommended_route"]
        assert rec.get("enum") == ["simple", "complex", "unknown"], \
            "recommended_route enum must be simple|complex|unknown"

    def test_description_references_adr0048(self):
        schema = json.loads((REPO_ROOT / "_lib/schemas/planner_state_schema.json").read_text())
        rec = schema["properties"]["recommended_route"]
        assert "ADR-0048" in rec.get("description", ""), \
            "description must cite ADR-0048 for audit trail"


# ---------------------------------------------------------------------------
# 2. planner_handoff_schema.json: recommended_route required
# ---------------------------------------------------------------------------

class TestPlannerHandoffSchemaV11:
    def test_recommended_route_in_required(self):
        schema = json.loads((REPO_ROOT / "_lib/schemas/planner_handoff_schema.json").read_text())
        assert "recommended_route" in schema.get("required", []), \
            "ADR-0048 §Decision 2: recommended_route must be REQUIRED in planner_handoff_schema"

    def test_recommended_route_enum(self):
        schema = json.loads((REPO_ROOT / "_lib/schemas/planner_handoff_schema.json").read_text())
        rec = schema["properties"]["recommended_route"]
        assert rec.get("enum") == ["simple", "complex", "unknown"]

    def test_proposals_ready_still_present(self):
        """Backward compat: per fix-v4-rdd-planner-scope-over-assignment A3, the
        old proposals_authored was renamed to proposals_ready in v1.0; this test
        ensures the rename wasn't accidentally reverted."""
        schema = json.loads((REPO_ROOT / "_lib/schemas/planner_handoff_schema.json").read_text())
        assert "proposals_ready" in schema["properties"]
        assert "proposals_authored" not in schema["properties"], \
            "proposals_authored is fiction (planner never authors); should have been renamed"

    def test_description_references_adr0048(self):
        schema = json.loads((REPO_ROOT / "_lib/schemas/planner_handoff_schema.json").read_text())
        rec = schema["properties"]["recommended_route"]
        assert "ADR-0048" in rec.get("description", "")


# ---------------------------------------------------------------------------
# 3. _lib/planner_state.py: _default_state() returns recommended_route
# ---------------------------------------------------------------------------

class TestPlannerStateDefaultRecommendedRoute:
    def test_default_state_has_recommended_route(self):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.planner_state import _default_state
s = _default_state()
print('OK' if s.get('recommended_route') == 'unknown' else 'FAIL: ' + str(s.get('recommended_route')))
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_recommended_route_excluded_from_semantic_hash(self):
        """ADR-0048: recommended_route is a derived advisory signal; changes to it
        alone should NOT bump state_revision (excluded from semantic hash)."""
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.planner_state import _planner_state_semantic_hash
base = {{'version': 1, 'current_sprint': 'sprint-2026-09', 'active_projects': [], 'recommended_route': 'simple'}}
changed = dict(base)
changed['recommended_route'] = 'complex'
h1 = _planner_state_semantic_hash(base)
h2 = _planner_state_semantic_hash(changed)
print('OK' if h1 == h2 else f'FAIL: hashes differ: {{h1!r}} vs {{h2!r}}')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout


# ---------------------------------------------------------------------------
# 4. _lib/planner_handoff.py: write_planner_handoff accepts recommended_route
# ---------------------------------------------------------------------------

class TestPlannerHandoffWriteRecommendedRoute:
    def test_write_with_recommended_route_simple(self, tmp_path):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.planner_handoff import write_planner_handoff, read_planner_handoff
result = write_planner_handoff(
    '{tmp_path}', ['p1'], 1, ['f1'], 'sprint-2026-09',
    awaiting_builder=['change-x'], recommended_route='simple',
)
read_back = read_planner_handoff('{tmp_path}')
assert read_back['recommended_route'] == 'simple', read_back
print('OK')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_write_with_recommended_route_complex(self, tmp_path):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.planner_handoff import write_planner_handoff, read_planner_handoff
write_planner_handoff(
    '{tmp_path}', [], 0, [], 'sprint-2026-09',
    recommended_route='complex',
)
read_back = read_planner_handoff('{tmp_path}')
assert read_back['recommended_route'] == 'complex', read_back
print('OK')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_write_default_recommended_route_is_unknown(self, tmp_path):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.planner_handoff import write_planner_handoff, read_planner_handoff
write_planner_handoff('{tmp_path}', [], 0, [], 'sprint-2026-09')
read_back = read_planner_handoff('{tmp_path}')
assert read_back['recommended_route'] == 'unknown', read_back
print('OK')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_env_var_recommended_route_validation(self, tmp_path):
        """__main__ entry point must validate RECOMMENDED_ROUTE env var against enum."""
        result = subprocess.run(
            ["python3", "-m", "_lib.planner_handoff"],
            env={
                "PROJECT_ROOT": str(tmp_path),
                "PROPOSALS_READY": "",
                "PROPOSALS_APPROVED_COUNT": "0",
                "FEATURES_ACTIVE": "",
                "CURRENT_SPRINT": "sprint-2026-09",
                "RECOMMENDED_ROUTE": "invalid_value",
                "PATH": __import__("os").environ.get("PATH", ""),
                "PYTHONPATH": str(REPO_ROOT),
            },
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode != 0, "invalid RECOMMENDED_ROUTE must fail"
        assert "simple|complex|unknown" in result.stderr or "RECOMMENDED_ROUTE" in result.stderr


# ---------------------------------------------------------------------------
# 5. planner_stage_exit.sh: passes RECOMMENDED_ROUTE + double-gate
# ---------------------------------------------------------------------------

class TestPlannerStageExitRecommendedRoute:
    def test_script_passes_recommended_route_env(self):
        script = (REPO_ROOT / "skills/rdd-planner/scripts/planner_stage_exit.sh").read_text()
        assert "RECOMMENDED_ROUTE" in script, \
            "planner_stage_exit.sh must read RECOMMENDED_ROUTE env var (per ADR-0048)"

    def test_script_has_double_gate(self):
        """Per ADR-0048 §Decision 2: planner-done 双门控 = roadmap存在 + recommended_route≠unknown."""
        script = (REPO_ROOT / "skills/rdd-planner/scripts/planner_stage_exit.sh").read_text()
        assert "roadmap.md" in script, "double-gate 1: roadmap.md check missing"
        assert "RECOMMENDED" in script and "unknown" in script, \
            "double-gate 2: recommended_route check missing"

    def test_script_exits_nonzero_if_recommended_unknown(self, tmp_path):
        """End-to-end: planner_stage_exit.sh must reject when recommended_route=unknown."""
        # Setup: create roadmap.md (passes gate 1) + openspec/changes/test-change (passes
        # existence check) but no planner-state.json (gate 2 fails: RECOMMENDED=unknown).
        (tmp_path / "roadmap.md").write_text("# Test roadmap\n")
        (tmp_path / "openspec/changes/test-change").mkdir(parents=True)
        (tmp_path / "openspec/changes/test-change/proposal.md").write_text("# proposal\n")
        (tmp_path / ".rddf/state").mkdir(parents=True)

        result = subprocess.run(
            ["bash", str(REPO_ROOT / "skills/rdd-planner/scripts/planner_stage_exit.sh"), "test-change"],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 2, \
            f"exit code should be 2 (double-gate fail), got {result.returncode}; stderr: {result.stderr}"
        assert "双门控失败" in result.stderr or "recommended_route" in result.stderr.lower()


# ---------------------------------------------------------------------------
# 6. _lib/planner_sync.py: _compute_recommended_route heuristic
# ---------------------------------------------------------------------------

class TestComputeRecommendedRoute:
    def _compute(self, active_projects):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys, json
sys.path.insert(0, '{sys_path}')
from _lib.planner_sync import _compute_recommended_route
import json
active = json.loads('{json.dumps(active_projects)}')
print(_compute_recommended_route(active))
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        return result.stdout.strip()

    def test_empty_active_returns_unknown(self):
        assert self._compute([]) == "unknown"

    def test_priority_p0_returns_complex(self):
        assert self._compute([{"priority": "P0", "proposal": "x"}]) == "complex"

    def test_priority_p1_returns_complex(self):
        assert self._compute([{"priority": "P1", "proposal": "x"}]) == "complex"

    def test_priority_p3_no_complex_keyword_returns_simple(self):
        active = [{
            "priority": "P3",
            "proposal": "fix-typo-readme",
            "theme": "documentation typo",
            "project_id": "docs",
        }]
        assert self._compute(active) == "simple"

    def test_complex_keyword_in_theme_returns_complex(self):
        active = [{
            "priority": "P3",
            "proposal": "x",
            "theme": "public interface change",
            "project_id": "api",
        }]
        assert self._compute(active) == "complex"

    def test_complex_keyword_in_proposal_name_returns_complex(self):
        active = [{
            "priority": "P3",
            "proposal": "breaking-change-to-config",
            "theme": "",
            "project_id": "config",
        }]
        assert self._compute(active) == "complex"

    def test_lib_core_path_returns_complex(self):
        active = [{
            "priority": "P3",
            "proposal": "refactor-x",
            "theme": "touch _lib/core/atomic_write.py",
            "project_id": "core",
        }]
        assert self._compute(active) == "complex"

    def test_lib_schemas_path_returns_complex(self):
        active = [{
            "priority": "P3",
            "proposal": "refactor-y",
            "theme": "add new field to _lib/schemas/foo.json",
            "project_id": "schemas",
        }]
        assert self._compute(active) == "complex"

    def test_mixed_signals_takes_priority_p1_over_p3(self):
        """If ANY active project has P0/P1, overall = complex (priority dominates)."""
        active = [
            {"priority": "P3", "proposal": "simple-1", "theme": "x", "project_id": "y"},
            {"priority": "P1", "proposal": "urgent-1", "theme": "x", "project_id": "y"},
        ]
        assert self._compute(active) == "complex"


# ---------------------------------------------------------------------------
# 7. _lib/cli/planner_cmd.py: status output shows recommended_route
# ---------------------------------------------------------------------------

class TestPlannerCmdStatusOutput:
    def test_status_shows_recommended_route(self, tmp_path):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.planner_state import write_state, read_state, _default_state
from _lib.cli.planner_cmd import cmd_planner
from pathlib import Path

# Setup state with explicit recommended_route
import json
state = _default_state()
state['recommended_route'] = 'simple'
write_state(Path('{tmp_path}'), state)

# Run status
import io, sys as _sys
old_stdout = _sys.stdout
_sys.stdout = io.StringIO()
try:
    cmd_planner(['status', '--project-root', '{tmp_path}'])
    output = _sys.stdout.getvalue()
finally:
    _sys.stdout = old_stdout

assert 'Recommended route: simple' in output, output
print('OK')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_status_hint_for_simple(self, tmp_path):
        """When recommended_route=simple, status should hint at option 5 (dispatch-quick)."""
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.planner_state import write_state, _default_state
from _lib.cli.planner_cmd import cmd_planner
from pathlib import Path

state = _default_state()
state['recommended_route'] = 'simple'
write_state(Path('{tmp_path}'), state)

import io, sys as _sys
old_stdout = _sys.stdout
_sys.stdout = io.StringIO()
try:
    cmd_planner(['status', '--project-root', '{tmp_path}'])
    output = _sys.stdout.getvalue()
finally:
    _sys.stdout = old_stdout

assert 'option 5' in output or 'dispatch-quick' in output, output
print('OK')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout


# ---------------------------------------------------------------------------
# 8. _lib/builder_deps.py: read_planner_recommended_route helper
# ---------------------------------------------------------------------------

class TestBuilderDepsReadPlannerRecommendedRoute:
    def test_function_exists(self):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.builder_deps import read_planner_recommended_route
print('OK' if callable(read_planner_recommended_route) else 'FAIL')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_returns_unknown_when_handoff_missing(self, tmp_path):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.builder_deps import read_planner_recommended_route
from pathlib import Path
assert read_planner_recommended_route(Path('{tmp_path}')) == 'unknown'
print('OK')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_reads_recommended_route_from_handoff(self, tmp_path):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.planner_handoff import write_planner_handoff
from _lib.builder_deps import read_planner_recommended_route
from pathlib import Path

write_planner_handoff(
    '{tmp_path}', [], 0, [], 'sprint-2026-09',
    recommended_route='simple',
)
assert read_planner_recommended_route(Path('{tmp_path}')) == 'simple'
print('OK')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_returns_unknown_on_invalid_enum(self, tmp_path):
        """Defensive: if handoff contains garbage, return unknown (not crash)."""
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys, json
sys.path.insert(0, '{sys_path}')
from pathlib import Path

# Write malformed handoff directly
state_dir = Path('{tmp_path}') / '.rddf' / 'state'
state_dir.mkdir(parents=True, exist_ok=True)
(state_dir / '.planner-handoff.json').write_text(json.dumps({{'recommended_route': 'garbage_value'}}))

from _lib.builder_deps import read_planner_recommended_route
assert read_planner_recommended_route(Path('{tmp_path}')) == 'unknown'
print('OK')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout


# ---------------------------------------------------------------------------
# 9. _lib/builder_handoff.py: approval_status enum allows dispatched_to_quick
# ---------------------------------------------------------------------------

class TestBuilderHandoffDispatchedToQuick:
    def test_write_with_dispatched_to_quick_status(self, tmp_path):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.builder_handoff import write_builder_handoff, read_builder_handoff
write_builder_handoff(
    project_root='{tmp_path}', change_name='test-change',
    approval_status='dispatched_to_quick',
    dispatch_quick_at='2026-09-09T10:00:00Z',
)
read_back = read_builder_handoff('{tmp_path}', 'test-change')
assert read_back['approval_status'] == 'dispatched_to_quick', read_back
assert read_back['dispatch_quick_at'] == '2026-09-09T10:00:00Z', read_back
print('OK')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_invalid_approval_status_rejected(self, tmp_path):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.builder_handoff import write_builder_handoff
try:
    write_builder_handoff(
        project_root='{tmp_path}', change_name='test-change',
        approval_status='invalid_value',
    )
    print('FAIL: should have raised')
except ValueError as e:
    if 'approval_status' in str(e):
        print('OK')
    else:
        print(f'FAIL: wrong error: {{e}}')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_invalid_dispatch_outcome_rejected(self, tmp_path):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.builder_handoff import write_builder_handoff
try:
    write_builder_handoff(
        project_root='{tmp_path}', change_name='test-change',
        approval_status='dispatched_to_quick',
        dispatch_quick_at='2026-09-09T10:00:00Z',
        dispatch_quick_outcome='not_a_real_outcome',
    )
    print('FAIL: should have raised')
except ValueError as e:
    if 'dispatch_quick_outcome' in str(e):
        print('OK')
    else:
        print(f'FAIL: wrong error: {{e}}')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_completed_outcome_accepted(self, tmp_path):
        sys_path = str(REPO_ROOT)
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '{sys_path}')
from _lib.builder_handoff import write_builder_handoff, read_builder_handoff
for outcome in ('completed', 'escalated', 'unverified'):
    write_builder_handoff(
        project_root='{tmp_path}', change_name='change-' + outcome,
        approval_status='dispatched_to_quick',
        dispatch_quick_at='2026-09-09T10:00:00Z',
        dispatch_quick_outcome=outcome,
    )
    read_back = read_builder_handoff('{tmp_path}', 'change-' + outcome)
    assert read_back['dispatch_quick_outcome'] == outcome, read_back
print('OK')
"""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout


# ---------------------------------------------------------------------------
# 10. _lib/schemas/rdd_quick_context_schema.json: new schema per ADR-0048
# ---------------------------------------------------------------------------

class TestRddQuickContextSchema:
    def test_schema_exists(self):
        path = REPO_ROOT / "_lib/schemas/rdd_quick_context_schema.json"
        assert path.exists(), "rdd_quick_context_schema.json must exist (per ADR-0048)"

    def test_schema_required_fields(self):
        schema = json.loads((REPO_ROOT / "_lib/schemas/rdd_quick_context_schema.json").read_text())
        required = schema.get("required", [])
        for field in ["change_name", "proposal_path", "from_builder", "dispatched_at"]:
            assert field in required, f"required field missing: {field}"

    def test_from_builder_is_const_true(self):
        schema = json.loads((REPO_ROOT / "_lib/schemas/rdd_quick_context_schema.json").read_text())
        assert schema["properties"]["from_builder"]["const"] is True, \
            "from_builder must be const True (only builder-dispatched creates this file)"

    def test_dispatch_outcome_enum(self):
        schema = json.loads((REPO_ROOT / "_lib/schemas/rdd_quick_context_schema.json").read_text())
        expected = {"completed", "escalated", "unverified"}
        actual = set(schema["properties"]["expected_outcome"]["enum"])
        assert actual == expected, f"expected_outcome enum mismatch: {actual}"
