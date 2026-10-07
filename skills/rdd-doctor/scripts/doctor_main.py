"""Doctor main: aggregator dispatcher with lazy-import check modules.

Per add-rdd-doctor-coverage-completion (2026-10-07):
  - _CHECKERS dict is now a `name -> import_path` string map (was callable).
  - aggregate_findings lazy-resolves the callable on first use via _resolve_check.
  - This eliminates the temp-fixture ModuleNotFoundError (4 check modules
    depend on _lib imports; tests copy rdd-doctor/ to $BATS_TEST_TMPDIR
    without _lib/, breaking eager `from checks import ...`).

Module-load cost: 1 sys.path tweak + 0 imports. Per-category first-call:
  ~1ms importlib overhead. Subsequent calls hit memoized callable.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable, List, Tuple, Union

from doctor_render import Finding, Severity, exit_code_for, render_human, render_json, render_quiet


_PROJECT_ROOT = Path(os.environ.get("RDDF_PROJECT_ROOT", Path.cwd())).resolve()


_CHECKERS: dict[str, Union[str, Callable]] = {
    "state": "checks.state_schema_check.run",
    "plan-tdd": "checks.plan_tdd_check.run",
    "roadmap-meta": "checks.roadmap_meta_check.run",
    "proposal-table": "checks.proposal_table_check.run",
    "proposal-section": "checks.proposal_section_check.run",
    "tasks-checkbox": "checks.tasks_checkbox_check.run",
    "migration-residue": "checks.migration_residue_check.run",
    "orphan-gates": "checks.orphan_gates_check.run",
    "roadmap-refs": "checks.roadmap_refs_check.run",
    "roadmap-feature": "checks.roadmap_feature_check.run",
    "roadmap-md-integrity": "checks.roadmap_md_integrity_check.run",
    "roadmap-phases": "checks.roadmap_phases_check.run",
    "docs-consistency": "checks.docs_consistency_check.run",
    "ai-context-bootstrap": "checks.ai_context_bootstrap_check.run",
    "gitignore": "checks.gitignore_check.run",
    "bypass-audit": "checks.bypass_audit_check.run",
    "improvement-frontmatter-consistency": "checks.improvement_frontmatter_check.run",
    "objective-lifecycle": "checks.objective_lifecycle_check.run",
    "objective-structure": "checks.objective_structure_check.run",
    "arch-audit": "checks.arch_audit_check.run",
}


def _resolve_check(name: str) -> Callable:
    """Lazy-resolve `checks.<module>.run` callable for the named category.

    On first invocation: adds _PROJECT_ROOT to sys.path, imports the module
    via importlib, resolves `.run`, and memoizes back into _CHECKERS.
    Subsequent calls hit the memoized callable (fast path).
    """
    entry = _CHECKERS[name]
    if isinstance(entry, str):
        if str(_PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(_PROJECT_ROOT))
        import importlib
        module_name, _, attr_name = entry.rpartition(".")
        module = importlib.import_module(module_name)
        run_fn = getattr(module, attr_name)
        _CHECKERS[name] = run_fn
        return run_fn
    return entry


def aggregate_findings(category: str | None) -> Tuple[List[Finding], List[str]]:
    """Run all 22 checkers (or filtered subset) and aggregate findings.

    A checker exception is converted to a single CRITICAL finding rather than
    aborting the whole run.
    """
    findings: List[Finding] = []
    categories_checked: List[str] = []

    if category and category not in _CHECKERS:
        return [], []

    selected: dict = (
        {category: _CHECKERS[category]} if category else _CHECKERS
    )

    for name in selected:
        categories_checked.append(name)
        try:
            run_fn = _resolve_check(name)
            cat_findings = run_fn(project_root=_PROJECT_ROOT)
            findings.extend(cat_findings)
        except Exception as e:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category=name,
                file="(checker)",
                line=None,
                snippet=f"checker raised {type(e).__name__}: {e}",
                fix_hint="report bug; this is an internal doctor failure",
            ))

    return findings, categories_checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rdd-doctor")
    parser.add_argument("--json", action="store_true", help="Write .rddf/state/.doctor-report.json")
    parser.add_argument("--category", choices=list(_CHECKERS.keys()), help="Run only this category")
    parser.add_argument("--check", choices=list(_CHECKERS.keys()),
                        help="Alias for --category (e.g. --check orphan-gates)")
    parser.add_argument("--quiet", action="store_true", help="Single-line output, most severe only")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args(argv)

    if args.version:
        print("rdd-doctor 0.1.0")
        return 0

    findings, categories_checked = aggregate_findings(category=args.check or args.category)

    if args.json:
        report_path = Path(".rddf/state/.doctor-report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_json(findings, categories_checked))
        print(f"📋 Report: {report_path}")
    elif args.quiet:
        print(render_quiet(findings))
    else:
        print(render_human(findings, categories_checked))

    return exit_code_for(findings)


if __name__ == "__main__":
    sys.exit(main())