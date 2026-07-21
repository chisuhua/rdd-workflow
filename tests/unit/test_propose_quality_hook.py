"""Unit tests for skills/propose/scripts/propose_quality_hook.py."""
import json
from pathlib import Path

from skills.propose.scripts import propose_quality_hook as pqh


def _seed_good_change(root: str, name: str) -> None:
    change_dir = Path(root) / "openspec" / "changes" / name
    change_dir.mkdir(parents=True, exist_ok=True)
    proposal = (
        "## Why\n\n" + ("x" * 500) + "\n\nRefs ADR-0019.\n\n"
        "## In Scope\n\ndo thing\n\n## Out of Scope\n\nnot doing\n"
    )
    (change_dir / "proposal.md").write_text(proposal, encoding="utf-8")
    (change_dir / "tasks.md").write_text("## Tasks\n\n- [ ] one\n- [ ] two\n", encoding="utf-8")
    (Path(root) / "roadmap.md").write_text(f"# Roadmap\n\n- {name}\n", encoding="utf-8")


def test_run_quality_check_writes_valid_json(tmp_path):
    report = pqh.run_quality_check(str(tmp_path), "c1")
    assert report["schema_version"] == 1
    assert report["change"] == "c1"
    assert "warnings" in report
    saved_path = tmp_path / ".rddf" / "state" / "propose-quality.json"
    assert saved_path.exists()
    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    assert saved["change"] == "c1"


def test_invoke_returns_zero_in_default_mode(tmp_path, monkeypatch, capsys):
    _seed_good_change(str(tmp_path), "c1")
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("STRICT_PROPOSE_GATE", raising=False)
    assert pqh.invoke_from_propose_phase4("c1") == 0
    captured = capsys.readouterr()
    assert "passes all quality checks" in captured.out


def test_invoke_returns_one_under_strict_with_warnings(tmp_path, monkeypatch, capsys):
    change_dir = tmp_path / "openspec" / "changes" / "c1"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("## Why\n\nshort\n", encoding="utf-8")
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("STRICT_PROPOSE_GATE", "yes")
    assert pqh.invoke_from_propose_phase4("c1") == 1


def test_invoke_returns_zero_under_strict_no_warnings(tmp_path, monkeypatch, capsys):
    _seed_good_change(str(tmp_path), "c1")
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("STRICT_PROPOSE_GATE", "yes")
    assert pqh.invoke_from_propose_phase4("c1") == 0


def test_report_has_correct_schema_version_and_counts(tmp_path):
    _seed_good_change(str(tmp_path), "c1")
    report = pqh.run_quality_check(str(tmp_path), "c1")
    assert report["schema_version"] == 1
    assert report["check_count"] == 5
    assert report["passed_count"] == 5
    saved = json.loads((tmp_path / ".rddf" / "state" / "propose-quality.json").read_text())
    assert saved["passed_count"] == 5


def test_run_quality_check_aggregates_warnings(tmp_path, monkeypatch):
    change_dir = tmp_path / "openspec" / "changes" / "c1"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text(
        "## Why\n\n<skeleton motivation - 1-2 sentences>\n\n"
        "## What Changes\n\n- <file path or module affected>\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("STRICT_PROPOSE_GATE", "yes")
    report = pqh.run_quality_check(str(tmp_path), "c1")
    assert len(report["warnings"]) >= 1
    assert report["passed_count"] == 5 - len(report["warnings"])
