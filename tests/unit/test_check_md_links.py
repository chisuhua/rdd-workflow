"""Unit tests for tests/scripts/check_md_links.py — the floor rules.

The bats file covers CLI behaviour; the floor (a checker that scanned nothing
must not report success) is a function-level rule, so it is tested here.
"""
from __future__ import annotations

import importlib.util
sys_path_stub = None
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "tests" / "scripts" / "check_md_links.py"

spec = importlib.util.spec_from_file_location("check_md_links", CHECKER)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_zero_files_never_passes(tmp_path):
    findings, links = mod.check_links([], floor=(1, 0))
    assert links == 0
    assert any("scan floor not met" in f for f in findings)


def test_zero_links_never_passes(tmp_path):
    doc = tmp_path / "a.md"
    doc.write_text("# doc\n\nno links here\n", encoding="utf-8")
    findings, links = mod.check_links([doc], floor=(1, 1))
    assert links == 0
    assert any("scan floor not met" in f for f in findings)


def test_a_scan_with_files_and_links_passes_the_floor(tmp_path):
    doc = tmp_path / "a.md"
    doc.write_text("# doc\n\n[ok](./b.md)\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("# b\n", encoding="utf-8")
    findings, links = mod.check_links([doc], floor=(1, 1))
    assert links == 1
    assert not any("scan floor not met" in f for f in findings)


def test_phase_versions_are_derived_from_skill_files():
    """"阶段 0.0.z" 是 SKILL.md 的命名空间 —— 必须由 SKILL.md 派生，不能猜。"""
    phases = mod._known_phase_versions()
    assert "0.0.5" in phases


def test_version_report_classifies_the_package_version():
    findings, report = mod.version_report([])
    assert findings == []
