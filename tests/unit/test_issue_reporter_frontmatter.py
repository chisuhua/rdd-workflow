"""Tests for ADR-0027 §4 issue file frontmatter completeness."""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))

from issue_reporter import detect_issue, write_issue_file  # type: ignore[import-not-found]


def test_all_reporter_fields_present(tmp_path: Path, monkeypatch) -> None:
    """IssueResult + _render_issue_body must populate all 6 ADR-0027 §4 Reporter fields."""
    monkeypatch.delenv("RDDF_SESSION_ID", raising=False)
    payload = {
        "description": "test issue",
        "stack": ["frame1", "frame2"],
        "metadata": {"phase": "guide-ship", "exit_code": 137},
    }
    result = detect_issue("phase-crash", payload)
    # Set skill_invoked manually (not yet wired in detect_issue)
    result.skill_invoked = "post-flow-analysis"
    result.project_root = str(tmp_path)

    file_path = write_issue_file(result, str(tmp_path))
    text = file_path.read_text(encoding="utf-8")

    # Required frontmatter fields
    for field in ("category", "detected_at", "rdd_workflow_version", "dedup_hash",
                  "submitted", "submitted_url", "exit_code"):
        assert f"{field}:" in text, f"missing frontmatter field: {field}\n{text}"

    # Required Reporter fields (ADR §4)
    for field in ("python_version", "git_version", "os_platform",
                  "project_hash", "rddf_session_id", "skill_invoked"):
        assert f"{field}:" in text, f"missing Reporter field: {field}\n{text}"

    # Sections present
    assert "## Description" in text
    assert "## Reporter" in text
    assert "## Stack trace" in text
    assert "## Repro" in text


def test_stack_trace_sanitized_no_home_path(tmp_path: Path, monkeypatch) -> None:
    """Stack trace must be sanitized — no /home/<user>/ leaks."""
    home_leak = f"/home/{os.environ.get('USER', 'someone')}/private/path"
    payload = {
        "description": "issue with leaked path",
        "stack": [f"Traceback at {home_leak}:42"],
    }
    result = detect_issue("flow-bug", payload)
    result.skill_invoked = "manual"
    result.project_root = str(tmp_path)
    file_path = write_issue_file(result, str(tmp_path))
    text = file_path.read_text(encoding="utf-8")
    assert "/home/" not in text, f"home path leaked: {text}"


def test_rddf_session_id_none_when_env_unset(tmp_path: Path, monkeypatch) -> None:
    """Without RDDF_SESSION_ID env, must emit 'none' in frontmatter."""
    monkeypatch.delenv("RDDF_SESSION_ID", raising=False)
    result = detect_issue("phase-crash", {"description": "x"})
    result.skill_invoked = "manual"
    result.project_root = str(tmp_path)
    file_path = write_issue_file(result, str(tmp_path))
    text = file_path.read_text(encoding="utf-8")
    # The rddf_session_id line must appear (either with value or with `none`)
    assert "rddf_session_id:" in text
    # When unset, the value should be `none`
    assert 'rddf_session_id: "none"' in text or "rddf_session_id: none" in text


def test_project_hash_deterministic_for_same_project_root(tmp_path: Path) -> None:
    """project_hash = sha256(project_root)[:8] — stable for same root."""
    expected = hashlib.sha256(str(tmp_path).encode()).hexdigest()[:8]

    result1 = detect_issue("flow-bug", {"description": "first", "project_root": str(tmp_path)})
    result1.skill_invoked = "manual"
    file_path1 = write_issue_file(result1, str(tmp_path))

    result2 = detect_issue("flow-bug", {"description": "second", "project_root": str(tmp_path)})
    result2.skill_invoked = "manual"
    file_path2 = write_issue_file(result2, str(tmp_path))

    text1 = file_path1.read_text(encoding="utf-8")
    text2 = file_path2.read_text(encoding="utf-8")
    assert f'project_hash: "{expected}"' in text1
    assert f'project_hash: "{expected}"' in text2