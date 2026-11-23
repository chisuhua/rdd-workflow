"""Unit tests for `rddf openspec quota` (`_lib/cli/openspec_cmd.py`).

Covers AC-1 (unconfigured ⇒ exit 0 + `unlimited` token), AC-2 (exceeded ⇒
exit 1 + `--json.active`), AC-3 (fixed `--json` contract, incl. the error
shape), AC-8 (`--limit` boundaries) and AC-9 (second-level `--help`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from _lib.cli.openspec_cmd import cmd_openspec  # noqa: E402


def _write_yaml(project_root: Path, text: str) -> None:
    (project_root / ".rddf").mkdir(exist_ok=True)
    (project_root / ".rddf" / "project.yaml").write_text(text, encoding="utf-8")


def _make_changes(project_root: Path, names: list[str], *, archive: bool = False) -> None:
    changes = project_root / "openspec" / "changes"
    changes.mkdir(parents=True, exist_ok=True)
    if archive:
        (changes / "archive").mkdir(exist_ok=True)
    for name in names:
        (changes / name).mkdir()


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# AC-1 — unconfigured
# ---------------------------------------------------------------------------

def test_unconfigured_is_ok_and_says_unlimited(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _make_changes(project, ["a", "b"], archive=True)
    assert cmd_openspec(["quota"]) == 0
    out = capsys.readouterr().out
    assert "unlimited" in out
    assert "2 active" in out


def test_unconfigured_json(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cmd_openspec(["quota", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"active": 0, "limit": None, "ok": True}


# ---------------------------------------------------------------------------
# AC-2 — exceeded
# ---------------------------------------------------------------------------

def test_exceeded_exits_1(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_yaml(project, "openspec:\n  proposed_limit: 3\n")
    _make_changes(project, ["a", "b", "c", "d"], archive=True)
    assert cmd_openspec(["quota"]) == 1
    out = capsys.readouterr().out
    assert "4 active" in out and "limit 3" in out


def test_exceeded_json_counts_archive_out(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_yaml(project, "openspec:\n  proposed_limit: 3\n")
    _make_changes(project, ["a", "b", "c", "d"], archive=True)
    assert cmd_openspec(["quota", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"active": 4, "limit": 3, "ok": False}


def test_within_limit_exits_0(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_yaml(project, "openspec:\n  proposed_limit: 3\n")
    _make_changes(project, ["a"], archive=True)
    assert cmd_openspec(["quota", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"active": 1, "limit": 3, "ok": True}


# ---------------------------------------------------------------------------
# AC-3 — fixed JSON contract on configuration errors
# ---------------------------------------------------------------------------

def test_config_error_json_shape(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_yaml(project, 'openspec:\n  proposed_limit: "3"\n')
    assert cmd_openspec(["quota", "--json"]) == 2
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["error"]
    assert payload["active"] is None
    assert payload["limit"] is None
    assert payload["ok"] is False


def test_config_error_text_goes_to_stderr(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_yaml(project, "proposed_limit: 3\n")
    assert cmd_openspec(["quota"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "proposed_limit" in captured.err


# ---------------------------------------------------------------------------
# AC-8 — `--limit` boundaries
# ---------------------------------------------------------------------------

def test_limit_zero_means_unlimited(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _make_changes(project, ["a", "b"])
    assert cmd_openspec(["quota", "--limit", "0", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"active": 2, "limit": None, "ok": True}


def test_limit_overrides_config(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_yaml(project, "openspec:\n  proposed_limit: 1\n")
    _make_changes(project, ["a", "b"])
    assert cmd_openspec(["quota", "--limit", "5", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"active": 2, "limit": 5, "ok": True}


@pytest.mark.parametrize("args", [["--limit", "-1"], ["--limit", "abc"], ["--limit"]],
                         ids=["negative", "non-int", "missing-value"])
def test_limit_usage_errors(project: Path, capsys: pytest.CaptureFixture[str], args: list[str]) -> None:
    assert cmd_openspec(["quota", *args]) == 2
    assert capsys.readouterr().err


# ---------------------------------------------------------------------------
# AC-9 — help
# ---------------------------------------------------------------------------

def test_quota_help_exits_0_and_lists_flags(capsys: pytest.CaptureFixture[str]) -> None:
    assert cmd_openspec(["quota", "--help"]) == 0
    out = capsys.readouterr().out
    assert "--json" in out
    assert "--limit" in out
    assert "unlimited" in out


def test_top_help_mentions_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    assert cmd_openspec(["--help"]) == 0
    assert "quota" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# unknown input
# ---------------------------------------------------------------------------

def test_unknown_subaction_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert cmd_openspec(["bogus"]) == 2
    assert "bogus" in capsys.readouterr().err


def test_unknown_flag_exits_2(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cmd_openspec(["quota", "--bogus"]) == 2
    assert capsys.readouterr().err
