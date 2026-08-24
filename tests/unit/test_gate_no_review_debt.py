"""Regression: review_debt_recorded must NOT be in _DEFAULT_CHECKS.

Fix-adr-0027-review-debt-recorded-gate removed the broken gate
(ran after commit so diff was always empty). The new helper in
_lib/review_debt_checker.py handles this in Phase 2.5.
"""
from __future__ import annotations

import pytest


def test_review_debt_recorded_removed_from_default_checks() -> None:
    from skills._lib.gate import _DEFAULT_CHECKS
    ship_checks = _DEFAULT_CHECKS.get("ship_done", [])
    names = [c.name for c in ship_checks]
    assert "review_debt_recorded" not in names, (
        "review_debt_recorded was removed; see _lib/review_debt_checker.py"
    )