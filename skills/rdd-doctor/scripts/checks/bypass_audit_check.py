"""bypass_audit_check.py — rdd-doctor check for SKIP_* bypass usage

Per improvement #bypass-audit-mechanism (P2 governance):
- Reads .rddf/state/.bypass-audit.jsonl (append-only audit log)
- Aggregates current-month usage by env_var
- Emits WARNING when threshold exceeded, CRITICAL when 2x threshold
- Thresholds:
  - ARCHIVE_ON_MAIN: 3/month
  - SKIP_RDD_VERIFIER: 5/month
  - SKIP_HUB_CHECK: 5/month
  - SKIP_DESIGN_GATE: 10/month (default)
  - SKIP_ARCH_GATE: 10/month (default)
  - SKIP_DEPS_GATE: 10/month (default)
  - SKIP_AC_GATE: 10/month (default)
  - SKIP_CONTRACT_GATE: 10/month (default)
  - SKIP_PROPOSAL_COVERAGE: 10/month (default)
  - tools/archive_on_main.sh: 3/month (default for ARCHIVE_ON_MAIN)
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List

# Import shared Finding type
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
_PARENT_DIR = str(Path(__file__).resolve().parents[1])
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)
from doctor_render import Finding, Severity  # type: ignore  # noqa: E402

# Per-env_var thresholds (per ADR-0027 + bypass-audit-mechanism design).
# Specific overrides + default fallback.
SPECIFIC_THRESH: dict[str, int] = {
    "ARCHIVE_ON_MAIN": 3,
    "SKIP_RDD_VERIFIER": 5,
    "SKIP_HUB_CHECK": 5,
    "SKIP_DESIGN_GATE": 10,
    "SKIP_ARCH_GATE": 10,
    "SKIP_DEPS_GATE": 10,
    "SKIP_AC_GATE": 10,
    "SKIP_CONTRACT_GATE": 10,
    "SKIP_PROPOSAL_COVERAGE": 10,
}
DEFAULT_THRESH = 10
CRITICAL_MULTIPLIER = 2


def _load_events(audit_file: Path) -> list[dict]:
    """Read all JSONL events, silently skipping malformed lines."""
    if not audit_file.exists():
        return []
    events = []
    for line in audit_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _monthly_counts(events: list[dict]) -> dict[str, int]:
    """Count current-month events by env_var (UTC)."""
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    counts: dict[str, int] = defaultdict(int)
    for e in events:
        ts = e.get("ts", "")
        if ts.startswith(month):
            counts[e.get("env_var", "unknown")] += 1
    return dict(counts)


def run(project_root: Path) -> List[Finding]:
    """Run bypass-audit check. Returns list of Findings."""
    audit_file = project_root / ".rddf" / "state" / ".bypass-audit.jsonl"

    events = _load_events(audit_file)
    if not events:
        return []  # No bypass usage recorded → no findings

    counts = _monthly_counts(events)
    findings: List[Finding] = []

    for env_var, count in counts.items():
        limit = SPECIFIC_THRESH.get(env_var, DEFAULT_THRESH)
        if count <= limit:
            continue

        if count > limit * CRITICAL_MULTIPLIER:
            severity = Severity.CRITICAL
        else:
            severity = Severity.WARNING

        findings.append(
            Finding(
                severity=severity,
                category="bypass-audit",
                file=str(audit_file),
                line=None,
                snippet=f"{env_var}={count} (limit={limit})",
                fix_hint=(
                    "1) 检查每次旁路 reason 是否必要\n"
                    "2) 若多次重复原因，考虑修复根本 bug\n"
                    "3) 若确实是 hotfix/紧急场景，记录在 PR description 中"
                ),
            )
        )

    return findings


if __name__ == "__main__":
    # CLI entry: print findings as human-readable
    project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings = run(project_root)
    if not findings:
        print("ℹ️  bypass-audit: no threshold violations this month")
    else:
        for f in findings:
            print(f"[{f.severity}] {f.category}: {f.snippet}")