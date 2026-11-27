"""rdd-doctor category `commit-gate` —— 声明的**可用性三面**（design D-4）。

判据真源：`openspec/changes/add-commit-gate-declaration-bootstrap/proposal.md` 的 AC3–AC5。
⚠ 三面**互斥**（按 未声明 → 空壳 → 未 tracked 判，最多一条 finding）；⚠ 只报 WARNING（检测 ≠ 拦截）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "rdd-doctor" / "scripts"))

from checks.commit_gate_check import run  # noqa: E402


def _write_decl(root: Path, payload: dict) -> None:
    path = root / ".rddf" / "commit-gate.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)


def test_missing_declaration_is_reported(tmp_path):
    findings = run(tmp_path)
    assert len(findings) == 1
    assert findings[0].category == "commit-gate"
    assert findings[0].file == ".rddf/commit-gate.json"
    assert "不设门禁" in findings[0].fix_hint
    assert "rddf commit-gate init" in findings[0].fix_hint


def test_shell_declaration_is_reported(tmp_path):
    _write_decl(tmp_path, {"verify_commands": [["true"]]})
    findings = run(tmp_path)
    assert len(findings) == 1
    assert "空壳" in findings[0].fix_hint
    assert "true" in findings[0].fix_hint


def test_untracked_declaration_is_reported(tmp_path):
    _git_init(tmp_path)
    _write_decl(tmp_path, {"verify_commands": [["./test.sh"]]})
    findings = run(tmp_path)
    assert len(findings) == 1
    assert "未 git-tracked" in findings[0].fix_hint
    assert "git add" in findings[0].fix_hint


def test_tracked_non_shell_declaration_is_silent(tmp_path):
    _git_init(tmp_path)
    _write_decl(tmp_path, {"verify_commands": [["./test.sh"]]})
    subprocess.run(["git", "add", ".rddf/commit-gate.json"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "decl"], cwd=tmp_path, check=True)
    assert run(tmp_path) == []


def test_faces_are_mutually_exclusive(tmp_path):
    """空壳 + 未 tracked ⇒ **只报空壳**（不重复报未 tracked）。"""
    _git_init(tmp_path)
    _write_decl(tmp_path, {"verify_commands": [["exit", "0"]]})
    findings = run(tmp_path)
    assert len(findings) == 1
    assert "空壳" in findings[0].fix_hint


def test_unparsable_declaration_is_reported_as_unusable(tmp_path):
    path = tmp_path / ".rddf" / "commit-gate.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    findings = run(tmp_path)
    assert len(findings) == 1
    assert "解析失败" in findings[0].fix_hint
