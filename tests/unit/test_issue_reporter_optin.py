"""Tests for ADR-0027 §3 triple opt-in gate — the single choke point for L2 gh submission."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))

from issue_reporter import should_auto_submit_gh_submission  # type: ignore[import-not-found]


@pytest.fixture(autouse=True)
def _clean_optin_env(monkeypatch):
    """Ensure opt-in env vars are deterministic per test."""
    for k in ("RDDF_REPORT_ENABLED", "RDDF_REPORT_AUTO_SUBMIT", "RDDF_REPORT_SUBMIT_CATEGORIES",
              "CI", "GITHUB_ACTIONS", "JENKINS_URL"):
        monkeypatch.delenv(k, raising=False)
    yield


def test_opt_in_disabled_writes_local_only():
    """Without RDDF_REPORT_ENABLED=yes, must NOT auto-submit — L1 only."""
    assert should_auto_submit_gh_submission("flow-bug") is False


def test_opt_in_enabled_category_not_in_list_rejects_with_false(monkeypatch):
    """RDDF_REPORT_ENABLED=yes + category not in RDDF_REPORT_SUBMIT_CATEGORIES → False."""
    monkeypatch.setenv("RDDF_REPORT_ENABLED", "yes")
    monkeypatch.setenv("RDDF_REPORT_AUTO_SUBMIT", "yes")
    monkeypatch.setenv("RDDF_REPORT_SUBMIT_CATEGORIES", "flow-bug,phase-crash")
    assert should_auto_submit_gh_submission("manual") is False


def test_ci_environment_auto_downgrades(monkeypatch):
    """Even with all env vars set, CI=true must downgrade to L1."""
    monkeypatch.setenv("RDDF_REPORT_ENABLED", "yes")
    monkeypatch.setenv("RDDF_REPORT_AUTO_SUBMIT", "yes")
    monkeypatch.setenv("RDDF_REPORT_SUBMIT_CATEGORIES", "flow-bug,gate-failure,phase-crash")
    monkeypatch.setenv("CI", "true")
    assert should_auto_submit_gh_submission("flow-bug") is False