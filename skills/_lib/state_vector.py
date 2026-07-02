"""Unified state vector — single source of truth for spec-workflow v2.

Stored as JSON at `.spec-workflow/state-vector.json`. All writes are atomic
(write-temp-then-rename) and protected by a `FileLock` (10s timeout). All
writes are schema-validated (JSON Schema draft-07) and checksummed
(SHA-256 of canonical JSON) for corruption detection.
"""
from __future__ import annotations
import copy
import datetime
import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import jsonschema

from skills._lib.lock import FileLock, LockTimeout

logger = logging.getLogger(__name__)


SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "schemas", "state_vector_schema.json"
)
_LOCK_TIMEOUT = 10.0
_SCHEMA_CACHE: Optional[dict] = None
_VALIDATOR_CACHE: Optional[jsonschema.Draft7Validator] = None


def _load_schema() -> dict:
    """Load the JSON Schema once, cache in memory for validation performance."""
    global _SCHEMA_CACHE, _VALIDATOR_CACHE
    if _SCHEMA_CACHE is None:
        with open(SCHEMA_PATH) as f:
            _SCHEMA_CACHE = json.load(f)
        assert _SCHEMA_CACHE is not None
        _VALIDATOR_CACHE = jsonschema.Draft7Validator(_SCHEMA_CACHE)
    assert _SCHEMA_CACHE is not None  # for type checkers
    return _SCHEMA_CACHE


def _get_validator() -> jsonschema.Draft7Validator:
    """Return a cached Draft7Validator (≈8x faster than jsonschema.validate per call)."""
    _load_schema()
    assert _VALIDATOR_CACHE is not None
    return _VALIDATOR_CACHE


class StateVectorError(Exception):
    """Raised on validation failure, corruption, or I/O error."""


def _canonical_json(data: dict) -> str:
    """Serialize dict with sorted keys and no extra whitespace (for checksum stability)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_checksum(data: dict) -> str:
    """SHA-256 of canonical JSON, excluding the `metadata.checksum` field itself."""
    d = copy.deepcopy(data)
    if "metadata" in d and isinstance(d["metadata"], dict):
        d["metadata"].pop("checksum", None)
    return hashlib.sha256(_canonical_json(d).encode("utf-8")).hexdigest()


class StateVector:
    """Unified workflow state. All access goes through the lock + schema validator."""

    def __init__(self, data: dict):
        self._data = data
        self._validate(data)

    # ----- Constructors --------------------------------------------------

    @classmethod
    def create_default(cls) -> "StateVector":
        """Return a fresh default state vector with version 2.0 and current timestamps."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return cls({
            "version": "2.0",
            "goal": None,
            "arch_side": {
                "phase": "idle",
                "current_change": None,
                "completed_changes": [],
            },
            "plan_side": {
                "active_change": None,
                "plan_file": None,
                "worktree_path": None,
            },
            "ship_side": {
                "current_phase": "idle",
                "progress": {"complete": 0, "total": 0},
            },
            "loop_state": {
                "mode": "idle",
                "iteration": 0,
                "last_action": None,
                "last_action_at": None,
            },
            "session_management": {
                "current_session": None,
                "active_sessions": [],
                "session_statistics": {"total": 0, "active": 0, "completed": 0, "failed": 0},
            },
            "dependency_graph": {
                "nodes": [],
                "edges": [],
                "execution_order": [],
            },
            "memory": {"notes": "", "learnings": []},
            "metadata": {
                "spec_workflow_version": "2.0.0",
                "git_commit": None,
                "created_at": now,
                "updated_at": now,
                "checksum": "",  # populated on save
            },
        })

    @classmethod
    def load(cls, path: str, verify_checksum: bool = True) -> "StateVector":
        """Load state vector from disk. Returns default if file missing.

        Raises:
            StateVectorError: if file exists but is corrupted (bad checksum) or invalid.
        """
        if not os.path.exists(path):
            return cls.create_default()
        try:
            with FileLock(path + ".lock", timeout=_LOCK_TIMEOUT):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except LockTimeout as e:
            raise StateVectorError(f"Could not acquire lock for {path}: {e}") from e
        except json.JSONDecodeError as e:
            raise StateVectorError(f"State vector at {path} is not valid JSON: {e}") from e

        if verify_checksum and data.get("metadata", {}).get("checksum"):
            expected = data["metadata"]["checksum"]
            actual = _compute_checksum(data)
            if expected != actual:
                raise StateVectorError(
                    f"State vector at {path} failed checksum verification "
                    f"(expected {expected[:12]}..., got {actual[:12]}...)"
                )
        return cls(data)

    # ----- Validation ---------------------------------------------------

    @staticmethod
    def _validate(data: dict) -> None:
        validator = _get_validator()
        errors = list(validator.iter_errors(data))
        if errors:
            e = errors[0]
            raise StateVectorError(f"State vector failed schema validation: {e.message}") from e

    # ----- Mutation -----------------------------------------------------

    def update_field(self, dotted_key: str, value: Any) -> None:
        """Update a (possibly nested) field by dotted path. Validates in-place."""
        new_data = copy.deepcopy(self._data)
        keys = dotted_key.split(".")
        cur = new_data
        for k in keys[:-1]:
            if k not in cur or not isinstance(cur[k], dict):
                raise StateVectorError(f"Cannot traverse into non-dict at '{k}'")
            cur = cur[k]
        cur[keys[-1]] = value
        new_data["metadata"]["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._validate(new_data)
        self._data = new_data

    # ----- Persistence --------------------------------------------------

    def save(self, path: str) -> None:
        """Atomically write state vector to disk, protected by file lock."""
        # Always recompute checksum and updated_at on save
        self._data["metadata"]["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._data["metadata"]["checksum"] = _compute_checksum(self._data)
        self._validate(self._data)

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        try:
            with FileLock(path + ".lock", timeout=_LOCK_TIMEOUT):
                # Atomic write: write to temp, then rename
                fd, tmp = tempfile.mkstemp(
                    dir=os.path.dirname(path) or ".",
                    prefix=".state-vector-", suffix=".tmp",
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(self._data, f, indent=2, sort_keys=True, ensure_ascii=False)
                        f.write("\n")
                    os.replace(tmp, path)
                except Exception:
                    if os.path.exists(tmp):
                        os.unlink(tmp)
                    raise
        except LockTimeout as e:
            raise StateVectorError(f"Could not acquire lock to save {path}: {e}") from e

    # ----- Accessors ----------------------------------------------------

    def to_dict(self) -> dict:
        """Return a deep copy of the underlying data (safe to mutate)."""
        return copy.deepcopy(self._data)

    def get_field(self, dotted_key: str, default: Any = None) -> Any:
        """Read a field by dotted path. Returns `default` if any segment is missing."""
        cur: Any = self._data
        for k in dotted_key.split("."):
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur
