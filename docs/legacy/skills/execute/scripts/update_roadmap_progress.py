"""Update roadmap-state.json from roadmap-meta.yaml (Oracle C1 safe).

Extracted from skills/execute.md L296-L346 (~50-line inline bash block).

Original code read roadmap-meta.yaml (for phase/category), then updated
roadmap-state.json to mark a change as completed and re-evaluate the
all_changes_complete gate_status.

Public function:
- update_roadmap_progress(project_root, change_name) -> dict
"""

import json
import os
import sys
from typing import Any, Dict, Optional


def _read_meta_yaml(meta_path: str) -> Optional[Dict[str, Any]]:
    """Read roadmap-meta.yaml, return {phase, category} or None on failure."""
    content: dict = {}
    try:
        import yaml
        with open(meta_path) as f:
            content = yaml.safe_load(f) or {}
    except ImportError:
        # Fallback: simple key-value parser for roadmap block
        try:
            with open(meta_path) as f:
                current_key = None
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("phase:"):
                        content["phase"] = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                    elif stripped.startswith("category:"):
                        content["category"] = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        except Exception:
            return None
    except Exception:
        return None

    roadmap = content.get("roadmap", content)
    phase = roadmap.get("phase")
    category = roadmap.get("category")
    if not phase or not category:
        return None
    return {"phase": phase, "category": category}


def update_roadmap_progress(
    project_root: str,
    change_name: str,
) -> Dict[str, Any]:
    """Update roadmap-state.json with completed change. Returns result dict.

    - Reads roadmap-meta.yaml to find phase/category
    - Adds change_name to completed_changes (idempotent)
    - Re-evaluates all_changes_complete gate_status

    Args:
        project_root: Absolute path to project root.
        change_name: Name of the change to mark complete.

    Returns:
        Dict with keys: change_name, phase, category, completed_changes,
        all_changes_complete, OR error (on failure).
    """
    # Locate and read roadmap-meta.yaml
    meta_path = os.path.join(
        project_root, "openspec", "changes", change_name, "roadmap-meta.yaml"
    )
    if not os.path.isfile(meta_path):
        return {"error": f"roadmap-meta.yaml not found at {meta_path}"}

    meta = _read_meta_yaml(meta_path)
    if not meta:
        return {"error": f"Could not parse roadmap-meta.yaml at {meta_path}"}

    change_phase = meta["phase"]
    change_category = meta["category"]

    # Locate and read roadmap-state.json
    state_path = os.path.join(project_root, ".rddf", "state", "roadmap-state.json")
    if not os.path.isfile(state_path):
        return {"error": f"roadmap-state.json not found at {state_path}"}

    try:
        with open(state_path) as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {"error": f"Failed to read roadmap-state.json: {e}"}

    # Locate the phase and category in the state
    phases = state.get("phases", {})
    if change_phase not in phases:
        return {"error": f"Phase '{change_phase}' not found in roadmap-state.json"}

    phase_data = phases[change_phase]
    categories = phase_data.get("categories", {})
    if change_category not in categories:
        return {"error": f"Category '{change_category}' not found in phase '{change_phase}'"}

    cat_data = categories[change_category]

    # Mark change as completed (idempotent)
    completed = cat_data.get("completed_changes", [])
    if change_name not in completed:
        completed.append(change_name)
        cat_data["completed_changes"] = completed

    # Re-evaluate: are all changes in this phase complete?
    all_complete = True
    for cat_id, cat_info in categories.items():
        total = len(cat_info.get("changes", []))
        done_count = len(cat_info.get("completed_changes", []))
        if done_count < total:
            all_complete = False
            break

    # Update gate_status
    if "gate_status" not in phase_data:
        phase_data["gate_status"] = {}
    phase_data["gate_status"]["all_changes_complete"] = all_complete

    # Write back
    try:
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
    except OSError as e:
        return {"error": f"Failed to write roadmap-state.json: {e}"}

    return {
        "change_name": change_name,
        "phase": change_phase,
        "category": change_category,
        "completed_changes": completed,
        "all_changes_complete": all_complete,
    }