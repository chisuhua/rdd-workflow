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
    # 6 new cross-repo federation schemas (ADR-0030 + 7 related proposals)
    ".cross-repo-pending.json": "cross_repo_pending_schema.json",
    ".cross-repo-audit.jsonl": "cross_repo_audit_schema.json",
    ".mcp-trace.jsonl": "mcp_trace_schema.json",
    ".contract-cache.json": "contract_cache_schema.json",
    ".cross-repo-deps-cache.json": "cross_repo_deps_cache_schema.json",
    ".hub-metrics.json": "hub_metrics_schema.json",
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


def _check_schema_version_metadata(project_root: Path) -> List[Finding]:
    """Scan _lib/schemas/*.json for missing top-level 'version' field.

    Per ADR-0016 + fix-schema-version-field proposal: every schema must
    declare a top-level `"version": {"const": "v1"}` metadata field.
    Missing → CRITICAL.

    Schema metadata `version` is distinct from any `properties.version`
    data field; JSON Schema draft 2020-12 ignores unknown top-level
    keywords, so the metadata does not interfere with data validation.
    """
    findings: List[Finding] = []
    schemas_root = project_root / "skills" / "_lib" / "schemas"
    if not schemas_root.is_dir():
        return findings
    for schema_path in sorted(schemas_root.glob("*.json")):
        try:
            schema = json.loads(schema_path.read_text())
        except json.JSONDecodeError:
            continue
        if "version" not in schema:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="state",
                file=str(schema_path),
                line=None,
                snippet="missing top-level 'version' field (ADR-0016 violation)",
                fix_hint=(
                    'add "version": {"const": "v1", "description": "..."} '
                    "to schema top level"
                ),
            ))
            continue
        if not isinstance(schema["version"], dict) or schema["version"].get("const") != "v1":
            findings.append(Finding(
                severity=Severity.WARNING,
                category="state",
                file=str(schema_path),
                line=None,
                snippet="version.const is not 'v1' (schema metadata drift)",
                fix_hint="update version.const to 'v1' per ADR-0016 baseline",
            ))
    return findings


def run(project_root: Path | None = None) -> List[Finding]:
    """Run cat-1 against project_root."""
    import os
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
        os.environ.setdefault("RDDF_PROJECT_ROOT", str(project_root.resolve()))
    state_dir = project_root / ".rddf" / "state"
    if not state_dir.is_dir():
        return []

    findings = _check_schema_version_metadata(project_root)

    findings: List[Finding] = []
    for state_name, schema_name in _STATE_FILES.items():
        state_file = state_dir / state_name
        if not state_file.is_file():
            continue
        try:
            schema_path = resolve_real_lib_path(f"schemas/{schema_name}", project_root=project_root)
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