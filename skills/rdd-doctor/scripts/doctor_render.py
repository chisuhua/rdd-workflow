"""Aggregate findings, compute exit codes, render human or JSON output."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True)
class Finding:
    severity: Severity
    category: str
    file: str
    line: int | None
    snippet: str
    fix_hint: str


def exit_code_for(findings: Iterable[Finding], checker_exception: bool = False) -> int:
    """Map findings to exit code.

    0: all OK
    1: only INFO and/or WARNING
    2: at least one CRITICAL
    3: checker raised internal exception
    """
    if checker_exception:
        return 3
    findings = list(findings)
    if not findings:
        return 0
    severities = {f.severity for f in findings}
    if Severity.CRITICAL in severities:
        return 2
    return 1


def _group_by_severity(findings: list[Finding]) -> dict[Severity, list[Finding]]:
    by_sev: dict[Severity, list[Finding]] = {s: [] for s in Severity}
    for f in findings:
        by_sev[f.severity].append(f)
    return by_sev


def render_human(findings: list[Finding], categories_checked: list[str]) -> str:
    """Human-readable grouped report."""
    parts: list[str] = []
    parts.append(f"🩺 RDD Doctor Report — {datetime.now(timezone.utc).isoformat()}")
    parts.append("")

    if not findings:
        parts.append("✅ All 5 categories OK")
        return "\n".join(parts)

    icons = {Severity.CRITICAL: "❌", Severity.WARNING: "⚠️ ", Severity.INFO: "ℹ️ "}
    by_sev = _group_by_severity(findings)
    for sev in (Severity.CRITICAL, Severity.WARNING, Severity.INFO):
        items = by_sev[sev]
        if not items:
            continue
        parts.append(f"=== {sev.value} ({len(items)}) ===")
        for f in items:
            line_part = f"Line {f.line}: " if f.line is not None else ""
            parts.append(f"  {icons[sev]} [{f.category}] {f.file}")
            parts.append(f"     {line_part}{f.snippet}")
            parts.append(f"     Fix: {f.fix_hint}")
        parts.append("")

    counts = {s.value: len(by_sev[s]) for s in Severity}
    parts.append(
        f"Summary: {counts[Severity.CRITICAL.value]} CRITICAL · "
        f"{counts[Severity.WARNING.value]} WARNING · "
        f"{counts[Severity.INFO.value]} INFO"
    )
    return "\n".join(parts)


def render_quiet(findings: list[Finding]) -> str:
    """At most one line: the most severe finding summary."""
    if not findings:
        return "✅ All 5 categories OK"
    by_sev = _group_by_severity(findings)
    for sev in (Severity.CRITICAL, Severity.WARNING, Severity.INFO):
        if by_sev[sev]:
            return f"{sev.value}: {len(by_sev[sev])} ({by_sev[sev][0].category})"
    return "✅ All 5 categories OK"


def render_json(findings: list[Finding], categories_checked: list[str]) -> str:
    """JSON payload.

    Schema: {timestamp, categories_checked, findings[{severity,category,file,line,snippet,fix_hint}], summary{critical,warning,info}}
    """
    by_sev = _group_by_severity(findings)
    counts = {s: len(by_sev[s]) for s in Severity}
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "categories_checked": categories_checked,
        "findings": [asdict(f) | {"severity": f.severity.value} for f in findings],
        "summary": {s.value.lower(): counts[s] for s in Severity},
    }
    return json.dumps(payload, indent=2)