"""Unit tests for skills/rdd-doctor/scripts/checks/roadmap_backup_check.py."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from checks.roadmap_backup_check import run  # noqa: E402


def _setup_backup(tmp_path: Path, *, backup_dirs: list[str]) -> Path:
    repo = tmp_path
    backup_root = repo / ".rddf" / "roadmap" / ".backup"
    backup_root.mkdir(parents=True, exist_ok=True)
    for d in backup_dirs:
        (backup_root / d).mkdir(exist_ok=True)
    return repo


def test_roadmap_backup_no_backup_dir_clean(tmp_path: Path):
    """No .backup/ dir at all → no findings."""
    findings = run(project_root=tmp_path)
    assert findings == [], f"expected clean, got: {findings}"


def test_roadmap_backup_empty_backup_dir_clean(tmp_path: Path):
    """.backup/ exists but empty → no findings."""
    (tmp_path / ".rddf" / "roadmap" / ".backup").mkdir(parents=True)
    findings = run(project_root=tmp_path)
    assert findings == [], f"expected clean (empty), got: {findings}"


def test_roadmap_backup_single_recent_info(tmp_path: Path):
    """Single recent backup → INFO (history retention expected)."""
    today = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    repo = _setup_backup(tmp_path, backup_dirs=[today])
    findings = run(project_root=repo)
    info = [f for f in findings if f.severity == Severity.INFO]
    assert len(info) >= 1, f"expected ≥1 INFO, got: {findings}"


def test_roadmap_backup_multiple_warns(tmp_path: Path):
    """Multiple backup dirs coexist → WARNING."""
    repo = _setup_backup(tmp_path, backup_dirs=[
        "20260801T120000Z",
        "20260901T120000Z",
        "20261001T120000Z",
    ])
    findings = run(project_root=repo)
    warns = [f for f in findings if f.severity == Severity.WARNING]
    assert len(warns) >= 1, f"expected ≥1 WARNING, got: {findings}"


def test_roadmap_backup_stale_warns(tmp_path: Path):
    """Backup older than 90 days → WARNING."""
    old = (datetime.now(timezone.utc) - timedelta(days=120)).strftime("%Y%m%dT%H%M%SZ")
    repo = _setup_backup(tmp_path, backup_dirs=[old])
    findings = run(project_root=repo)
    stale = [f for f in findings if f.severity == Severity.WARNING and "stale" in f.snippet.lower()]
    assert len(stale) >= 1, f"expected ≥1 stale WARNING, got: {findings}"


def test_roadmap_backup_malformed_name_warns(tmp_path: Path):
    """Backup dir name not matching ISO basic-format → WARNING."""
    repo = _setup_backup(tmp_path, backup_dirs=["not-a-timestamp"])
    findings = run(project_root=repo)
    malformed = [f for f in findings if f.severity == Severity.WARNING and "malformed" in f.snippet.lower()]
    assert len(malformed) >= 1, f"expected ≥1 malformed WARNING, got: {findings}"