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

from issue_reporter import detect_issue, write_issue_file, submit_issue_via_gh  # type: ignore[import-not-found]


def cmd_report_issue(args: list[str]) -> int:
    """Submit a manual issue report (Agent plane, bypasses classifier)."""
    parser = argparse.ArgumentParser(prog="rddf report-issue")
    parser.add_argument("description", help="One-line description of the issue")
    parser.add_argument(
        "--category", default="manual",
        choices=["flow-bug", "gate-failure", "phase-crash", "manual"],
        help="Issue category (default: manual)",
    )
    parser.add_argument("--phase", default="", help="Originating phase (optional metadata)")
    parser.add_argument(
        "--no-submit", action="store_true",
        help="Write local file only, skip gh submission",
    )
    parsed = parser.parse_args(args)

    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    payload = {
        "description": parsed.description,
        "stack": [],
        "metadata": {"phase": parsed.phase} if parsed.phase else {},
    }
    result = detect_issue(parsed.category, payload)
    file_path = write_issue_file(result, project_root=project_root)
    print(f"✅ wrote {file_path}")

    if not parsed.no_submit:
        gh_repo = os.environ.get("RDDF_REPORT_GH_REPO", "chisuhua/rdd-workflow")
        submit = submit_issue_via_gh(file_path, parsed.category, gh_repo)
        if submit.success:
            print(f"✅ submitted: {submit.submitted_url}")
        else:
            print(f"ℹ️  local-only (gh submit skipped): {submit.error}")
    return 0
