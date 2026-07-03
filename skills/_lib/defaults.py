"""Built-in defaults for spec-workflow v2 configuration.

The `DEFAULTS` dict is the lowest-priority source in the config merge order:
runtime params > loop.yaml > .spec-workflow.json > env vars > DEFAULTS.

Override any value via `.spec-workflow.json` or environment variables
(see `skills/_lib/config.py`).
"""
from __future__ import annotations
import copy


DEFAULTS = {
    "version": "2.0",
    "interaction": {
        "mode": "hybrid",  # one of: loop, menu, hybrid
        "menu_items": ["propose", "execute", "status", "archive"],
    },
    "loop": {
        "max_iterations": 100,
        "max_retries": 3,
        "retry_backoff_seconds": 5,
    },
    "state": {
        "path": ".spec-workflow/state-vector.json",
        "lock_timeout_seconds": 10.0,
    },
    "event_log": {
        "path": ".spec-workflow/event-log.jsonl",
        "max_size_mb": 50,
    },
    "gate": {
        "load_defaults": True,
        "auto_allow_warnings": True,
    },
    "sync": {
        "v1x_enabled": True,
        "conflict_resolution": "state_vector_wins",  # the only supported mode
    },
}


# Module-level path constants — exported for use as default argument values
# in other modules' function signatures. These mirror the corresponding
# entries in DEFAULTS above (state.path, event_log.path, etc.) but are
# immutable module-level strings, while DEFAULTS holds configurable values
# that can be overridden via `.spec-workflow.json` or environment variables.
STATE_VECTOR_PATH = ".spec-workflow/state-vector.json"
EVENT_LOG_PATH = ".spec-workflow/event-log.jsonl"
MEMORY_PATH = ".spec-workflow/memory.jsonl"
DETECTOR_PLUGIN_DIR = ".spec-workflow/detectors"
ACTION_PLUGIN_DIR = ".spec-workflow/actions"


def get_defaults() -> dict:
    """Return a deep copy of the defaults dict (safe to mutate)."""
    return copy.deepcopy(DEFAULTS)
