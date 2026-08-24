"""``rddf report-issue`` subcommand handler.

Manual issue submission for the Agent plane of ADR-0027. Bypasses the
three-way classifier — the user has already done the classification by
choosing the category explicitly. Default category is ``manual``.

Usage::

    python3 -m skills._lib.cli report-issue "doc typo on line 42"
    python3 -m skills._lib.cli report-issue --category flow-bug --phase guide-plan "schema drift"
"""
from __future__ import annotations

import argparse
import os
import sys

# Package-safe import: add _lib/ to sys.path so bare `from issue_reporter`
# works whether the CLI is run from the source repo, a global install,
# or a third-party project (matches _lib/post_flow_analysis.py pattern).
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from issue_reporter import detect_issue, write_issue_file, submit_issue_via_gh, should_auto_submit_gh_submission, is_ci_environment  # type: ignore[import-not-found]


def cmd_report_issue(args: list[str]) -> int:
    """Submit a manual issue report (Agent plane, bypasses classifier).

    By default, **never auto-submits to GitHub** (--no-submit is the default;
    pass --submit to opt in). Phase-exit hooks in SKILL.md rely on this
    default to avoid accidental L2 submission when AI agents invoke this
    command.
    """
    parser = argparse.ArgumentParser(prog="rddf report-issue")
    parser.add_argument("description", help="One-line description of the issue")
    parser.add_argument(
        "--category", default="manual",
        choices=["flow-bug", "gate-failure", "phase-crash", "manual"],
        help="Issue category (default: manual)",
    )
    parser.add_argument("--phase", default="", help="Originating phase (optional metadata)")
    parser.add_argument(
        "--exit-code", type=int, default=0,
        help="Exit code of the originating phase (metadata only, default 0)",
    )
    parser.add_argument(
        "--no-submit", action="store_true", default=True,
        help="[DEFAULT] Write local file only, skip gh submission",
    )
    parser.add_argument(
        "--submit", dest="no_submit", action="store_false",
        help="Opt in to gh submission (overrides --no-submit default). "
             "Honors triple opt-in gate (RDDF_REPORT_ENABLED + AUTO_SUBMIT + category).",
    )
    parsed = parser.parse_args(args)

    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    payload = {
        "description": parsed.description,
        "stack": [],
        "metadata": {
            "phase": parsed.phase,
            "exit_code": parsed.exit_code,
        } if parsed.phase or parsed.exit_code else {},
    }
    result = detect_issue(parsed.category, payload)
    file_path = write_issue_file(result, project_root=project_root)
    print(f"✅ wrote {file_path}")

    if not parsed.no_submit:
        if is_ci_environment():
            print("ℹ️  local-only (CI auto-downgrade, --submit ignored)")
            return 0
        if not should_auto_submit_gh_submission(parsed.category):
            print("❌ gh submit rejected: triple opt-in not satisfied "
                  "(need RDDF_REPORT_ENABLED=yes AND RDDF_REPORT_AUTO_SUBMIT=yes "
                  "AND category ∈ RDDF_REPORT_SUBMIT_CATEGORIES AND NOT CI).")
            return 2
        gh_repo = os.environ.get("RDDF_REPORT_GH_REPO", "chisuhua/rdd-workflow")
        submit = submit_issue_via_gh(file_path, parsed.category, gh_repo)
        if submit.success:
            print(f"✅ submitted: {submit.submitted_url}")
        else:
            print(f"ℹ️  local-only (gh submit skipped): {submit.error}")
    return 0
