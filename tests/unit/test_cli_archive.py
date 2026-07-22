"""Unit tests for ``skills._lib.cli.archive_cmd``."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from skills._lib.cli import archive_cmd


def test_cmd_archive_without_name_exits_nonzero(capsys):
    """cmd_archive with no name prints usage and exits non-zero."""
    rc = archive_cmd.cmd_archive([])
    captured = capsys.readouterr()
    assert rc != 0
    assert "用法" in captured.out or "usage" in captured.out.lower()


def test_cmd_archive_help_flag_returns_zero(capsys):
    """cmd_archive --help prints usage and returns 0 without invoking archive.sh."""
    rc = archive_cmd.cmd_archive(["--help"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "usage" in captured.out.lower() or "用法" in captured.out


def test_cmd_archive_invokes_archive_sh(tmp_path, monkeypatch, capsys):
    """cmd_archive <name> subprocesses to skills/_lib/archive.sh and reports success."""
    # Build a fake archive.sh at the expected location
    fake_archive_dir = tmp_path / "skills" / "_lib"
    fake_archive_dir.mkdir(parents=True)
    fake_archive = fake_archive_dir / "archive.sh"
    fake_archive.write_text(
        '#!/usr/bin/env bash\n'
        'archive_change() { echo "fake-archive called with $1"; exit 0; }\n'
    )
    fake_archive.chmod(0o755)
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))

    # Monkeypatch _ARCHIVE_SH so _resolve_archive_sh returns our fake
    monkeypatch.setattr(archive_cmd, "_ARCHIVE_SH", str(fake_archive))

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["bash"], returncode=0, stdout="fake-archive called with my-change\n", stderr=""
        )
        rc = archive_cmd.cmd_archive(["my-change"])

    assert rc == 0
    assert mock_run.called
    # Verify the subprocess call includes the change name
    call_args_str = str(mock_run.call_args)
    assert "my-change" in call_args_str
    captured = capsys.readouterr()
    assert "归档完成" in captured.out or "completed" in captured.out.lower()


def test_cmd_archive_missing_archive_sh(tmp_path, monkeypatch, capsys):
    """When archive.sh is not found, cmd_archive prints a clear error and exits 1."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    # Monkeypatch _ARCHIVE_SH to point at a nonexistent file
    monkeypatch.setattr(archive_cmd, "_ARCHIVE_SH", str(tmp_path / "skills" / "_lib" / "nonexistent.sh"))
    rc = archive_cmd.cmd_archive(["my-change"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "archive.sh" in captured.err or "找不到" in captured.err