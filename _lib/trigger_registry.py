"""TriggerRegistry — persistent storage for triggers in .rddf/state/triggers.json.

Uses atomic write pattern (temp + rename) to prevent corruption on crash.
"""
from __future__ import annotations
import json
import os
import tempfile

from skills._lib.triggers import Trigger, TriggerManager

DEFAULT_REGISTRY_PATH = ".rddf/state/triggers.json"


class TriggerRegistry:
    """Persistent registry with atomic JSON writes."""

    def __init__(self, project_root: str = ".", path: str = DEFAULT_REGISTRY_PATH):
        self.project_root = project_root
        self.path = os.path.join(project_root, path)

    def load(self) -> TriggerManager:
        """Load triggers from disk. Returns empty manager if file missing or corrupt."""
        if not os.path.isfile(self.path):
            return TriggerManager()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            triggers = [Trigger.from_dict(t) for t in data.get("triggers", [])]
            return TriggerManager(triggers=triggers)
        except (json.JSONDecodeError, OSError, KeyError, TypeError):
            # Corrupt or unreadable — return empty rather than crashing
            return TriggerManager()

    def save(self, manager: TriggerManager) -> None:
        """Atomically save triggers to disk via temp file + rename."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        data = {"version": 1, "triggers": [t.to_dict() for t in manager.triggers]}
        # Write to temp file then rename for atomicity
        dir_name = os.path.dirname(self.path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix="triggers.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.path)
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def update(self, manager: TriggerManager) -> None:
        """Convenience: save the manager."""
        self.save(manager)
