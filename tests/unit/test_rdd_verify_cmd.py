"""Tests for rddf rdd-verify CLI subcommand.

Per ADR-0034 §4.1: CLI backend for 5th phase batch verifier.
"""
import os
import subprocess as sp
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Ensure cli package is importable when running directly
from skills._lib.cli import _ROUTES, route  # noqa: E402


def test_rdd_verify_registered():
    """Verify rdd-verify is registered in _ROUTES dict."""
    assert "rdd-verify" in _ROUTES
    assert _ROUTES["rdd-verify"] == "skills._lib.cli.rdd_verify_cmd:cmd_rdd_verify"


def test_help_flag():
    """Verify --help shows expected flags."""
    result = sp.run(
        ["python3", "_lib/cli/rdd_verify_cmd.py", "--help"],
        capture_output=True, text=True
    )
    assert "--dry-run" in result.stdout
    assert "--max-changes" in result.stdout
    assert "--loop" in result.stdout


def test_dry_run_with_empty_queue(tmp_path, monkeypatch):
    """Dry-run with empty iteration.json exits 0."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / ".rddf" / "state" / "iteration.json").write_text('{"changes": []}')

    from skills._lib.cli.rdd_verify_cmd import cmd_rdd_verify
    exit_code = cmd_rdd_verify(["--dry-run"])
    assert exit_code == 0


def test_skip_returns_exit_2(tmp_path, monkeypatch):
    """SKIP_RDD_VERIFIER=yes returns exit 2."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / ".rddf" / "state" / "iteration.json").write_text(
        '{"changes": [{"name": "x", "status": "ship-done"}]}'
    )

    from skills._lib.cli.rdd_verify_cmd import cmd_rdd_verify
    old = os.environ.get("SKIP_RDD_VERIFIER")
    os.environ["SKIP_RDD_VERIFIER"] = "yes"
    try:
        exit_code = cmd_rdd_verify([])
        assert exit_code == 2
    finally:
        if old is None:
            os.environ.pop("SKIP_RDD_VERIFIER", None)
        else:
            os.environ["SKIP_RDD_VERIFIER"] = old


def test_dry_run_with_ship_done_queue(tmp_path, monkeypatch, capsys):
    """Dry-run prints ship-done changes without modifying state."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / ".rddf" / "state" / "iteration.json").write_text(
        '{"changes": [{"name": "alpha", "status": "ship-done"}, '
        '{"name": "beta", "status": "planned"}]}'
    )

    from skills._lib.cli.rdd_verify_cmd import cmd_rdd_verify
    exit_code = cmd_rdd_verify(["--dry-run"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "alpha" in captured.out
    assert "beta" not in captured.out


def test_max_changes_limit(tmp_path, monkeypatch, capsys):
    """RDDF_VERIFIER_MAX_CHANGES / --max-changes limits scan."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    changes = ",".join([
        f'{{"name": "c{i}", "status": "ship-done"}}' for i in range(5)
    ])
    (tmp_path / ".rddf" / "state" / "iteration.json").write_text(
        f'{{"changes": [{changes}]}}'
    )

    from skills._lib.cli.rdd_verify_cmd import cmd_rdd_verify
    exit_code = cmd_rdd_verify(["--dry-run", "--max-changes", "2"])
    captured = capsys.readouterr()
    assert exit_code == 0
    # Only 2 changes should appear in dry-run output
    assert "c0" in captured.out
    assert "c1" in captured.out
    assert "c4" not in captured.out


def test_corrupt_iteration_json_returns_zero(tmp_path, monkeypatch):
    """Defensive: corrupt iteration.json treated as empty queue."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    (tmp_path / ".rddf" / "state" / "iteration.json").write_text("{invalid")

    from skills._lib.cli.rdd_verify_cmd import cmd_rdd_verify
    exit_code = cmd_rdd_verify(["--dry-run"])
    assert exit_code == 0