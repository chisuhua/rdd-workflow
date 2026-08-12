"""Cat 1 — Validate .rddf/state/*.json against _lib/schemas/*.json."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

import jsonschema
from referencing import Registry, Resource

from doctor_render import Finding, Severity
from path_resolver import LibPathNotFoundError, resolve_real_lib_path


# Map state file basename → schema basename
_STATE_FILES = {
    "state_vector.json": "state_vector_schema.json",
    "sessions.json": "sessions_schema.json",
    "iteration.json": "iteration_schema.json",
    "deps_analysis.json": "deps_analysis_schema.json",
}


def _build_schema_registry(schema_path: Path) -> Registry:
    """Load all sibling *.json schemas into a referencing.Registry.

    Schemas with ``$id`` are registered under that $id so that external
    ``$ref: "<id>.json"`` lookups inside any schema resolve correctly.
    Returns an empty Registry if no schemas have $id.
    """
    registry: Registry = Registry()
    for sibling in sorted(schema_path.parent.glob("*.json")):
        try:
            data = json.loads(sibling.read_text())
        except json.JSONDecodeError:
            continue
        if "$id" in data:
            registry = registry.with_resource(
                uri=data["$id"], resource=Resource.from_contents(data)
            )
    return registry


def run(project_root: Path | None = None) -> List[Finding]:
    """Run cat-1 against project_root."""
    import os
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    os.environ.setdefault("RDDF_PROJECT_ROOT", str(project_root.resolve()))
    state_dir = project_root / ".rddf" / "state"
    if not state_dir.is_dir():
        return []

    findings: List[Finding] = []
    for state_name, schema_name in _STATE_FILES.items():
        state_file = state_dir / state_name
        if not state_file.is_file():
            continue
        try:
            schema_path = resolve_real_lib_path(f"schemas/{schema_name}")
        except LibPathNotFoundError as e:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="state",
                file=str(state_file),
                line=None,
                snippet=f"schema {schema_name} not found",
                fix_hint=f"check that _lib/schemas/{schema_name} exists (real path)",
            ))
            continue
        try:
            schema = json.loads(schema_path.read_text())
            data = json.loads(state_file.read_text())
        except json.JSONDecodeError as e:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="state",
                file=str(state_file),
                line=e.lineno,
                snippet=f"invalid JSON: {e.msg}",
                fix_hint="re-run guide-plan or restore from backup",
            ))
            continue

        registry = _build_schema_registry(schema_path)
        validator = jsonschema.Draft7Validator(schema, registry=registry)
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="state",
                file=str(state_file),
                line=None,
                snippet=f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}",
                fix_hint="re-run guide-plan or manually migrate to current schema",
            ))
    return findings