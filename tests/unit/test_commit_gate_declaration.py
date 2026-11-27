"""commit-gate 声明的**推导规则**与**非平凡判据**（design D-2 / D-3）。

判据真源：`openspec/changes/add-commit-gate-declaration-bootstrap/proposal.md` 的 AC1/AC2/AC6。
⚠ 生成器 / doctor / `--help` 文案共用 `_lib/commit_gate_declaration.py`（禁第二份枚举）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _lib.commit_gate_declaration import (  # noqa: E402
    SHELL_COMMANDS,
    derive_verify_commands,
    is_shell_declaration,
    shell_commands_display,
)


def _touch(root: Path, name: str, content: str = "") -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ── 推导（候选表 + 仓内证据；只取第一个命中）───────────────────────────────


def test_test_sh_wins(tmp_path):
    _touch(tmp_path, "test.sh", "#!/bin/sh\n")
    _touch(tmp_path, "go.mod", "module x\n")
    assert derive_verify_commands(tmp_path) == [["./test.sh"]]


def test_package_json_needs_test_script(tmp_path):
    _touch(tmp_path, "package.json", json.dumps({"scripts": {"build": "x"}}))
    assert derive_verify_commands(tmp_path) is None
    _touch(tmp_path, "package.json", json.dumps({"scripts": {"test": "vitest"}}))
    assert derive_verify_commands(tmp_path) == [["npm", "test"]]


def test_makefile_needs_test_target(tmp_path):
    _touch(tmp_path, "Makefile", "build:\n\techo build\n")
    assert derive_verify_commands(tmp_path) is None
    _touch(tmp_path, "Makefile", "test:\n\techo test\n")
    assert derive_verify_commands(tmp_path) == [["make", "test"]]


@pytest.mark.parametrize("evidence,expected", [
    ("pyproject.toml", ["python3", "-m", "pytest"]),
    ("pytest.ini", ["python3", "-m", "pytest"]),
    ("go.mod", ["go", "test", "./..."]),
    ("Cargo.toml", ["cargo", "test"]),
])
def test_single_file_candidates(tmp_path, evidence, expected):
    _touch(tmp_path, evidence, "")
    assert derive_verify_commands(tmp_path) == [expected]


def test_no_entry_point_is_not_guessed(tmp_path):
    _touch(tmp_path, "README.md", "nothing to run\n")
    assert derive_verify_commands(tmp_path) is None


# ── 非平凡枚举（AC6：禁「之类」）─────────────────────────────────────────


@pytest.mark.parametrize("argv", [["true"], ["echo"], [":"], ["exit", "0"], ["exit 0"]])
def test_single_shell_command_is_shell(argv):
    assert is_shell_declaration([argv]) is True


def test_two_commands_is_not_shell():
    assert is_shell_declaration([["true"], ["echo"]]) is False


def test_real_command_is_not_shell():
    assert is_shell_declaration([["./test.sh"]]) is False
    assert is_shell_declaration([["npm", "test"]]) is False


def test_empty_or_missing_is_not_shell():
    assert is_shell_declaration([]) is False
    assert is_shell_declaration(None) is False


def test_shell_commands_are_the_enumeration():
    """枚举是**单一真源**：`--help` 文案与 doctor 文案都从它渲染。"""
    assert SHELL_COMMANDS == ("true", "echo", ":", "exit 0")
    display = shell_commands_display()
    for cmd in SHELL_COMMANDS:
        assert cmd in display


def test_help_text_renders_the_same_enumeration(capsys):
    from _lib.cli.commit_gate_cmd import cmd_commit_gate

    assert cmd_commit_gate(["--help"]) == 0
    out = capsys.readouterr().out
    for cmd in SHELL_COMMANDS:
        assert cmd in out, cmd
