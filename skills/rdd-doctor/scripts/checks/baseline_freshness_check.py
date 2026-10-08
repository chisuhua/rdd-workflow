"""rdd-doctor category: baseline-freshness (per follow-up 2026-10-08).

Inspects `tests/KNOWN_FAILURES.txt` to detect two staleness signals:
  - WARNING when the most recent refresh summary comment is >30 days old
  - CRITICAL when the most recent refresh summary comment is >90 days old
  - WARNING when any active entry has a `# reason required` placeholder
    (i.e. added by selective refresh but not yet triaged to a real reason)

Date is parsed from the latest `# ==== YYYY-MM-DD refresh summary ... ===`
comment, NOT from file mtime (which is unreliable: git checkout, clone,
and the script's own atomic-rename pattern can reset mtime).

Pure read-only; never modifies KNOWN_FAILURES.txt.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity


_REFRESH_SUMMARY_RE = re.compile(
    r"# === (\d{4}-\d{2}-\d{2}) refresh summary"
)
_REASON_PLACEHOLDER_RE = re.compile(r"#\s*reason required\b")
_ENTRY_LINE_RE = re.compile(r"^[^#\s].*#")
_WARNING_DAYS = 30
_CRITICAL_DAYS = 90


def _latest_refresh_date(path: Path) -> Optional[datetime]:
    """Return the date of the most recent refresh summary comment.

    Walks the file bottom-up and returns the FIRST (most recent) match.
    Returns None if no refresh summary is present.
    """
    if not path.is_file():
        return None
    last: Optional[datetime] = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _REFRESH_SUMMARY_RE.search(line)
        if m:
            try:
                d = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if last is None or d > last:
                last = d
    return last


def _count_placeholder_reasons(path: Path) -> int:
    if not path.is_file():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not _ENTRY_LINE_RE.match(line):
            continue
        if _REASON_PLACEHOLDER_RE.search(line):
            count += 1
    return count


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))

    baseline = project_root / "tests" / "KNOWN_FAILURES.txt"
    if not baseline.is_file():
        return [Finding(
            severity=Severity.WARNING,
            category="baseline-freshness.missing-file",
            file=str(baseline),
            line=None,
            snippet="KNOWN_FAILURES.txt does not exist; no baseline to compare against",
            fix_hint="run bash tests/scripts/refresh_known_failures.sh to bootstrap",
        )]

    findings: List[Finding] = []

    last_refresh = _latest_refresh_date(baseline)
    if last_refresh is None:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="baseline-freshness.no-refresh-summary",
            file=str(baseline),
            line=None,
            snippet="no '# === YYYY-MM-DD refresh summary ... ===' comment found",
            fix_hint="run bash tests/scripts/refresh_known_failures.sh to add a summary",
        ))
    else:
        age_days = (datetime.now(timezone.utc) - last_refresh).days
        if age_days > _CRITICAL_DAYS:
            sev = Severity.CRITICAL
        elif age_days > _WARNING_DAYS:
            sev = Severity.WARNING
        else:
            sev = None
        if sev is not None:
            findings.append(Finding(
                severity=sev,
                category=f"baseline-freshness.stale-refresh",
                file=str(baseline),
                line=None,
                snippet=f"last refresh was {age_days} days ago ({last_refresh.date().isoformat()})",
                fix_hint=(
                    "run bash tests/scripts/refresh_known_failures.sh "
                    "(use --dry-run first to preview the diff)"
                ),
            ))

    placeholders = _count_placeholder_reasons(baseline)
    if placeholders > 0:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="baseline-freshness.placeholder-reasons",
            file=str(baseline),
            line=None,
            snippet=f"{placeholders} entries still have '# reason required' placeholder",
            fix_hint=(
                "triage each placeholder: replace with a real reason (issue link, "
                "ADR ref, or 'tracked in <proposal>.md')"
            ),
        ))

    if not findings:
        findings.append(Finding(
            severity=Severity.INFO,
            category="baseline-freshness.healthy",
            file=str(baseline),
            line=None,
            snippet=(
                f"baseline fresh (last refresh {last_refresh.date().isoformat() if last_refresh else 'n/a'}); "
                f"no placeholder reasons"
            ),
            fix_hint="no action required",
        ))

    return findings
