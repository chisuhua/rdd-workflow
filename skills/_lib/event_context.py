"""Event context — reads the current state vector to populate event `context` fields.

Provides a single helper `current_context()` used by EventLog.record() to attach
the active goal, change, and loop iteration to every event.
"""
from __future__ import annotations
import os
from typing import Any

from skills._lib.state_vector import StateVector


DEFAULT_STATE_PATH = ".spec-workflow/state-vector.json"


def current_context(state_path: str = DEFAULT_STATE_PATH) -> dict:
    """Return a dict snapshot of relevant state for attaching to an event.

    If the state vector cannot be loaded, returns an empty dict (events are
    still recorded; just without context).
    """
    try:
        sv = StateVector.load(state_path, verify_checksum=False)
        data = sv.to_dict()
        return {
            "goal": data.get("goal"),
            "active_change": data.get("plan_side", {}).get("active_change")
                              or data.get("arch_side", {}).get("current_change"),
            "arch_phase": data.get("arch_side", {}).get("phase"),
            "ship_phase": data.get("ship_side", {}).get("current_phase"),
            "loop_mode": data.get("loop_state", {}).get("mode"),
            "loop_iteration": data.get("loop_state", {}).get("iteration", 0),
        }
    except Exception:
        return {}
