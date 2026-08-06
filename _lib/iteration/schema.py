"""Iteration state - schema constants and validation helpers.

Extracted from ``skills/_lib/iteration.py`` (v2.0.8 split). This module
holds the JSON-Schema plumbing (path constants, status enums, validation
helpers) shared by ``store.py`` (CRUD) and ``render.py`` (CLI output).

The schema file itself lives at ``skills/_lib/schemas/iteration_schema.json``
- the same location it has always been. Because this module now lives at
``skills/_lib/iteration/schema.py`` (one directory deeper than the old
``skills/_lib/iteration.py``), ``SCHEMA_PATH`` is computed relative to the
parent ``_lib/`` directory so the path resolves identically to the
pre-split module.

All public names in this module are re-exported from
``skills._lib.iteration`` (the package ``__init__.py``), so existing
``from skills._lib.iteration import SCHEMA_PATH`` imports continue to work
unchanged.
"""
from __future__ import annotations

import json
import os
from typing import Any

import jsonschema
import referencing
from referencing.exceptions import NoSuchResource

# SCHEMA_PATH points at ``skills/_lib/schemas/iteration_schema.json``.
# This module lives at ``skills/_lib/iteration/schema.py`` (one directory
# deeper than the original ``skills/_lib/iteration.py``), so we climb one
# level (``..``) to land on ``_lib/`` before joining ``schemas/...``.
# The resolved path is byte-identical to the pre-split value.
SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "schemas",
    "iteration_schema.json",
)

_DEFAULT_PHASE = "default"
_VALID_STATUSES = ("planned", "proposed", "in_worktree", "review", "completed", "archived")
# Statuses that block a dependent planned change from being filled.
# A planned change's blocker must be in one of these statuses to count as
# "still blocking". When a blocker transitions out (e.g. to archived), the
# dependent becomes "unblocked" and ready for fill.
_BLOCKING_STATUSES = ("planned", "in_worktree", "review")

# Sentinel for distinguishing "argument not passed" from "argument passed
# as None". Used by set_deps_info so callers can explicitly clear a
# field (blocker=None) without affecting it.
_UNSET: Any = object()


def _load_schema() -> dict:
    """Load the JSON Schema (cached on first call)."""
    if not os.path.isfile(SCHEMA_PATH):
        raise FileNotFoundError(
            f"iteration schema not found at {SCHEMA_PATH}; "
            f"the iteration.py module requires it for validation"
        )
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def _load_registry() -> referencing.Registry:
    """Build a referencing.Registry with all local sub-schemas pre-registered."""
    schemas_dir = os.path.dirname(SCHEMA_PATH)
    schema_data = _load_schema()
    registry = referencing.Registry()
    sid = schema_data.get("$id")
    if sid:
        registry = registry.with_resource(sid, referencing.Resource.from_contents(schema_data))
    registry = _register_refs(registry, schema_data, schemas_dir)
    return registry


def _register_refs(registry: referencing.Registry, schema: dict, base_dir: str) -> referencing.Registry:
    """Recursively register $ref targets in the schema."""
    for key, val in schema.items():
        if key == "$ref" and isinstance(val, str) and val.endswith(".json") and not val.startswith("#"):
            ref_path = os.path.join(base_dir, val)
            if os.path.isfile(ref_path) and not _is_registered(registry, ref_path):
                with open(ref_path) as f:
                    ref_schema = json.load(f)
                rid = ref_schema.get("$id")
                if rid:
                    registry = registry.with_resource(rid, referencing.Resource.from_contents(ref_schema))
                registry = _register_refs(registry, ref_schema, base_dir)
        elif isinstance(val, dict):
            registry = _register_refs(registry, val, base_dir)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    registry = _register_refs(registry, item, base_dir)
    return registry


def _is_registered(registry: referencing.Registry, path: str) -> bool:
    try:
        with open(path) as f:
            data = json.load(f)
        rid = data.get("$id")
        if rid:
            try:
                registry.get_or_retrieve(rid)
                return True
            except NoSuchResource:
                return False
    except (json.JSONDecodeError, OSError):
        return False
    return False


def _validate(data: dict) -> None:
    """Validate iteration data against the schema. Raises jsonschema.ValidationError on failure."""
    schema = _load_schema()
    registry = _load_registry()
    validator = jsonschema.Draft7Validator(schema, registry=registry)
    errors = list(validator.iter_errors(data))
    if errors:
        raise jsonschema.ValidationError(errors[0].message)
