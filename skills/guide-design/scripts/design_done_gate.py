"""Design-done gate integration for Hub RFC pending checks.

Provides check_hub_pending() which queries .rddf/state/.cross-repo-pending.json
and returns True (block) if any pending RFC entries exist.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def check_hub_pending() -> bool:
    """Check if any Hub RFC Issues are still pending.

    Returns:
        True if there are pending RFC Issues (gate should BLOCK).
        False if all approved or no pending entries.
    """
    if os.environ.get("SKIP_HUB_CHECK", "").lower() == "true":
        return False

    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    state_dir = os.path.join(project_root, ".rddf", "state")
    pending_file = os.path.join(state_dir, ".cross-repo-pending.json")

    if not os.path.exists(pending_file):
        return False

    try:
        state = json.loads(open(pending_file).read())
    except (json.JSONDecodeError, OSError):
        return False

    return any(e.get("status") == "pending" for e in state.get("entries", []))
