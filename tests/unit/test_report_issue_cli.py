"""Tests for rddf report-issue CLI argparse + behavior."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))


def test_exit_code_flag_accepted(monkeypatch):
    """argparse must accept --exit-code (not the legacy --exit)."""
    monkeypatch.setattr(sys, "argv", ["rddf", "report-issue", "--exit-code", "137", "desc"])
    # Direct invocation: must not raise SystemExit(2) from argparse
    from cli.report_issue_cmd import cmd_report_issue  # type: ignore[import-not-found]
    monkeypatch.setenv("RDDF_PROJECT_ROOT", "/tmp/nonexistent-root-for-test")
    # argparse may exit 0 (write local file) or 2 (argparse error) — anything but argparse error
    import argparse
    try:
        result = cmd_report_issue(["--exit-code", "137", "desc"])
        assert result == 0
    except SystemExit as e:
        assert e.code != 2, f"argparse rejected --exit-code: code={e.code}"