"""Unit tests for ``skills._lib.cli.version_cmd``."""
from __future__ import annotations

import json

import pytest

from skills._lib.cli import version_cmd


@pytest.fixture
def fake_package_json(tmp_path, monkeypatch):
    """Create a fake package.json with a known version."""
    pkg = tmp_path / "package.json"
    pkg.write_text(json.dumps({"version": "2.0.7", "name": "spec-workflow"}))
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    return tmp_path


def test_cmd_version_prints_banner(fake_package_json, capsys):
    """cmd_version prints 'rddf v<version> — spec-workflow CLI' to stdout."""
    rc = version_cmd.cmd_version([])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "rddf v2.0.7 — spec-workflow CLI\n"


def test_cmd_version_exits_zero(fake_package_json):
    """cmd_version returns exit code 0 on success."""
    rc = version_cmd.cmd_version([])
    assert rc == 0


def test_cmd_version_missing_package_json(tmp_path, monkeypatch, capsys):
    """When package.json is missing, cmd_version prints a friendly error and exits 1."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = version_cmd.cmd_version([])
    captured = capsys.readouterr()
    assert rc == 1
    assert "package.json" in captured.err


def test_cmd_version_missing_version_field(tmp_path, monkeypatch, capsys):
    """When package.json exists but has no 'version' field, fall back to '0.0.0'."""
    pkg = tmp_path / "package.json"
    pkg.write_text(json.dumps({"name": "spec-workflow"}))
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = version_cmd.cmd_version([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "rddf v0.0.0" in captured.out