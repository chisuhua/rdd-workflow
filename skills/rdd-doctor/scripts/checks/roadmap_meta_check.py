"""Cat 3 — Validate openspec/changes/*/roadmap-meta.yaml field completeness and types.

Critical for catching the S4 root cause: when manual_deps or manual_blocks is
a string instead of a list, the deps stage silently skips the change. Doctor
flags this as CRITICAL with a 'silently ignore' hint.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List

from doctor_render import Finding, Severity


_REQUIRED_FIELDS = ["phase", "category", "change_type", "priority"]
_ARRAY_FIELDS = ["manual_deps", "manual_blocks"]


def _parse_yaml_simple(path: Path) -> dict[str, Any]:
    """Parse the 6 fields roadmap-meta uses, no PyYAML dependency.

    roadmap-meta.yaml in this project has a tiny fixed shape. A full YAML
    parser is overkill; this handles the documented fields and silently
    ignores anything else.
    """
    text = path.read_text()
    out: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            out[key] = [
                v.strip().strip('"').strip("'")
                for v in inner.split(",")
                if v.strip()
            ] if inner else []
        elif val == "" or val.lower() in ("null", "~"):
            out[key] = None
        else:
            out[key] = val
    return out


def run(project_root: Path | None = None) -> List[Finding]:
    """Run cat-3 against project_root."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    changes_root = project_root / "openspec" / "changes"
    if not changes_root.is_dir():
        return []

    findings: List[Finding] = []
    for change_dir in sorted(changes_root.iterdir()):
        if not change_dir.is_dir() or change_dir.name == "archive":
            continue
        meta = change_dir / "roadmap-meta.yaml"
        if not meta.is_file():
            continue

        try:
            data = _parse_yaml_simple(meta)
        except Exception as e:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="roadmap-meta",
                file=str(meta),
                line=None,
                snippet=f"YAML parse error: {e}",
                fix_hint="re-run propose or manually fix YAML syntax",
            ))
            continue

        for field in _REQUIRED_FIELDS:
            if field not in data or data[field] in (None, ""):
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category="roadmap-meta",
                    file=str(meta),
                    line=None,
                    snippet=f"missing required field '{field}'",
                    fix_hint="re-run propose to regenerate roadmap-meta.yaml",
                ))

        for field in _ARRAY_FIELDS:
            v = data.get(field)
            if v is not None and not isinstance(v, list):
                findings.append(Finding(
                    severity=Severity.CRITICAL,
                    category="roadmap-meta",
                    file=str(meta),
                    line=None,
                    snippet=f"field '{field}' should be array, found {type(v).__name__}",
                    fix_hint=(
                        f"convert '{field}' to YAML list form (e.g. `[{v}]` → "
                        f"`[item1, item2]`); deps-driven execution mode will "
                        f"silently ignore this change otherwise"
                    ),
                ))

    return findings