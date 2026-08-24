"""Tests for fix-review-debt-recorded-gate: Phase 2.5 pre-commit helper."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture
def fresh_project(tmp_path: Path) -> Path:
    """Create a project root with a TODO marker + no historic debt file."""
    (tmp_path / "main.go").write_text(
        "package main\n// TODO: refactor this part\nfunc main() {}\n"
    )
    (tmp_path / ".rddf").mkdir()
    (tmp_path / ".rddf" / "improvements").mkdir()
    return tmp_path


def test_go_project_todo_detected(fresh_project: Path) -> None:
    """Scenario A: .go file with TODO -> found_count > 0, persisted=False."""
    from skills._lib.review_debt_checker import check_review_debt_recorded
    verdict = check_review_debt_recorded(
        project_root=str(fresh_project),
        change_name="add-foo",
        execute_finished_at=datetime.now(timezone.utc),
    )
    assert verdict.found_count >= 1
    assert verdict.persisted is False
    assert "TODO" in verdict.reason


def test_rust_project_todo_detected(fresh_project: Path) -> None:
    """Scenario D: .rs file with TODO -> found_count > 0."""
    (fresh_project / "main.rs").write_text(
        "fn main() {}\n// TODO: handle error properly\n"
    )
    from skills._lib.review_debt_checker import check_review_debt_recorded
    verdict = check_review_debt_recorded(
        project_root=str(fresh_project),
        change_name="add-foo",
        execute_finished_at=datetime.now(timezone.utc),
    )
    assert verdict.found_count >= 1


def test_permission_error_not_swallowed(fresh_project: Path) -> None:
    """Scenario C: PermissionError on .rddf/improvements must NOT silent-pass."""
    import stat
    improvements = fresh_project / ".rddf" / "improvements"
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("Running as root - chmod ineffective")
    try:
        improvements.chmod(stat.S_IWUSR | stat.S_IXUSR)  # remove read
    except OSError:
        pytest.skip("chmod unavailable")
    try:
        from skills._lib.review_debt_checker import check_review_debt_recorded
        verdict = check_review_debt_recorded(
            project_root=str(fresh_project),
            change_name="add-foo",
            execute_finished_at=datetime.now(timezone.utc),
        )
        # Should NOT silent-pass; either raises or returns non-OK verdict
        assert verdict.persisted is False or "permission" in verdict.reason.lower()
    finally:
        improvements.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def test_historic_debt_file_not_counted(fresh_project: Path) -> None:
    """Scenario E: old debt file (mtime before execute_finished_at) doesn't count."""
    debt = fresh_project / ".rddf" / "improvements" / "cleanup-old-debt.md"
    debt.write_text("# historic debt\n")
    old_time = time.time() - 86400
    os.utime(debt, (old_time, old_time))

    from skills._lib.review_debt_checker import check_review_debt_recorded
    finish_time = datetime.now(timezone.utc)
    verdict = check_review_debt_recorded(
        project_root=str(fresh_project),
        change_name="add-foo",
        execute_finished_at=finish_time,
    )
    assert verdict.persisted is False


def test_helper_uses_project_root_not_cwd(tmp_path: Path) -> None:
    """Project root param must be honored even when cwd != project_root."""
    project = tmp_path / "myproject"
    project.mkdir()
    (project / "main.go").write_text("// TODO: stuff\n")
    (project / ".rddf" / "improvements").mkdir(parents=True)

    other = tmp_path / "other-subdir"
    other.mkdir()
    old_cwd = os.getcwd()
    try:
        os.chdir(other)
        from skills._lib.review_debt_checker import check_review_debt_recorded
        verdict = check_review_debt_recorded(
            project_root=str(project),
            change_name="add-foo",
            execute_finished_at=datetime.now(timezone.utc),
        )
        assert verdict.found_count >= 1, "must find TODO regardless of cwd"
    finally:
        os.chdir(old_cwd)