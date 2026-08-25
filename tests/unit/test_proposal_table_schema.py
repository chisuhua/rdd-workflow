"""Regression: every linked row in proposal-approved.md has 4 columns.

Fix-adr-0027-skill-count-and-table-schema: rdd-doctor's
proposal_table_check.py enforces 4 columns for proposal-approved.md
(提案 | 优先级 | 完成时间 | 状态). Previously, 9 rows in lines 108-116
were 3 columns, generating 16 WARNINGs (1 header + some data rows).

This test locks the 4-column invariant.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
ROW_PATTERN = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|")


def _count_columns(line: str) -> int:
    return line.count("|") - 1


def test_proposal_approved_data_rows_have_four_columns() -> None:
    """Every linked data row in proposal-approved.md must have 4 columns."""
    path = REPO_ROOT / "proposal-approved.md"
    if not path.is_file():
        pytest.skip("proposal-approved.md not found")
    text = path.read_text()
    in_data = False
    offenders = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith("|------") or stripped.startswith("| ---"):
            in_data = True
            continue
        if not in_data or not stripped.startswith("|"):
            continue
        if not ROW_PATTERN.match(stripped):
            continue
        cols = _count_columns(stripped)
        if cols != 4:
            offenders.append(f"  line {line_no}: {cols} columns: {stripped[:80]}")
    assert not offenders, (
        "proposal-approved.md has non-4-column linked rows:\n" + "\n".join(offenders)
    )


def test_proposal_approved_status_column_populated() -> None:
    """The 4th column (status) must be non-empty for every linked row."""
    path = REPO_ROOT / "proposal-approved.md"
    if not path.is_file():
        pytest.skip("proposal-approved.md not found")
    text = path.read_text()
    in_data = False
    empty_status = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith("|------") or stripped.startswith("| ---"):
            in_data = True
            continue
        if not in_data or not stripped.startswith("|"):
            continue
        if not ROW_PATTERN.match(stripped):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 4 or not cells[3]:
            empty_status.append(f"  line {line_no}: {stripped[:80]}")
    assert not empty_status, (
        "proposal-approved.md rows with empty status column:\n"
        + "\n".join(empty_status)
    )