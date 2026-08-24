"""Regression: forbid CLI paths from calling submit_issue_via_gh directly.

Per ADR-0027 §3, all L2 gh submission paths MUST go through
``should_auto_submit_gh_submission`` in ``_lib/issue_reporter.py``. Any
``_lib/cli/`` module that calls ``submit_issue_via_gh`` directly is a bypass
of the triple opt-in gate.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_CLI_DIR = Path(__file__).resolve().parent.parent.parent / "_lib" / "cli"

# Pattern: imports submit_issue_via_gh WITHOUT also importing should_auto_submit_gh_submission
_BYPASS_PATTERN = re.compile(
    r"from\s+issue_reporter\s+import[^\n]*submit_issue_via_gh(?!.*should_auto_submit_gh_submission)",
    re.MULTILINE,
)


@pytest.mark.parametrize("cli_file", sorted(_CLI_DIR.glob("*.py")))
def test_no_direct_submit_issue_via_gh_import_in_cli(cli_file: Path) -> None:
    """Every CLI module must import should_auto_submit_gh_submission, NOT submit_issue_via_gh directly."""
    if cli_file.name == "__init__.py":
        pytest.skip("package init")
    text = cli_file.read_text(encoding="utf-8")
    matches = _BYPASS_PATTERN.findall(text)
    assert not matches, (
        f"{cli_file.name} bypasses triple opt-in gate: directly imports submit_issue_via_gh. "
        f"Use should_auto_submit_gh_submission() from issue_reporter instead.\n"
        f"Found: {matches}"
    )