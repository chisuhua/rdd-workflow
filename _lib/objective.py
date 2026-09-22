"""Parser + validator + grace helper for objective files.

Objective files live in `.rddf/roadmap/objectives/*.md` and are owned by
rdd-planner per ADR-0028 role model. They are NOT openspec changes; they
are source-of-truth artifacts for cross-sprint complex targets that span
multiple openspec changes.

Design references:
- D5: status enum (active/deferred/completed/archived)
- D6: ledger kind enum (5 values)
- D7: frontmatter 9 required fields
- D9: N/A format constraint `^N/A — .+$` in section 10
- D11: grace check via review_by

This module is stdlib-only (yaml + re + datetime). No external deps.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Constants — single source of truth, consumed by _lib/cli/objective_cmd.py
# and skills/rdd-doctor/scripts/checks/objective_*.py.
# ---------------------------------------------------------------------------

STATUS_ENUM = frozenset({"active", "deferred", "completed", "archived"})
PRIORITY_ENUM = frozenset({"P0", "P1", "P2"})
KIND_ENUM = frozenset(
    {"deferral-rationale", "go-decision", "sprint-review", "scope-change", "adr-amendment"}
)
REQUIRED_SECTIONS: tuple[str, ...] = ("## 1.", "## 2.", "## 3.", "## 9.", "## 10.", "## 11.")
OPTIONAL_SECTIONS: tuple[str, ...] = ("## 5.",)
NA_PATTERN = re.compile(r"^N/A — .+$", re.MULTILINE)
ID_PATTERN = re.compile(r"^objective-[a-z0-9][a-z0-9-]{0,63}$")
REQUIRED_FRONTMATTER: tuple[str, ...] = (
    "id", "status", "created", "last_revised", "review_by",
    "owner", "priority", "manual_deps", "theme",
)


def parse_objective(path: Path | str) -> dict[str, Any]:
    """Parse an objective file.

    Returns a dict with keys:
        frontmatter: dict of YAML frontmatter fields
        sections: dict mapping section heading (e.g. '## 1.') to body str
        ledger_rows: list of dicts parsed from ## 11. tracking ledger table
                     each row: {sprint: str, kind: str, content: str,
                               decision: str, reason: str}

    Raises ValueError on missing/malformed frontmatter.
    """
    text = Path(path).read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"missing YAML frontmatter (file must start with '---'): {path}")

    # Find closing --- (must be within first 20 lines per project convention)
    end = -1
    lines = text.split("\n")
    for i, line in enumerate(lines[1:20], start=1):
        if line.strip() == "---":
            end = i
            break
    if end == -1:
        raise ValueError(f"malformed YAML frontmatter (no closing '---' within first 20 lines): {path}")

    frontmatter_raw = "\n".join(lines[1:end])
    try:
        frontmatter = yaml.safe_load(frontmatter_raw) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in frontmatter: {path}: {exc}") from exc

    # PyYAML auto-converts ISO date strings to datetime.date objects.
    # Coerce back to strings so downstream code can treat them uniformly.
    for date_field in ("created", "last_revised", "review_by"):
        if date_field in frontmatter:
            value = frontmatter[date_field]
            if hasattr(value, "isoformat"):
                frontmatter[date_field] = value.isoformat()
            elif value is not None:
                frontmatter[date_field] = str(value)

    body = "\n".join(lines[end + 1 :])

    # Extract sections by heading prefix
    sections: dict[str, str] = {}
    for heading in REQUIRED_SECTIONS + OPTIONAL_SECTIONS:
        # Find heading, then capture content until next ## heading or EOF
        pattern = re.compile(
            rf"^{re.escape(heading)}[^\n]*\n(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(body)
        sections[heading] = match.group(1).strip() if match else ""

    # Parse ## 11. tracking ledger table
    ledger_rows: list[dict[str, str]] = []
    ledger_section = sections.get("## 11.", "")
    if ledger_section:
        for line in ledger_section.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            # Skip header row, separator row, and empty rows
            if "---" in stripped or "Sprint" in stripped and "kind" in stripped:
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) < 5:
                continue
            ledger_rows.append(
                {
                    "sprint": cells[0],
                    "kind": cells[1],
                    "content": cells[2],
                    "decision": cells[3],
                    "reason": cells[4],
                }
            )

    return {"frontmatter": frontmatter, "sections": sections, "ledger_rows": ledger_rows}


def validate_objective(data: dict[str, Any]) -> list[str]:
    """Validate parsed objective data. Returns list of error messages (empty = valid).

    Covers:
    - frontmatter field presence (9 required)
    - status / priority enums
    - id pattern (objective- prefix)
    - manual_deps array structure
    - ledger kind enum (5 values)
    - required section presence (6 hand-written sections)
    - N/A format constraint for section 10 (deferred objective pattern)
    """
    errors: list[str] = []
    frontmatter = data.get("frontmatter", {})

    # Required fields
    for req in REQUIRED_FRONTMATTER:
        if req not in frontmatter:
            errors.append(f"missing required frontmatter field: {req}")

    # ID pattern
    obj_id = frontmatter.get("id", "")
    if obj_id and not ID_PATTERN.match(obj_id):
        errors.append(f"invalid id pattern: {obj_id!r} (must match {ID_PATTERN.pattern})")

    # Status enum
    status = frontmatter.get("status")
    if status not in STATUS_ENUM:
        errors.append(f"invalid status: {status!r} (must be one of {sorted(STATUS_ENUM)})")

    # Priority enum
    priority = frontmatter.get("priority")
    if priority not in PRIORITY_ENUM:
        errors.append(f"invalid priority: {priority!r} (must be one of {sorted(PRIORITY_ENUM)})")

    # Owner constraint
    owner = frontmatter.get("owner")
    if owner != "rdd-planner":
        errors.append(f"invalid owner: {owner!r} (must be 'rdd-planner')")

    # manual_deps must be list
    manual_deps = frontmatter.get("manual_deps")
    if not isinstance(manual_deps, list):
        errors.append(f"manual_deps must be a list, got {type(manual_deps).__name__}")

    # Date format check (ISO YYYY-MM-DD)
    for date_field in ("created", "last_revised", "review_by"):
        val = frontmatter.get(date_field)
        if val and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(val)):
            errors.append(f"{date_field} must be ISO date (YYYY-MM-DD): {val!r}")

    # Ledger kind enum
    for row in data.get("ledger_rows", []):
        kind = row.get("kind", "")
        if kind not in KIND_ENUM:
            errors.append(f"invalid ledger kind: {kind!r} (must be one of {sorted(KIND_ENUM)})")

    # Required sections
    sections = data.get("sections", {})
    for sec in REQUIRED_SECTIONS:
        if not sections.get(sec, "").strip():
            errors.append(f"missing required section: {sec}")

    # N/A format constraint for section 10 (per design D9)
    section_10 = sections.get("## 10.", "")
    # Detect "N/A" usage in section 10
    if re.search(r"^N/A(\s|$)", section_10, re.MULTILINE) and not NA_PATTERN.search(section_10):
        errors.append("section 10 uses 'N/A' but not 'N/A — <reason>' format")

    return errors


def derive_associations(data: dict[str, Any], project_root: Path | None = None) -> dict[str, list[str]]:
    """Derive §7 features / §8 changes associated with this objective.

    Phase 1 implementation: returns empty lists + manual_deps from frontmatter.
    Phase 2 enhancement: grep `.rddf/roadmap/features/*.md` and
    `openspec/changes/*/roadmap-meta.yaml` for `objective_ref: <id>` field
    to populate features/changes lists.

    For now, derives nothing beyond what frontmatter already declares.
    """
    frontmatter = data.get("frontmatter", {})
    manual_deps = frontmatter.get("manual_deps", [])
    # Phase 1 stub: no filesystem scan yet.
    return {
        "features": [],  # Phase 2: scan .rddf/roadmap/features/*.md for objective_ref
        "changes": [],   # Phase 2: scan openspec/changes/*/roadmap-meta.yaml for objective_ref
        "objectives": manual_deps,  # manual_deps are explicit forward declarations
    }


def grace_period_exceeded(data: dict[str, Any], today: date | None = None) -> bool:
    """Return True if review_by < today AND status in (active, deferred).

    Used by rdd-doctor --category objective-lifecycle to emit WARNING.
    """
    today = today or date.today()
    frontmatter = data.get("frontmatter", {})
    review_by_str = frontmatter.get("review_by")
    if not review_by_str:
        return False
    try:
        review_by = date.fromisoformat(review_by_str)
    except (TypeError, ValueError):
        return False
    status = frontmatter.get("status")
    return review_by < today and status in ("active", "deferred")


def is_na_format(content: str) -> bool:
    """Check if content contains a valid N/A — <reason> marker.

    Returns True if at least one line matches the N/A format pattern.
    Returns False for plain 'N/A' (missing reason after em-dash).
    """
    if not content:
        return False
    return bool(NA_PATTERN.search(content))


def next_status_after_grace(current_status: str) -> str | None:
    """Determine next status when grace period is exceeded.

    Returns None if no transition is automatic (planner must manually decide).
    Current rule: grace-exceeded objectives stay in their current status but
    emit WARNING. planner must call revise-objective or archive-objective.
    """
    # No automatic transition — planner decides.
    return None
