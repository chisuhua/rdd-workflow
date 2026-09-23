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
# value=None means no formal JSON Schema — use per-line JSON check + custom logic
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
    # v3 (feat-guide-orchestrator-session-event-bus): events.jsonl workflow bus.
    # No formal schema — custom per-line + last_seen_offset checks (see _check_events_jsonl).
    "events.jsonl": None,
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

    Uses resolve_real_lib_path to find the real _lib/schemas/ directory
    (not the shim at skills/_lib/schemas/), ensuring we don't flag shim
    schemas that exist only for backward compat.
    """
    findings: List[Finding] = []
    try:
        schemas_root = resolve_real_lib_path("schemas", project_root=project_root)
    except LibPathNotFoundError:
        return findings
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

    # v3 (feat-guide-orchestrator-session-event-bus): custom check for events.jsonl
    # (no formal JSON Schema — per-line JSON + last_seen_offset reference validation).
    events_file = state_dir / "events.jsonl"
    if events_file.is_file():
        findings.extend(_check_events_jsonl(events_file, state_dir))

    for state_name, schema_name in _STATE_FILES.items():
        state_file = state_dir / state_name
        if not state_file.is_file():
            continue
        # v3: schema_name=None means no formal schema (e.g. events.jsonl).
        # Use per-line JSON check (handled below for .jsonl) without schema validation.
        if schema_name is None:
            if state_file.suffix == ".jsonl":
                with open(state_file) as f:
                    for line_no, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            json.loads(line)
                        except json.JSONDecodeError as e:
                            findings.append(Finding(
                                severity=Severity.CRITICAL,
                                category="state",
                                file=str(state_file),
                                line=line_no,
                                snippet=f"invalid JSON: {e.msg}",
                                fix_hint="check events.jsonl syntax (per-line JSON)",
                            ))
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
        except json.JSONDecodeError as e:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="state",
                file=str(schema_path),
                line=e.lineno,
                snippet=f"invalid JSON: {e.msg}",
                fix_hint="check schema file syntax",
            ))
            continue

        # JSONL: multi-document, parse per-line (fix: was json.load single-doc)
        if state_file.suffix == ".jsonl":
            with open(state_file) as f:
                for line_no, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as e:
                        findings.append(Finding(
                            severity=Severity.CRITICAL,
                            category="state",
                            file=str(state_file),
                            line=line_no,
                            snippet=f"invalid JSON: {e.msg}",
                            fix_hint="re-run guide-plan or restore from backup",
                        ))
            continue

        try:
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


def _check_events_jsonl(events_file: Path, state_dir: Path) -> List[Finding]:
    """Validate events.jsonl workflow event bus (v3 per feat-guide-orchestrator-session-event-bus).

    Two assertions per AC-12:
    1. Each line is valid JSON.
    2. stage_guide.goal.last_seen_offset references a valid line index (0-based).

    v3 line numbers are 0-based (events_log.py read_since contract). A
    last_seen_offset >= total_lines means the next read returns empty until
    new events arrive; if last_seen_offset > total_lines by a large margin,
    it's likely a stale reference after archive_events that wasn't reset.
    """
    findings: List[Finding] = []
    # Parse all lines; track total line count and per-line parse success.
    valid_lines = 0
    bad_line_nos: List[int] = []
    with open(events_file) as f:
        for line_no, raw in enumerate(f, 0):  # 0-based line numbering
            line = raw.strip()
            if not line:
                continue
            try:
                json.loads(line)
                valid_lines += 1
            except json.JSONDecodeError as e:
                bad_line_nos.append(line_no)
    # Malformed line findings (per-line JSON check).
    for line_no in bad_line_nos:
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="state",
            file=str(events_file),
            line=line_no + 1,  # 1-based for display
            snippet=f"invalid JSON in events.jsonl line {line_no + 1}",
            fix_hint="re-run hooks.sh to rewrite events, or restore from archive",
        ))

    # stage_guide.goal.last_seen_offset reference check (AC-12 assertion #2).
    sessions_file = state_dir / "sessions.json"
    if not sessions_file.is_file():
        return findings
    try:
        sessions_data = json.loads(sessions_file.read_text())
    except json.JSONDecodeError:
        # Session file malformed — already reported by the main loop; skip here.
        return findings
    for session in sessions_data.get("sessions", []):
        if session.get("kind") != "stage_guide":
            continue
        goal = session.get("goal", {})
        offset = goal.get("last_seen_offset")
        if not isinstance(offset, int):
            continue
        # last_seen_offset is 0-based line index (events_log.py read_since contract).
        # If offset > total valid lines, the next read returns [] until new events arrive.
        # This is allowed (will re-read on next event) — only flag if massively out of range.
        if offset > valid_lines + 1000:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="state",
                file=str(sessions_file),
                line=None,
                snippet=(
                    f"stage_guide session {session.get('session_id')} has "
                    f"goal.last_seen_offset={offset} which is far beyond events.jsonl "
                    f"line count ({valid_lines}); possible stale reference after "
                    f"archive_events (see ADR-0055 §Metis B4 — last_seen_offset should reset to 0 on archive)"
                ),
                fix_hint=(
                    "re-emit guide session or manually update goal.last_seen_offset "
                    "to a valid line index (0-based) or 0 for fresh re-read"
                ),
            ))
    return findings