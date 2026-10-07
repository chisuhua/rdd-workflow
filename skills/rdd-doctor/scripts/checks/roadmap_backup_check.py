"""rdd-doctor category: roadmap-backup (per add-rdd-doctor-coverage-completion).

Inspects `.rddf/roadmap/.backup/<timestamp>/` subdirectories:
  - INFO when exactly 1 backup exists (history retention expected)
  - WARNING when ≥2 backups coexist (consolidation suggestion)
  - WARNING when any backup is older than 90 days (cleanup suggestion)
  - WARNING when backup dir name does NOT match `<YYYYMMDD>T<HHMMSS>Z`

Severity: WARNING = action suggested; INFO = informational.
Pure read-only; no .backup/ writes.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity


_BACKUP_PATTERN = re.compile(r"^(\d{8}T\d{6}Z)$")
_NINETY_DAYS_SECONDS = 90 * 24 * 60 * 60


def run(project_root: Path | None = None) -> List[Finding]:
    import os

    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))

    backup_root = project_root / ".rddf" / "roadmap" / ".backup"
    if not backup_root.is_dir():
        return []

    findings: List[Finding] = []
    subdirs = sorted([p for p in backup_root.iterdir() if p.is_dir()])

    for subdir in subdirs:
        m = _BACKUP_PATTERN.match(subdir.name)
        if not m:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="roadmap-backup.malformed-name",
                file=str(subdir),
                line=None,
                snippet=f"malformed backup dir name '{subdir.name}' (not <YYYYMMDD>T<HHMMSS>Z)",
                fix_hint="rename to ISO8601 basic-format timestamp or remove",
            ))
            continue

        try:
            ts = datetime.strptime(subdir.name, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()
        except ValueError:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="roadmap-backup.malformed-name",
                file=str(subdir),
                line=None,
                snippet=f"backup dir name '{subdir.name}' matches pattern but isn't a valid timestamp",
                fix_hint="rename or remove",
            ))
            continue

        if age_seconds > _NINETY_DAYS_SECONDS:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="roadmap-backup.stale-snapshot",
                file=str(subdir),
                line=None,
                snippet=f"stale backup '{subdir.name}' is {int(age_seconds / 86400)} days old (threshold 90)",
                fix_hint="archive to long-term backup or remove",
            ))

    if len(subdirs) >= 2:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="roadmap-backup.multiple-snapshots",
            file=str(backup_root),
            line=None,
            snippet=f"{len(subdirs)} backup directories coexist; consolidate to one canonical snapshot",
            fix_hint="merge into single .rddf/roadmap/ or remove obsolete",
        ))
    elif len(subdirs) == 1:
        findings.append(Finding(
            severity=Severity.INFO,
            category="roadmap-backup.snapshot-exists",
            file=str(backup_root),
            line=None,
            snippet=f"backup dir '{subdirs[0].name}' exists; history retention per roadmap migration",
            fix_hint="no action required",
        ))

    return findings