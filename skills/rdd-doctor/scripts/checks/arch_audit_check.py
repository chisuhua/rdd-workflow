"""Arch-audit check — surfaces arch-side drift and completeness signals.

Read-only diagnostic for architecture artifacts. Surfaces arch-quality
state on demand via `rddf doctor --category arch-audit`.

Checks (all deterministic, no LLM, no code execution):
  1. Theme-doc inventory (per ADR-0057) — INFO summary (count) +
     WARNING if 0 theme docs found in `docs/architecture/` (signals
     no architecture snapshot has been written yet).
  2. ADR inventory — INFO summary (count, latest ID, superseded count,
     status drift).
  3. `.rddf/state/.arch-handoff.json` sanity — INFO presence, WARNING
     if missing (signals arch-done never ran).

CHANGED 2026-09-30 (per ADR-0057):
  - Replaced gap-analysis structural check with theme-doc existence check
    (gap-analysis artifact type deleted; theme docs are now rdd-arch's
    primary composition artifacts per ADR-0057 §Decision).
  - Removed `_lib.arch.protocol` dependency (deleted with ADR-0046
    superseded). No more lazy-import machinery needed.

Design decisions (mirrors existing doctor checks):
  - Always returns `List[Finding]`; never raises. Checker exceptions
    become a single CRITICAL finding at the aggregate layer (see
    `doctor_main.aggregate_findings`).
  - All findings are categorised `arch-audit` for filtering.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity

_CATEGORY = "arch-audit"


def _check_theme_docs(project_root: Path) -> List[Finding]:
    """Surface theme-doc inventory in docs/architecture/ (per ADR-0057).

    Theme docs (`docs/architecture/*.md`) are rdd-arch's primary composition
    artifacts — they encode current-architecture snapshot + composing ADR
    references. Zero theme docs signals that arch-create + theme-doc sync
    has not produced any artifacts yet (pre-Phase-2 state).

    Skips `*-0000-template.md` placeholder files.
    """
    arch_dir = project_root / "docs" / "architecture"
    if not arch_dir.is_dir():
        return [Finding(
            severity=Severity.WARNING,
            category=_CATEGORY,
            file=str(arch_dir),
            line=None,
            snippet="docs/architecture/ missing (rdd-arch owns theme docs per ADR-0057; create first theme doc to anchor architecture snapshot)",
            fix_hint="create first theme doc (e.g., overview.md or workflow-phases.md) via skill_use('rdd-arch')",
        )]

    theme_files = sorted(
        p for p in arch_dir.glob("*.md")
        if "0000-template" not in p.name
    )

    if not theme_files:
        return [Finding(
            severity=Severity.WARNING,
            category=_CATEGORY,
            file=str(arch_dir),
            line=None,
            snippet="0 theme docs found (rdd-arch owns docs/architecture/*.md per ADR-0057; 0 docs means no architecture snapshot committed)",
            fix_hint="create first theme doc (e.g., overview.md, workflow-phases.md) via skill_use('rdd-arch')",
        )]

    return [Finding(
        severity=Severity.INFO,
        category=_CATEGORY,
        file=str(arch_dir),
        line=None,
        snippet=f"{len(theme_files)} theme docs ({', '.join(p.stem for p in theme_files[:5])}{' …' if len(theme_files) > 5 else ''})",
        fix_hint="no action required; informational summary",
    )]


def _check_adr_inventory(project_root: Path) -> List[Finding]:
    """Surface ADR inventory summary (count, latest ID, status drift)."""
    adr_dir = project_root / "docs" / "adr"
    if not adr_dir.is_dir():
        return [Finding(
            severity=Severity.INFO,
            category=_CATEGORY,
            file=str(adr_dir),
            line=None,
            snippet="docs/adr/ missing (no ADRs to inventory)",
            fix_hint="run skill_use('rdd-arch') Phase 2 to create first ADR",
        )]

    adr_files = sorted(adr_dir.glob("ADR-*.md"))
    adr_files = [p for p in adr_files if "0000-template" not in p.name]

    if not adr_files:
        return [Finding(
            severity=Severity.INFO,
            category=_CATEGORY,
            file=str(adr_dir),
            line=None,
            snippet="0 ADRs found (arch-done gate requires ≥1 per ADR-0048 single-gate)",
            fix_hint="create first ADR via skill_use('rdd-arch') Phase 2",
        )]

    # Extract ADR numbers + status field
    adr_numbers: List[int] = []
    superseded_count = 0
    status_drift: List[str] = []
    for adr_path in adr_files:
        m = re.match(r"ADR-(\d{4})-", adr_path.name)
        if not m:
            continue
        adr_numbers.append(int(m.group(1)))
        text = adr_path.read_text(encoding="utf-8", errors="replace")
        # Allow optional blockquote `>` prefix (common in ADR frontmatter
        # rendered as `> **状态**: ...`).
        status_match = re.search(
            r"(?:^|\n)\s*>?\s*\*\*状态\*\*\s*[:：]\s*(.+)", text
        )
        status_match_en = re.search(
            r"(?:^|\n)\s*>?\s*\*\*Status\*\*\s*[:：]\s*(.+)", text
        )
        status = (status_match or status_match_en)
        if status:
            status_text = status.group(1).strip()
            if "替代" in status_text or "Superseded" in status_text:
                superseded_count += 1
            # Drift signal: status present but ambiguous
            if "待定" in status_text or "Draft" in status_text or "Proposed" in status_text:
                status_drift.append(f"{adr_path.name}: {status_text[:40]}")

    latest = max(adr_numbers) if adr_numbers else 0
    findings: List[Finding] = [
        Finding(
            severity=Severity.INFO,
            category=_CATEGORY,
            file=str(adr_dir),
            line=None,
            snippet=f"{len(adr_files)} ADRs (latest: ADR-{latest:04d}, superseded: {superseded_count})",
            fix_hint="no action required; informational summary",
        )
    ]
    for drift in status_drift:
        findings.append(Finding(
            severity=Severity.WARNING,
            category=_CATEGORY,
            file=str(adr_dir / drift.split(":")[0]),
            line=None,
            snippet=f"status field in non-terminal state ({drift.split(':', 1)[1].strip()})",
            fix_hint="finalize ADR status (Adopted / Superseded / Deprecated) or document why still pending",
        ))
    return findings


def _check_arch_handoff(project_root: Path) -> List[Finding]:
    """Check .rddf/state/.arch-handoff.json presence + validity (per ADR-0016 Layer 2).

    Presence is INFO (no arch-done yet is fine). Schema-shaped payload is
    WARNING if structurally broken; CRITICAL only if the gate had run but
    produced an invalid handoff (rare, surfaces real bug).
    """
    handoff_path = project_root / ".rddf" / "state" / ".arch-handoff.json"
    if not handoff_path.is_file():
        return [Finding(
            severity=Severity.INFO,
            category=_CATEGORY,
            file=str(handoff_path),
            line=None,
            snippet="arch-handoff missing (arch-done gate has not run yet, expected for pre-Phase-1 state)",
            fix_hint="run skill_use('rdd-arch') → completes when arch-done gate passes",
        )]

    try:
        data = json.loads(handoff_path.read_text())
    except json.JSONDecodeError as e:
        return [Finding(
            severity=Severity.CRITICAL,
            category=_CATEGORY,
            file=str(handoff_path),
            line=e.lineno,
            snippet=f"invalid JSON: {e.msg}",
            fix_hint="re-run skill_use('rdd-arch') to regenerate handoff, or restore from archive",
        )]

    version = data.get("version")
    if version not in (1, 2):
        return [Finding(
            severity=Severity.WARNING,
            category=_CATEGORY,
            file=str(handoff_path),
            line=None,
            snippet=f"unknown schema version: {version!r} (expected 1 or 2)",
            fix_hint="re-run skill_use('rdd-arch') or migrate schema; see _lib/schemas/arch_handoff_schema.json",
        )]

    return [Finding(
        severity=Severity.INFO,
        category=_CATEGORY,
        file=str(handoff_path),
        line=None,
        snippet=f"arch-handoff v{version} valid (adr_count={data.get('adr_count', '?')}, arch_complete_at={data.get('arch_complete_at', '?')})",
        fix_hint="no action required; informational summary",
    )]


def run(project_root: Path | None = None) -> List[Finding]:
    """Run arch-audit checks against project_root."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
        os.environ.setdefault("RDDF_PROJECT_ROOT", str(project_root.resolve()))

    findings: List[Finding] = []
    findings.extend(_check_theme_docs(project_root))
    findings.extend(_check_adr_inventory(project_root))
    findings.extend(_check_arch_handoff(project_root))
    return findings