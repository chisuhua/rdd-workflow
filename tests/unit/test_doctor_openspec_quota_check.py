"""Unit tests for the doctor `openspec-quota` checker.

AC-5② (the checker shares `_lib.openspec_quota.evaluate` with the CLI),
AC-6 (CRITICAL + gate placement + finding location), AC-7 (unconfigured ⇒
no findings), plus the two degradation paths (config error ⇒ WARNING;
module unavailable ⇒ INFO, never raise).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-doctor" / "scripts"))

import _lib.openspec_quota as quota  # noqa: E402

import checks.openspec_quota_check as check  # noqa: E402
from doctor_main import _CHECKERS, _GATES  # noqa: E402
from doctor_render import Severity  # noqa: E402


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


# ---------------------------------------------------------------------------
# AC-7 — unconfigured / within limit ⇒ silence
# ---------------------------------------------------------------------------

def test_unconfigured_project_has_no_findings(tmp_path: Path) -> None:
    _make_changes(tmp_path, ["a", "b", "c", "d"], archive=True)
    assert check.run(project_root=tmp_path) == []


def test_within_limit_has_no_findings(tmp_path: Path) -> None:
    _write_yaml(tmp_path, "openspec:\n  proposed_limit: 3\n")
    _make_changes(tmp_path, ["a"], archive=True)
    assert check.run(project_root=tmp_path) == []


# ---------------------------------------------------------------------------
# AC-6 — exceeded ⇒ CRITICAL with the config as its location
# ---------------------------------------------------------------------------

def test_exceeded_is_critical_and_points_at_config(tmp_path: Path) -> None:
    _write_yaml(tmp_path, "openspec:\n  proposed_limit: 3\n")
    _make_changes(tmp_path, ["a", "b", "c", "d"], archive=True)

    findings = check.run(project_root=tmp_path)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity is Severity.CRITICAL
    assert finding.category == "openspec-quota"
    assert finding.file == ".rddf/project.yaml"
    assert finding.line == 2
    assert "4 open change(s)" in finding.snippet


def test_gate_placement_is_advisory_only() -> None:
    """AC-6: a project that opted in wants the failure, but third parties must
    not be blocked ⇒ advisory gate, never structural."""
    assert "openspec-quota" in _CHECKERS
    assert "openspec-quota" in _GATES["advisory"]["categories"]
    assert "openspec-quota" not in _GATES["structural"]["categories"]


# ---------------------------------------------------------------------------
# configuration errors ⇒ WARNING (not CRITICAL, not silence)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "yaml_text",
    ['openspec:\n  proposed_limit: "3"\n', "proposed_limit: 3\n"],
    ids=["wrong-type", "wrong-nesting"],
)
def test_config_error_is_warning(tmp_path: Path, yaml_text: str) -> None:
    _write_yaml(tmp_path, yaml_text)
    findings = check.run(project_root=tmp_path)
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING
    assert findings[0].file == ".rddf/project.yaml"
    assert "proposed_limit" in findings[0].snippet


# ---------------------------------------------------------------------------
# AC-5② — the checker goes through the shared implementation
# ---------------------------------------------------------------------------

def test_checker_uses_the_shared_evaluate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        quota, "evaluate", lambda root, override=None: quota.QuotaResult(active=9, limit=3, ok=False)
    )
    findings = check.run(project_root=tmp_path)
    assert len(findings) == 1
    assert findings[0].severity is Severity.CRITICAL
    assert "9 open change(s)" in findings[0].snippet


def test_checker_follows_evaluate_when_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_changes(tmp_path, ["a", "b", "c", "d"])
    monkeypatch.setattr(
        quota, "evaluate", lambda root, override=None: quota.QuotaResult(active=0, limit=None, ok=True)
    )
    assert check.run(project_root=tmp_path) == []


# ---------------------------------------------------------------------------
# degradation: module unavailable ⇒ INFO, never raise
# ---------------------------------------------------------------------------

def test_missing_implementation_degrades_to_info(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check, "openspec_quota", None)
    findings = check.run(project_root=tmp_path)
    assert len(findings) == 1
    assert findings[0].severity is Severity.INFO
    assert "unavailable" in findings[0].snippet
