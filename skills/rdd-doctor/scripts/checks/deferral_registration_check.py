"""rdd-doctor category: `deferral-registration`.

A deferral ("本次不做 / 另案立项") closes work legitimately — but only when it
names where the deferred debt lives. Without a registration target the defect
has no debt entry and can be deferred forever (measured: two defects recurred
twice after being closed with「另案」and never got an improvement file).

This category reports every deferral wording in the project's documents that
carries no target:

    另案                      ← reported (no debt entry)
    另案（已登记：fix-foo）    ← OK (the debt is an improvement)
    另案（backlog：主题）      ← OK (the debt is a backlog placeholder)

Scope: **documents only** (``.rddf/improvements/**`` / ``.rddf/reviews/**``).
Source comments are the ``review-debt`` category's business — the two surfaces
must not report the same thing.

Existing noise is registered once in ``.rddf/deferral-exemptions.txt`` (an
auditable ledger, not a silent ignore). An exemption that no longer matches is
reported as「可清理」so the list cannot rot unnoticed.

Severity: WARNING (action: add the registration target, or remove the
exemption entry).
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity  # noqa: E402
from _lib.deferral_registration import (  # noqa: E402
    EXEMPTIONS_FILE,
    load_exemptions,
    scan_project,
    stale_exemptions,
)

_CATEGORY = "deferral-registration"


def run(project_root: str) -> list[Finding]:
    """Return findings for the `deferral-registration` category. Never raises."""
    try:
        exemptions = load_exemptions(project_root)
        findings = []
        for item in scan_project(project_root, exemptions):
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    category=_CATEGORY,
                    file=item.path,
                    line=item.line,
                    snippet=item.excerpt[:60],
                    fix_hint=(
                        f"deferral 「{item.phrase}」 没有登记目标 ⇒ 补"
                        f"「另案（已登记：<slug>）」或「另案（backlog：<topic>）」"
                    ),
                )
            )
        for rel in stale_exemptions(project_root, exemptions):
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    category=_CATEGORY,
                    file=EXEMPTIONS_FILE,
                    line=None,
                    snippet=rel,
                    fix_hint=f"豁免条目已不再命中 —— 可清理：从清单删除 {rel}",
                )
            )
        return findings
    except Exception as exc:  # noqa: BLE001 — a diagnostic must never crash doctor
        return [
            Finding(
                severity=Severity.WARNING,
                category=_CATEGORY,
                file=EXEMPTIONS_FILE,
                line=None,
                snippet=str(exc)[:80],
                fix_hint="deferral-registration 检查失败",
            )
        ]
