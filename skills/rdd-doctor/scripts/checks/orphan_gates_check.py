"""Orphan-gates check — detect gate functions never wired into their gate chain.

fix-orphan-hub-gates-wiring (Oracle 2026-08-18): check_hub_pending() and
check_cross_repo_approvals() in design_done_gate.py had zero production
callers. This checker extracts top-level public functions from the gate
module and verifies each is referenced by skills/guide-design/SKILL.md
(the design-done gate chain). Any unreferenced function is CRITICAL —
it means the gate silently stopped enforcing.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity

_GATE_MODULE = Path("skills/guide-design/scripts/design_done_gate.py")
_GATE_CHAIN = Path("skills/guide-design/SKILL.md")

_DEF_RE = re.compile(r"^def ([a-z][a-zA-Z0-9_]*)\(", re.MULTILINE)


def _public_functions(module_path: Path) -> List[str]:
    return _DEF_RE.findall(module_path.read_text())


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))

    module = project_root / _GATE_MODULE
    chain = project_root / _GATE_CHAIN
    if not module.is_file() or not chain.is_file():
        return []

    chain_text = chain.read_text()
    findings: List[Finding] = []
    for func in _public_functions(module):
        if func == "main":  # CLI dispatcher, not a gate
            continue
        if func not in chain_text:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="orphan-gates",
                file=str(module),
                line=None,
                snippet=f"orphan gate function: {func}() is not referenced by {_GATE_CHAIN}",
                fix_hint="wire it into check_design_done_gate() or remove it; an uncalled gate is a false promise",
            ))
    return findings
