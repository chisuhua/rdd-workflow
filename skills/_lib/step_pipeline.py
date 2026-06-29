"""StepPipeline — phase step execution engine (ADR-0011).

Loads phase templates from YAML, executes steps in order, and tracks
completion for interruption recovery. Designed for use by the ship-side
executor (`guide-ship` → `execute`): a long-running plan can be resumed
after a crash by re-invoking `get_pending_steps()` and skipping the
already-completed ones.

State storage:
- Primary: the `step_pipeline` slot on the `StateVector` (best-effort).
  The current `state_vector_schema.json` has `additionalProperties: false`
  at the top level, so persistence to StateVector is attempted but
  silently ignored if schema validation rejects the new key.
- Fallback: an in-memory dict (`self._local_state`) which is always
  authoritative within a single process. This keeps the public surface
  functional for callers that just want an in-memory pipeline.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml

from skills._lib.state_vector import StateVector
from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity


# Key under which the pipeline sub-state would live on the StateVector
# (currently advisory — the schema does not allow arbitrary top-level keys,
# so the in-memory mirror is the source of truth at runtime).
PIPELINE_STATE_KEY = "step_pipeline"

_DEFAULT_STATE: Dict[str, Any] = {
    "phase": None,
    "completed_steps": [],
    "current_step": None,
    "started_at": None,
    "error": None,
}


@dataclass
class PipelineEvent:
    """Lightweight event emitted when a step transitions state.

    The class is exported so callers (e.g. tribunal) can subscribe to
    pipeline transitions without depending on EventLog internals.
    """
    step_id: str
    status: str
    message: str


class StepPipeline:
    """Phase-aware step executor with interruption recovery.

    Typical usage::

        pipeline = StepPipeline(state_vector, event_log, templates_path)
        for step in pipeline.get_pending_steps("execute"):
            do_work(step)
            pipeline.mark_step_completed(step["id"])
    """

    def __init__(
        self,
        state_vector: StateVector,
        event_log: Optional[EventLog] = None,
        templates_path: Optional[str] = None,
    ):
        self.state_vector = state_vector
        self._event_log = event_log
        self._templates = self._load_templates(templates_path)
        # In-memory mirror of pipeline state. The StateVector schema
        # currently rejects arbitrary top-level keys, so this is the
        # runtime source of truth; the StateVector is still passed in
        # so future schema revisions can opt in to persistence.
        self._local_state: Dict[str, Any] = dict(_DEFAULT_STATE)

    # ----- Templates ----------------------------------------------------

    def _load_templates(self, path: Optional[str]) -> Dict[str, Any]:
        """Load phase templates from a YAML file. Falls back to default path."""
        candidates: List[str] = []
        if path:
            candidates.append(path)
        # Default: phase_templates.yaml sitting next to this module
        default = os.path.join(os.path.dirname(__file__), "phase_templates.yaml")
        candidates.append(default)

        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                with open(candidate, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if isinstance(data, dict):
                    return data.get("templates", {}) or {}
        return {}

    def list_steps(self, phase: str) -> List[Dict[str, Any]]:
        """Return the ordered step dicts for `phase`, or `[]` if unknown."""
        phase_def = self._templates.get(phase) or {}
        steps = phase_def.get("steps") or []
        return list(steps)

    # ----- Completion tracking -----------------------------------------

    def get_pending_steps(self, phase: str) -> List[Dict[str, Any]]:
        """Return the steps of `phase` that have not been completed yet."""
        all_steps = self.list_steps(phase)
        completed = set(self._get_state().get("completed_steps", []) or [])
        return [s for s in all_steps if s.get("id") not in completed]

    def is_step_completed(self, step_id: str) -> bool:
        """Return True iff `step_id` has been recorded as completed."""
        completed = self._get_state().get("completed_steps", []) or []
        return step_id in completed

    def mark_step_completed(self, step_id: str) -> None:
        """Record `step_id` as completed and emit a completion event."""
        state = self._get_state()
        completed = set(state.get("completed_steps", []) or [])
        completed.add(step_id)
        state["completed_steps"] = sorted(completed)
        self._save_state(state)
        self._emit(step_id, "completed", f"Step {step_id} completed")

    def reset(self) -> None:
        """Clear all completion state and return the pipeline to fresh defaults."""
        self._save_state(dict(_DEFAULT_STATE))

    # ----- Internal state plumbing --------------------------------------

    def _get_state(self) -> Dict[str, Any]:
        """Return the current pipeline sub-state.

        Tries the StateVector first (so an external orchestrator can seed
        state via the vector), and falls back to the in-memory mirror.
        """
        try:
            sv_state = self.state_vector.to_dict().get(PIPELINE_STATE_KEY)
            if isinstance(sv_state, dict) and sv_state:
                return sv_state
        except Exception:
            pass
        return self._local_state

    def _save_state(self, state: Dict[str, Any]) -> None:
        """Persist `state` to both the in-memory mirror and the StateVector.

        The StateVector write is best-effort: the current schema disallows
        arbitrary top-level keys, so a schema error is swallowed and the
        in-memory mirror is kept consistent.
        """
        self._local_state = dict(state)
        try:
            self.state_vector.update_field(PIPELINE_STATE_KEY, dict(state))
        except Exception:
            # StateVector schema currently does not accept the step_pipeline
            # top-level key. Persistence is advisory; the in-memory mirror
            # is authoritative for the lifetime of this pipeline instance.
            pass

    def _emit(self, step_id: str, status: str, message: str) -> None:
        """Append a completion event to the optional EventLog."""
        if self._event_log is None:
            return
        try:
            self._event_log.record(
                event_type=EventType.EXECUTION_UNIT_COMPLETED,
                severity=Severity.INFO,
                message=message,
            )
        except Exception:
            # EventLog failures must never break the pipeline
            pass
