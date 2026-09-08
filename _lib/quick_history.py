"""Audit-log data layer for rdd-quick (ADR-0047).

Public API:
- validate_entry(entry: dict) -> bool
- append_entry(entry: dict, history_file: Path) -> None  (atomic, raises on validation failure)
- read_entries(history_file: Path) -> list[dict]

Stdlib + jsonschema only. NO imports from skills._lib.* to keep zero-pollution
contract visible to readers (per design.md D8).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft7Validator

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "quick_history_schema.json"


def _load_validator() -> Draft7Validator:
    schema = json.loads(_SCHEMA_PATH.read_text())
    return Draft7Validator(schema)


_VALIDATOR: Draft7Validator | None = None


def _validator() -> Draft7Validator:
    # Lazy singleton — avoids re-parsing the schema on every call.
    global _VALIDATOR
    if _VALIDATOR is None:
        _VALIDATOR = _load_validator()
    return _VALIDATOR


def validate_entry(entry: dict[str, Any]) -> bool:
    """Return True iff *entry* satisfies the v1 audit-log schema.

    Validation is fail-closed: an invalid entry MUST be rejected so callers
    (especially append_history.py) cannot corrupt the audit log.
    """
    if not isinstance(entry, dict):
        return False
    return _validator().is_valid(entry)


def append_entry(entry: dict[str, Any], history_file: Path) -> None:
    """Append *entry* to *history_file* as a single JSONL line.

    Validation runs FIRST (no partial writes on failure). The actual file write
    is atomic via temp-file + os.replace() — concurrent readers always see the
    prior stable state or the fully appended state, never a partial line.

    Raises:
        ValueError: when *entry* fails schema validation
        OSError: when the file cannot be written (propagated)
    """
    if not validate_entry(entry):
        raise ValueError("quick_history entry fails schema validation (v1)")

    history_file = Path(history_file)
    history_file.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)

    # Read prior content (may be absent — first entry ever).
    prior = ""
    if history_file.exists():
        prior = history_file.read_text()
        # Guarantee single trailing newline so appended line is its own JSONL record.
        if prior and not prior.endswith("\n"):
            prior += "\n"

    new_content = prior + line + "\n"

    # Atomic write: temp file in same directory, then os.replace().
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{history_file.name}.",
        suffix=".tmp",
        dir=str(history_file.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, history_file)
    except Exception:
        # Clean up the temp file on any failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_entries(history_file: Path) -> list[dict[str, Any]]:
    """Return every well-formed JSONL entry from *history_file*.

    Blank lines and malformed lines are skipped silently — the audit log is
    append-only and corrupted past data MUST NOT block current operations.
    However, future writes will still validate against the schema.
    """
    history_file = Path(history_file)
    if not history_file.exists():
        return []

    entries: list[dict[str, Any]] = []
    for line in history_file.read_text().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            entries.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return entries


# Imported late to keep the module-level imports minimal.
import tempfile  # noqa: E402  (kept at bottom to emphasize public API above)