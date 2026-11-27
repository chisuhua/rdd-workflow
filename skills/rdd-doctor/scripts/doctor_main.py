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
    "review-debt": "checks.review_debt_check.run",
    "roadmap-backup": "checks.roadmap_backup_check.run",
    "baseline-freshness": "checks.baseline_freshness_check.run",
    "v4-residue": "checks.v4_residue_check.run",
    "layout": "checks.layout_check.run",
    "openspec-quota": "checks.openspec_quota_check.run",
    "deferral-registration": "checks.deferral_registration_check.run",
    "commit-gate": "checks.commit_gate_check.run",
}


# Gate definitions — the category list of each CI gate lives HERE, next to
# _CHECKERS, so the CI workflow (.github/workflows/test.yml) and the local
# gate (./test.sh) call ONE source instead of keeping two copies that drift.
#
# Semantics (identical to the workflow's previous inline loop):
#   * a category whose exit code is >= 2 (CRITICAL) makes the whole gate fail;
#   * a category with only warnings (exit 1) does NOT fail the gate;
#   * the gate runs the categories IN-PROCESS, so a crash of the doctor itself
#     is a non-zero exit instead of "every category returned 1 => green"
#     (the inline loop had that fail-open hole).
#   blocking=False  -> the gate only reports (never fails the build); that is
#                      what the workflow's advisory step always did.
_GATES: dict[str, dict] = {
    "structural": {
        "categories": [
            "state",
            "plan-tdd",
            "roadmap-meta",
            "roadmap-refs",
            "roadmap-feature",
            "roadmap-md-integrity",
            "roadmap-phases",
            "objective-lifecycle",
            "objective-structure",
            "arch-audit",
        ],
        "blocking": True,
    },
    "advisory": {
        "categories": [
            "bypass-audit",
            "migration-residue",
            "review-debt",
            "roadmap-backup",
            "v4-residue",
            "openspec-quota",
            "deferral-registration",
            "commit-gate",
        ],
        "blocking": False,
    },
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


def _run_one_category(name: str) -> tuple[int, List[Finding]]:
    """Run one category, returning (exit_code, findings).

    A checker exception becomes a CRITICAL finding (same as aggregate_findings),
    so a broken checker fails the gate instead of passing it.
    """
    findings: List[Finding] = []
    try:
        run_fn = _resolve_check(name)
        findings = list(run_fn(project_root=_PROJECT_ROOT))
    except Exception as e:
        findings = [Finding(
            severity=Severity.CRITICAL,
            category=name,
            file="(checker)",
            line=None,
            snippet=f"checker raised {type(e).__name__}: {e}",
            fix_hint="report bug; this is an internal doctor failure",
        )]
    return exit_code_for(findings), findings


def run_gate(name: str) -> int:
    """Run a named gate: one line per category + an aggregate exit code.

    Output is deliberately NOT render_quiet (that prints a single "OK" line and
    hides WHICH categories ran) — a gate log has to show every category it
    checked, otherwise a typo in the list is invisible.
    """
    spec = _GATES[name]
    categories: List[str] = list(spec["categories"])
    blocking: bool = bool(spec["blocking"])
    in_github = os.environ.get("GITHUB_ACTIONS") == "true"
    failed: List[str] = []
    warned: List[str] = []

    for cat in categories:
        rc, findings = _run_one_category(cat)
        crit = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        warn = sum(1 for f in findings if f.severity == Severity.WARNING)
        info = sum(1 for f in findings if f.severity == Severity.INFO)
        if rc >= 2:
            failed.append(cat)
            mark = "❌"
        elif rc == 1:
            warned.append(cat)
            mark = "⚠️"
        else:
            mark = "✅"
        print(f"{mark} {cat} (critical={crit} warning={warn} info={info})")
        if in_github:
            if rc >= 2:
                print(f"::error title=rdd-doctor::{cat} CRITICAL ({crit} critical finding(s))")
                for f in findings:
                    if f.severity == Severity.CRITICAL:
                        print(f"::error title=rdd-doctor::{cat} {f.file}:{f.line or '-'} {f.snippet}")
            elif rc == 1:
                print(f"::warning title=rdd-doctor::{cat} advisory ({warn} warning(s))")

    if failed and blocking:
        print(f"❌ rdd-doctor {name} gate: {len(failed)} category failure(s): {', '.join(failed)}")
        return 1
    if failed:
        # Non-blocking gate: report the criticals but never fail the build
        # (the workflow's advisory step has always been advisory).
        print(f"⚠️  rdd-doctor {name} gate (non-blocking): {len(failed)} category with critical findings: {', '.join(failed)}")
        return 0
    print(f"✅ rdd-doctor {name} gate: all {len(categories)} categories pass"
          + (f" ({len(warned)} with warnings)" if warned else ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rdd-doctor")
    parser.add_argument("--json", action="store_true", help="Write .rddf/state/.doctor-report.json")
    parser.add_argument("--category", choices=list(_CHECKERS.keys()), help="Run only this category")
    parser.add_argument("--check", choices=list(_CHECKERS.keys()),
                        help="Alias for --category (e.g. --check v4-residue)")
    parser.add_argument("--quiet", action="store_true", help="Single-line output, most severe only")
    parser.add_argument("--gate", choices=sorted(_GATES.keys()),
                        help="Run a named gate (see _GATES) and aggregate its exit code")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args(argv)

    if args.version:
        print("rdd-doctor 0.1.0")
        return 0

    if args.gate:
        return run_gate(args.gate)

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