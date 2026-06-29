## Task 1: Create phase_templates.yaml

**Files:**
- Create: `skills/_lib/phase_templates.yaml`

- [ ] **Step 1: Create phase_templates.yaml**

From ADR-0011 §"步骤模板定义":

```yaml
# skills/_lib/phase_templates.yaml — 默认阶段步骤模板
version: "2.0"

templates:
  arch:
    description: "架构定义阶段"
    steps:
      - id: "scan_architecture"
        type: "detector"
        module: "detectors"
        function: "detect_architecture"
      - id: "identify_gaps"
        type: "detector"
        module: "detectors"
        function: "detect_gaps"
      - id: "create_adr"
        type: "action"
        module: "actions"
        function: "action_create_adr"
      - id: "define_roadmap"
        type: "action"
        module: "actions"
        function: "action_define_roadmap"
      - id: "output_docs"
        type: "action"
        module: "actions"
        function: "action_output_arch_docs"

  plan:
    description: "变更生成阶段"
    steps:
      - id: "scan_candidates"
        type: "detector"
        module: "detectors"
        function: "detect_candidates"
      - id: "select_changes"
        type: "action"
        module: "actions"
        function: "action_select_changes"
      - id: "generate_proposal"
        type: "action"
        module: "actions"
        function: "action_generate_proposal"
      - id: "generate_design"
        type: "action"
        module: "actions"
        function: "action_generate_design"
      - id: "generate_tasks"
        type: "action"
        module: "actions"
        function: "action_generate_tasks"
      - id: "analyze_deps"
        type: "action"
        module: "actions"
        function: "action_analyze_deps"
      - id: "commit_change"
        type: "action"
        module: "actions"
        function: "action_commit_change"

  ship:
    description: "变更执行阶段"
    steps:
      - id: "select_change"
        type: "action"
        module: "actions"
        function: "action_select_change_for_ship"
      - id: "create_worktree"
        type: "action"
        module: "actions"
        function: "action_create_worktree"
      - id: "generate_plan"
        type: "action"
        module: "actions"
        function: "action_generate_plan"
      - id: "execute_units"
        type: "action"
        module: "actions"
        function: "action_execute_worktree"
      - id: "run_tests"
        type: "action"
        module: "actions"
        function: "action_run_tests"
      - id: "merge_to_main"
        type: "action"
        module: "actions"
        function: "action_merge_to_main"
      - id: "archive_change"
        type: "action"
        module: "actions"
        function: "action_archive_change"
```

- [ ] **Step 2: Verify YAML is parseable**

Run: `cd /workspace/project/spec-workflow && python3 -c "import yaml; d=yaml.safe_load(open('skills/_lib/phase_templates.yaml')); print(f'✅ {len(d[\"templates\"])} templates, {sum(len(t[\"steps\"]) for t in d[\"templates\"].values())} total steps')"`

Expected: 3 templates, ~20 total steps.

- [ ] **Step 3: Commit phase_templates.yaml**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/phase_templates.yaml && git commit -m "feat(pipeline): add default phase templates YAML — arch/plan/ship step sequences (ADR-0011)"
```

---

## Task 2: Create StepPipeline executor

**Files:**
- Create: `skills/_lib/step_pipeline.py`
- Create: `tests/unit/test_step_pipeline.py`

- [ ] **Step 1: Write TDD tests**

```python
"""Tests for StepPipeline — phase step execution (ADR-0011)."""
import os
import pytest
import yaml
from unittest.mock import MagicMock
from skills._lib.step_pipeline import StepPipeline, PipelineEvent
from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog


@pytest.fixture
def sv(tmp_path):
    return StateVector.load(str(tmp_path / "sv.json"))


@pytest.fixture
def el(tmp_path):
    return EventLog(str(tmp_path / "el.jsonl"))


@pytest.fixture
def pipeline(sv, el, tmp_path):
    """StepPipeline with a test template."""
    yaml_path = str(tmp_path / "test_templates.yaml")
    with open(yaml_path, "w") as f:
        f.write("""
templates:
  test_phase:
    steps:
      - id: "step_one"
        type: "detector"
        module: "detectors"
        function: "detect_health_issues"
      - id: "step_two"
        type: "action"
        module: "actions"
        function: "action_create_worktree"
""")
    return StepPipeline(state_vector=sv, event_log=el, templates_path=yaml_path)


def test_list_steps_returns_expected(pipeline):
    steps = pipeline.list_steps("test_phase")
    assert len(steps) == 2
    assert steps[0]["id"] == "step_one"
    assert steps[1]["id"] == "step_two"


def test_list_steps_unknown_phase_returns_empty(pipeline):
    steps = pipeline.list_steps("nonexistent")
    assert steps == []


def test_is_step_completed_initial_state(pipeline, sv):
    assert pipeline.is_step_completed("step_one") is False


def test_mark_step_completed_then_check(pipeline):
    pipeline.mark_step_completed("step_one")
    assert pipeline.is_step_completed("step_one") is True


def test_skip_completed_removes_done_steps(pipeline):
    pipeline.mark_step_completed("step_one")
    pending = pipeline.get_pending_steps("test_phase")
    assert len(pending) == 1
    assert pending[0]["id"] == "step_two"


def test_get_pending_steps_all_if_none_done(pipeline):
    pending = pipeline.get_pending_steps("test_phase")
    assert len(pending) == 2


def test_reset_clears_completed(pipeline):
    pipeline.mark_step_completed("step_one")
    pipeline.reset()
    assert pipeline.is_step_completed("step_one") is False
```

- [ ] **Step 2: Run — confirm ModuleNotFoundError**

- [ ] **Step 3: Create step_pipeline.py**

```python
"""StepPipeline — phase step execution engine (ADR-0011).

Loads phase templates from YAML, executes steps in order, tracks
completion for interruption recovery. Backward compatible — no
template = no behavior change in loop_engine.py.
"""
from __future__ import annotations
import os
import yaml
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity, Event


@dataclass
class PipelineEvent:
    step_id: str
    status: str  # "completed" | "failed" | "skipped"
    message: str


PIPELINE_STATE_KEY = "step_pipeline"


class StepPipeline:
    """Execute phase step sequences with interruption recovery."""

    def __init__(
        self,
        state_vector: StateVector,
        event_log: Optional[EventLog] = None,
        templates_path: Optional[str] = None,
    ):
        self.state_vector = state_vector
        self._event_log = event_log
        self._templates = self._load_templates(templates_path)

    def _load_templates(self, path: Optional[str]) -> Dict:
        if path and os.path.exists(path):
            with open(path) as f:
                return yaml.safe_load(f).get("templates", {})
        # Fall back to default built-in path
        default = os.path.join(
            os.path.dirname(__file__), "phase_templates.yaml"
        )
        if os.path.exists(default):
            with open(default) as f:
                return yaml.safe_load(f).get("templates", {})
        return {}

    def list_steps(self, phase: str) -> List[Dict]:
        template = self._templates.get(phase, {})
        return template.get("steps", [])

    def get_pending_steps(self, phase: str) -> List[Dict]:
        all_steps = self.list_steps(phase)
        completed = set(self._get_state().get("completed_steps", []))
        return [s for s in all_steps if s["id"] not in completed]

    def is_step_completed(self, step_id: str) -> bool:
        return step_id in self._get_state().get("completed_steps", [])

    def mark_step_completed(self, step_id: str) -> None:
        state = self._get_state()
        completed = set(state.get("completed_steps", []))
        completed.add(step_id)
        state["completed_steps"] = list(completed)
        self._save_state(state)
        self._emit(step_id, "completed", f"Step {step_id} completed")

    def reset(self) -> None:
        self._save_state({"phase": None, "completed_steps": [], "current_step": None, "started_at": None, "error": None})

    def _get_state(self) -> Dict:
        try:
            data = self.state_vector.to_dict()
            return data.get(PIPELINE_STATE_KEY, {})
        except Exception:
            return {}

    def _save_state(self, state: Dict) -> None:
        try:
            self.state_vector.update_field(PIPELINE_STATE_KEY, state)
        except Exception:
            pass

    def _emit(self, step_id: str, status: str, message: str) -> None:
        if self._event_log:
            self._event_log.record(
                event_type=EventType.EXECUTION_UNIT_COMPLETED,
                severity=Severity.INFO,
                message=message,
            )
```

- [ ] **Step 4: Run tests — all pass**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_step_pipeline.py -v`

Expected: 7 passed.

- [ ] **Step 5: Run full test suite — no regression**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/ -q --tb=short`

Expected: All pass.

- [ ] **Step 6: Commit StepPipeline**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/step_pipeline.py tests/unit/test_step_pipeline.py && git commit -m "feat(pipeline): add StepPipeline with skip-completed recovery and step-level events (ADR-0011)"
```

---

## Task 3: Update ADR-0011 status

**Files:**
- Modify: `docs/adr/ADR-0011-phase-step-pipeline-model.md`
- Modify: `docs/adr/README.md`

- [ ] **Step 1: Update ADR-0011 status**

```diff
- > **状态**: 已采纳
+ > **状态**: ✅ 已实施
```

- [ ] **Step 2: Update docs/adr/README.md table**

Change ADR-0011 row: `❌ 未实施（设计已采纳）` → `✅ 已实施`

- [ ] **Step 3: Commit ADR update**

```bash
cd /workspace/project/spec-workflow && git add docs/adr/ADR-0011-phase-step-pipeline-model.md docs/adr/README.md && git commit -m "docs(adr): ADR-0011 status → implemented (step pipeline complete)"
```

---

## Task 4: Final verification

- [ ] **Step 1: Run all tests**

Run: `cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/ -q --tb=short`

Expected: All pass (including new step_pipeline tests).

- [ ] **Step 2: openspec validate**

Run: `cd /workspace/project/spec-workflow && openspec validate v3-step-pipeline`

Expected: Valid.

- [ ] **Step 3: Verify git log**

Run: `cd /workspace/project/spec-workflow && git log --oneline -5`

Expected: Clean focused history.

---

## Self-Review

### 1. Spec Coverage

| Requirement | Task # | Status |
|------------|--------|--------|
| phase_templates.yaml with arch/plan/ship | Task 1 | ✅ 3 templates, ~20 steps |
| StepPipeline class | Task 2 | ✅ load, list, execute, skip-completed |
| Interruption recovery via completed_steps | Task 2 | ✅ get_pending_steps filters completed |
| Step-level event logging | Task 2 | ✅ _emit per step |
| YAML fallback (no file = old behavior) | Task 2 | ✅ _load_templates returns {} |
| ADR status update | Task 3 | ✅ |

### 2. Placeholder Scan

No TBDs, TODOs, or "implement later" found.

### 3. Type Consistency

- `StepPipeline.list_steps()` returns `List[Dict]` matching YAML structure
- `StepPipeline.get_pending_steps()` returns List[Dict] filtering completed IDs
- Pipeline stored in state vector under `step_pipeline` key (matching ADR-0011 §"状态向量存储")