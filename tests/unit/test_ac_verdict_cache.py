"""Tests for SHA-fingerprint verdict cache.

Per ADR-0034 §7.2 + Oracle §C: avoids double LLM calls when
archive_gate_check runs after rdd-verifier (same codebase commit = cache hit).
"""
import json
import subprocess as sp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _lib.verifier.cache import verdict_cache, read_verdict_cache, is_cache_fresh


def _git(cwd, *args):
    return sp.check_output(["git", "-C", cwd] + list(args)).decode().strip()


def _make_repo_with_commit(tmpdir):
    repo = Path(tmpdir) / "repo"
    repo.mkdir()
    _git(str(repo), "init", "-q")
    _git(str(repo), "config", "user.email", "test@test")
    _git(str(repo), "config", "user.name", "Test")
    (repo / "x.txt").write_text("hello")
    _git(str(repo), "add", "x.txt")
    _git(str(repo), "commit", "-q", "-m", "init")
    return repo


def test_write_and_read_cache(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    sha = _git(str(repo), "rev-parse", "HEAD")
    state_dir = repo / ".rddf" / "state"
    state_dir.mkdir(parents=True)

    verdict = [{"ac_id": "AC-1", "status": "pass", "confidence": 0.9,
                "evidence": [], "reasoning": "ok"}]
    path = verdict_cache(repo, "test-change", sha, verdict, ran_by="rdd-verifier")
    assert path.is_file()

    cached = read_verdict_cache(repo, "test-change")
    assert cached is not None
    assert cached["codebase_commit"] == sha
    assert cached["verdict"] == verdict
    assert cached["ran_by"] == "rdd-verifier"


def test_is_cache_fresh_match(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    sha = _git(str(repo), "rev-parse", "HEAD")
    (repo / ".rddf" / "state").mkdir(parents=True)
    verdict_cache(repo, "x", sha, [], "rdd-verifier")
    assert is_cache_fresh(repo, "x", sha) is True


def test_is_cache_fresh_stale(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    sha = _git(str(repo), "rev-parse", "HEAD")
    (repo / ".rddf" / "state").mkdir(parents=True)
    verdict_cache(repo, "x", sha, [], "rdd-verifier")
    (repo / "y.txt").write_text("world")
    _git(str(repo), "add", "y.txt")
    _git(str(repo), "commit", "-q", "-m", "y")
    new_sha = _git(str(repo), "rev-parse", "HEAD")
    assert new_sha != sha
    assert is_cache_fresh(repo, "x", new_sha) is False


def test_read_cache_missing_returns_none(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    assert read_verdict_cache(repo, "nonexistent") is None
    assert is_cache_fresh(repo, "nonexistent", "abc1234") is False


def test_read_cache_corrupt_returns_none(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    state_dir = repo / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    cache_file = state_dir / ".ac-verdict-corrupt.json"
    cache_file.write_text("{invalid json")
    assert read_verdict_cache(repo, "corrupt") is None
    assert is_cache_fresh(repo, "corrupt", "abc1234") is False


def test_cache_persists_at_correct_path(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    sha = _git(str(repo), "rev-parse", "HEAD")
    (repo / ".rddf" / "state").mkdir(parents=True)
    verdict_cache(repo, "my-change", sha, [], "archive_gate_check")
    expected = repo / ".rddf" / "state" / ".ac-verdict-my-change.json"
    assert expected.is_file()
    cached = read_verdict_cache(repo, "my-change")
    assert cached["ran_by"] == "archive_gate_check"


def test_cache_overwrites_on_second_write(tmp_path):
    repo = _make_repo_with_commit(str(tmp_path))
    sha = _git(str(repo), "rev-parse", "HEAD")
    (repo / ".rddf" / "state").mkdir(parents=True)
    verdict_cache(repo, "x", sha, [{"ac_id": "AC-1", "status": "pass",
                                     "confidence": 0.9, "evidence": [],
                                     "reasoning": "first"}],
                   "rdd-verifier")
    verdict_cache(repo, "x", sha, [{"ac_id": "AC-1", "status": "fail",
                                     "confidence": 0.9, "evidence": [],
                                     "reasoning": "second"}],
                   "rdd-verifier")
    cached = read_verdict_cache(repo, "x")
    assert cached["verdict"][0]["status"] == "fail"
    assert "second" in cached["verdict"][0]["reasoning"]