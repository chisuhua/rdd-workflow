"""Docs-consistency check — 6 drift categories between docs and code.

This is a thin adapter from `_lib/docs_consistency` (the canonical
implementation) to the rdd-doctor check interface (returns Finding list).

Source of truth: `_lib/docs_consistency.run_all()`
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity

_REPO_ROOT = Path(__file__).resolve().parents[4]  # _lib/checks/ → repo root


def _load_docs_consistency():
    """Lazy import to avoid sys.path issues."""
    import importlib.util
    import sys

    candidates = [
        _REPO_ROOT / "_lib" / "docs_consistency.py",
        _REPO_ROOT / "skills" / "_lib" / "docs_consistency.py",
    ]
    for path in candidates:
        if path.is_file():
            spec = importlib.util.spec_from_file_location(
                "docs_consistency", str(path)
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
    raise ImportError(
        f"docs_consistency module not found in {candidates}"
    )


_SEVERITY_MAP = {
    "CRITICAL": Severity.CRITICAL,
    "WARNING": Severity.WARNING,
    "INFO": Severity.INFO,
}


def run(project_root: Path | None = None) -> List[Finding]:
    """Run all 6 docs-consistency checks. Returns rdd-doctor Finding list."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))

    dc = _load_docs_consistency()
    issues = dc.run_all()

    findings: List[Finding] = []
    for issue in issues:
        severity = _SEVERITY_MAP.get(issue["severity"], Severity.WARNING)
        findings.append(Finding(
            severity=severity,
            category="docs-consistency",
            file="(repo-wide)",
            line=None,
            snippet=f"[{issue['name']}] {issue['detail']}",
            fix_hint=issue.get("fix_command", "manual fix"),
        ))

    return findings
