"""Builder feedback routing to .planner-feedback.json (per spec §3.5.2, batch 4)."""
import json
import os
from pathlib import Path

from _lib.core.lock import FileLock
from _lib.core.atomic_write import atomic_write_json


def route_feedback(
    feedback_entry: dict,
    project_root: str,
    accept_builder_source: bool = True,
    current_change=None,
) -> dict:
    should_promote = (
        feedback_entry.get("kind") == "ac-fail"
        and accept_builder_source
        and (current_change is None or feedback_entry.get("ref_change") == current_change)
    )
    if should_promote:
        _append_to_planner_feedback(project_root, feedback_entry)
    return {
        "feedback_id": feedback_entry.get("feedback_id"),
        "routed_to_planner_feedback": should_promote,
        "routed_at": __import__("datetime").datetime.utcnow().isoformat(),
    }


def _append_to_planner_feedback(project_root: str, feedback_entry: dict) -> None:
    planner_feedback_path = Path(project_root) / ".rddf" / "state" / ".planner-feedback.json"
    planner_feedback_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(planner_feedback_path) + ".lock", timeout=10):
        if planner_feedback_path.exists():
            data = json.loads(planner_feedback_path.read_text())
        else:
            data = {
                "schema": "planner-feedback-v1",
                "version": 1,
                "owner": "rdd-planner",
                "feedbacks": [],
                "summary": {"open_critical": 0, "open_warning": 0, "open_info": 0},
            }
        entry = dict(feedback_entry)
        entry["from_builder"] = True
        data["feedbacks"].append(entry)
        data["summary"]["open_info"] = data["summary"].get("open_info", 0) + 1
        atomic_write_json(str(planner_feedback_path), data)