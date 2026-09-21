"""Phase 2: Health Diagnosis (read-only, delegates to rddf doctor).

Forks `rddf doctor --json`, parses findings, classifies each into:
    auto-fixable | user-decision | manual-only

Whitelist per AC-6:
    auto-fixable: ai-context-bootstrap with "未部署" or "块已陈旧" / "stale" / "outdated"
    user-decision: ai-context-bootstrap (other), gitignore, docs-consistency
    manual-only: everything else (bypass-audit, orphan-gates, migration-residue, ...)
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


_AUTO_FIXABLE_CATEGORIES = {"ai-context-bootstrap"}
_USER_DECISION_CATEGORIES = {"gitignore", "docs-consistency"}

# Phrases indicating stale/undeployed state within ai-context-bootstrap findings
_AUTO_FIXABLE_PHRASES = ("未部署", "块已陈旧", "stale", "outdated", "missing")


def classify_finding(finding: dict[str, Any]) -> str:
    """Classify a doctor finding into auto-fixable / user-decision / manual-only.

    Args:
        finding: dict with keys 'category', 'severity', 'message', ...

    Returns:
        One of 'auto-fixable', 'user-decision', 'manual-only'.
    """
    category = finding.get("category", "")
    message = finding.get("message", "")

    if category in _AUTO_FIXABLE_CATEGORIES:
        # Even within auto-fixable category, only specific phrases are auto-fixable
        if any(phrase in message.lower() or phrase in message for phrase in _AUTO_FIXABLE_PHRASES):
            return "auto-fixable"
        # Other ai-context-bootstrap findings (e.g., drift beyond stale) require decision
        return "user-decision"

    if category in _USER_DECISION_CATEGORIES:
        return "user-decision"

    return "manual-only"


def diagnose(target_root: Path, doctor_json: dict[str, Any] | None = None) -> dict[str, Any]:
    """Phase 2 entry. Forks rddf doctor --json (or accepts pre-fetched JSON).

    Returns dict with:
        doctor_invoked: bool
        total_findings: int
        auto_fixable / user_decision / manual_only: int counts
        findings: list of {category, severity, message, class}
    """
    if doctor_json is None:
        try:
            r = subprocess.run(
                ["rddf", "doctor", "--json"],
                capture_output=True, text=True, timeout=5, cwd=str(target_root),
            )
        except (subprocess.TimeoutExpired, OSError):
            return {
                "doctor_invoked": False,
                "total_findings": 0,
                "auto_fixable": 0,
                "user_decision": 0,
                "manual_only": 0,
                "findings": [],
            }

        if r.returncode != 0 and not r.stdout.strip():
            return {
                "doctor_invoked": False,
                "total_findings": 0,
                "auto_fixable": 0,
                "user_decision": 0,
                "manual_only": 0,
                "findings": [],
            }
        try:
            doctor_json = json.loads(r.stdout)
        except json.JSONDecodeError:
            doctor_json = {"findings": []}

    findings = doctor_json.get("findings", [])
    classified = []
    counts = {"auto_fixable": 0, "user_decision": 0, "manual_only": 0}

    for f in findings:
        kind = classify_finding(f)
        counts[kind.replace("-", "_")] += 1
        classified.append({**f, "class": kind})

    return {
        "doctor_invoked": True,
        "total_findings": len(findings),
        **counts,
        "findings": classified,
    }


if __name__ == "__main__":
    import json as json_mod
    import sys
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    result = diagnose(target)
    print(json_mod.dumps(result, ensure_ascii=False, indent=2))


__all__ = ["classify_finding", "diagnose"]
