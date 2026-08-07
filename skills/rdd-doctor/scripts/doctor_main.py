"""Doctor main: single Python process importing all 5 checkers + aggregator."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple

from doctor_render import Finding, Severity, exit_code_for, render_human, render_json, render_quiet

from checks import (
    plan_tdd_check,
    proposal_table_check,
    roadmap_meta_check,
    state_schema_check,
    tasks_checkbox_check,
)


_CHECKERS = {
    "state": state_schema_check.run,
    "plan-tdd": plan_tdd_check.run,
    "roadmap-meta": roadmap_meta_check.run,
    "proposal-table": proposal_table_check.run,
    "tasks-checkbox": tasks_checkbox_check.run,
}


def aggregate_findings(category: str | None) -> Tuple[List[Finding], List[str]]:
    """Run all 5 checkers (or filtered subset) and aggregate findings.

    A checker exception is converted to a single CRITICAL finding rather than
    aborting the whole run.
    """
    project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings: List[Finding] = []
    categories_checked: List[str] = []

    if category and category not in _CHECKERS:
        return [], []

    selected: dict = (
        {category: _CHECKERS[category]} if category else _CHECKERS
    )

    for name, fn in selected.items():
        categories_checked.append(name)
        try:
            cat_findings = fn(project_root=project_root)
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
    parser.add_argument("--quiet", action="store_true", help="Single-line output, most severe only")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args(argv)

    if args.version:
        print("rdd-doctor 0.1.0")
        return 0

    findings, categories_checked = aggregate_findings(category=args.category)

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