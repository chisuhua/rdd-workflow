"""Arch-audit check — surfaces arch-side drift and completeness signals.

Read-only diagnostic for architecture artifacts. Closes the gap-analysis
auditability question raised in the rdd-arch v2.1.0 review (2026-09-29):
previously arch-quality was only reportable via the inline
`check_gap_analyses_advisory()` in `arch_done_gate.sh` (ephemeral, only
runs at arch-done). This check makes the same signals queryable on demand
via `rddf doctor --category arch-audit`.

Checks (all deterministic, no LLM, no code execution):
  1. Gap-analysis structural_ok (per `_lib.arch.protocol.validate_document`)
     — WARNING on structural drift, INFO on draft / partial / complete.
  2. ADR inventory — INFO summary (count, latest ID, status field).
  3. `.rddf/state/.arch-handoff.json` sanity — INFO presence, WARNING
     if missing (signals arch-done never ran).

Design decisions (mirrors existing doctor checks):
  - Always returns `List[Finding]`; never raises. Checker exceptions
    become a single CRITICAL finding at the aggregate layer (see
    `doctor_main.aggregate_findings`).
  - Uses lazy import for `_lib.arch.protocol` so missing _lib surfaces
    as INFO (graceful degradation) rather than aborting.
  - All findings are categorised `arch-audit` for filtering.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity

_REPO_ROOT = Path(__file__).resolve().parents[4]  # checks/ → repo root

_CATEGORY = "arch-audit"


def _load_arch_protocol():
    """Lazy import to mirror docs_consistency_check._load_docs_consistency().

    Falls back to `skills/_lib/arch/protocol.py` shim for backward compat
    (P1-1b identity-merge). Raises ImportError if neither path resolves —
    caller catches and emits a single INFO finding.

    The `sys.modules[name] = module` line is required: Python's
    `@dataclass` decorator resolves class namespace via
    `sys.modules[cls.__module__].__dict__`, which raises
    `AttributeError: 'NoneType' object has no attribute '__dict__'` if the
    module is loaded via `importlib.util.spec_from_file_location` without
    being registered first.
    """
    candidates = [
        _REPO_ROOT / "_lib" / "arch" / "protocol.py",
        _REPO_ROOT / "skills" / "_lib" / "arch" / "protocol.py",
    ]
    for path in candidates:
        if path.is_file():
            mod_name = "_arch_protocol_loader"
            spec = importlib.util.spec_from_file_location(mod_name, str(path))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = module
                spec.loader.exec_module(module)
                return module
    raise ImportError(
        f"_lib.arch.protocol not found in {candidates}"
    )


def _check_gap_analyses(project_root: Path) -> List[Finding]:
    """Validate gap-analysis documents via _lib.arch.protocol.validate_document."""
    arch_dir = project_root / "docs" / "architecture"
    if not arch_dir.is_dir():
        return [Finding(
            severity=Severity.INFO,
            category=_CATEGORY,
            file=str(arch_dir),
            line=None,
            snippet="docs/architecture/ missing (no gap-analyses to audit)",
            fix_hint="run skill_use('rdd-arch') Phase 3 to create gap analyses",
        )]

    try:
        protocol = _load_arch_protocol()
        analyses = protocol.list_analyses(arch_dir)
    except ImportError as e:
        return [Finding(
            severity=Severity.WARNING,
            category=_CATEGORY,
            file=str(arch_dir),
            line=None,
            snippet=f"_lib.arch.protocol import failed: {e}",
            fix_hint="verify _lib/arch/protocol.py exists (canonical path) or skills/_lib/arch/protocol.py (shim)",
        )]

    if not analyses:
        return [Finding(
            severity=Severity.INFO,
            category=_CATEGORY,
            file=str(arch_dir),
            line=None,
            snippet="0 gap-analyses found (gap enforced by optional docs/architecture/*.md convention, not blocking)",
            fix_hint="optional: generate gap analyses via skill_use('rdd-arch') Phase 3",
        )]

    findings: List[Finding] = []
    for gap_file in analyses:
        report = protocol.validate_document(gap_file)
        if not report.structural_ok:
            findings.append(Finding(
                severity=Severity.WARNING,
                category=_CATEGORY,
                file=str(gap_file),
                line=None,
                snippet=f"structural drift: {'; '.join(report.issues)} (per ADR-0046 §5, structural_ok is HARD)",
                fix_hint="re-generate via skill_use('rdd-arch') Phase 3 or hand-fix the missing section headings",
            ))
            continue

        # structural_ok True; surface status (completeness = advisory)
        label = {
            "draft": "still in skeleton (no curation done)",
            "partial": "partially curated (placeholder text remains)",
            "complete": "fully curated",
        }.get(report.completeness, f"unknown completeness: {report.completeness}")
        findings.append(Finding(
            severity=Severity.INFO,
            category=_CATEGORY,
            file=str(gap_file),
            line=None,
            snippet=f"{report.completeness} — {label}",
            fix_hint="no action required; advisory only",
        ))
    return findings


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
    findings.extend(_check_gap_analyses(project_root))
    findings.extend(_check_adr_inventory(project_root))
    findings.extend(_check_arch_handoff(project_root))
    return findings