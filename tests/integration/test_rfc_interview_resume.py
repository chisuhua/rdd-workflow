"""RFC interview state persistence + resume after interruption."""
from __future__ import annotations

import pytest

from _lib.rfc_interview_state import (
    load_state,
    save_state,
    clear_state,
    STATE_PATH_TEMPLATE,
)


def test_state_path_uses_rfc_dot_prefix(tmp_path, monkeypatch):
    """State file lives at .rddf/state/.rfc-interview-<name>.json (gitignored)."""
    monkeypatch.setenv("RDDF_STATE_DIR", str(tmp_path))
    path = STATE_PATH_TEMPLATE.format(state_dir=str(tmp_path), name="my-proposal")
    assert path == f"{tmp_path}/.rfc-interview-my-proposal.json"


def test_save_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_STATE_DIR", str(tmp_path))
    state = {"name": "my-proposal", "step": 2, "draft": {"title": "RFC"}}
    save_state("my-proposal", state)
    loaded = load_state("my-proposal")
    assert loaded == state


def test_resume_after_state_deletion(tmp_path, monkeypatch):
    """Acceptance: 删除 .json 后重跑 — load_state returns None (fresh start)."""
    monkeypatch.setenv("RDDF_STATE_DIR", str(tmp_path))
    save_state("x", {"step": 1})
    assert load_state("x") == {"step": 1}
    clear_state("x")
    assert load_state("x") is None


def test_load_state_missing_file_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("RDDF_STATE_DIR", str(tmp_path))
    assert load_state("never-saved") is None