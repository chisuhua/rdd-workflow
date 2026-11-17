"""Root + anchor contract of the archive gate (fix-verifier-gate-cache-root).

The gate had three mutually inconsistent conventions:

  * the bash segment read the cache from ``$tasks_root`` while the python
    segment read it from a self-derived main-repo root;
  * the bash segment compared the cache against ``HEAD`` while the write side
    records the ``openspec/<change>`` branch tip;
  * the integrity helper took one env var for two different roots.

These tests pin the replacement contract:

  * two roots, one job each — the gate root (artifacts + cache) and the
    canonical state root (the project registry);
  * one anchor — the implementation branch tip, root-independent;
  * the cache is read from the gate root first, the state root second, and
    the side that was used is reported.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from _lib.verifier.archive_gate import (  # noqa: E402
    check_archive_readiness,
    find_verdict_cache,
    resolve_branch_tip,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _make_repo(root: Path, branch: str = "openspec/ch-x") -> str:
    """Init a repo with one commit on `branch`; return the branch tip."""
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(root), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "x@x"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "x"], check=True)
    (root / "f").write_text("x")
    subprocess.run(["git", "-C", str(root), "add", "f"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "init"], check=True)
    subprocess.run(["git", "-C", str(root), "checkout", "-q", "-b", branch], check=True)
    return _git(root, "rev-parse", branch)


def _write_cache(root: Path, change: str, sha: str) -> Path:
    path = root / ".rddf" / "state" / "verifier" / f".ac-verdict-{change}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": 2, "version": 2, "change": change,
        "codebase_commit": sha, "verdict": [], "ran_by": "rdd-verifier",
        "verification_state": "passed", "failed_acs": [],
    }), encoding="utf-8")
    return path


def _write_registry(root: Path, change: str, verdict_sha: str) -> None:
    state = root / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "iteration.json").write_text(json.dumps({
        "version": 7, "updated_at": "2026-11-17T00:00:00Z", "current_phase": "phase-2",
        "changes": [{
            "name": change, "status": "in_worktree", "added_at": "2026-11-17T00:00:00Z",
            "verification": {"state": "passed", "verdict_sha": verdict_sha,
                             "archive_ready": True, "checked_at": "2026-11-17T00:00:00Z"},
        }],
    }), encoding="utf-8")


class TestFindVerdictCache:
    def test_gate_root_wins_when_both_sides_hold_a_cache(self, tmp_path):
        gate = tmp_path / "wt"
        state = tmp_path / "main"
        gate.mkdir()
        state.mkdir()
        _write_cache(gate, "ch-x", "aaa")
        _write_cache(state, "ch-x", "bbb")

        cache, root = find_verdict_cache(gate, state, "ch-x")
        assert root == gate
        assert cache["codebase_commit"] == "aaa"

    def test_state_root_is_the_fallback(self, tmp_path):
        gate = tmp_path / "wt"
        state = tmp_path / "main"
        gate.mkdir()
        state.mkdir()
        _write_cache(state, "ch-x", "bbb")

        cache, root = find_verdict_cache(gate, state, "ch-x")
        assert root == state
        assert cache["codebase_commit"] == "bbb"

    def test_missing_on_both_sides(self, tmp_path):
        gate = tmp_path / "wt"
        state = tmp_path / "main"
        gate.mkdir()
        state.mkdir()
        assert find_verdict_cache(gate, state, "ch-x") == (None, None)


class TestAnchor:
    def test_anchor_is_the_branch_tip_not_head(self, tmp_path):
        """The anchor must NOT be HEAD (spec: verifier-lifecycle)."""
        repo = tmp_path / "repo"
        tip = _make_repo(repo)
        # Move the default branch on: HEAD != branch tip now.
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "main"], check=True)
        (repo / "g").write_text("y")
        subprocess.run(["git", "-C", str(repo), "add", "g"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "more"], check=True)
        assert _git(repo, "rev-parse", "HEAD") != tip

        assert resolve_branch_tip(repo, "ch-x") == tip

    def test_missing_branch_resolves_to_none(self, tmp_path):
        repo = tmp_path / "repo"
        _make_repo(repo)
        assert resolve_branch_tip(repo, "no-such-change") is None


class TestCheckArchiveReadiness:
    def test_reads_the_registry_from_the_state_root(self, tmp_path):
        """A linked worktree never carries .rddf/state/ (gitignored)."""
        state = tmp_path / "main"
        gate = tmp_path / "wt"
        state.mkdir()
        gate.mkdir()
        tip = _make_repo(state)
        _write_registry(state, "ch-x", tip)
        _write_cache(gate, "ch-x", tip)

        result = check_archive_readiness(gate, "ch-x", state_root=state)
        assert result["ready"] is True, result
        assert result["cache_root"] == str(gate)

    def test_cache_in_the_state_root_is_accepted(self, tmp_path):
        state = tmp_path / "main"
        gate = tmp_path / "wt"
        state.mkdir()
        gate.mkdir()
        tip = _make_repo(state)
        _write_registry(state, "ch-x", tip)
        _write_cache(state, "ch-x", tip)

        result = check_archive_readiness(gate, "ch-x", state_root=state)
        assert result["ready"] is True, result
        assert result["cache_root"] == str(state)

    def test_stale_registry_verdict_sha_is_rejected(self, tmp_path):
        """The contract check binds the registry's verdict_sha to the anchor."""
        state = tmp_path / "main"
        gate = tmp_path / "wt"
        state.mkdir()
        gate.mkdir()
        _make_repo(state)
        _write_registry(state, "ch-x", "0000000000000000000000000000000000000000")
        _write_cache(gate, "ch-x", "0000000000000000000000000000000000000000")

        result = check_archive_readiness(gate, "ch-x", state_root=state)
        assert result["ready"] is False
        assert "stale" in result["reason"].lower()


class TestIntegrityHelperRoots:
    """The integrity helper must take the two roots SEPARATELY."""

    def _run(self, proposal_root: Path, cache_root: Path, change: str) -> dict:
        env = {
            **__import__("os").environ,
            "RDDF_PROJECT_ROOT": str(proposal_root),
            "CHANGE_NAME_FOR_INTEGRITY": change,
            "PYTHONPATH": str(REPO_ROOT),
        }
        out = subprocess.run(
            [sys.executable, str(REPO_ROOT / "_lib" / "cli" / "rdd_verify_cmd.py"),
             "--validate-cache-for-archive",
             "--proposal-root", str(proposal_root),
             "--cache-root", str(cache_root)],
            capture_output=True, text=True, env=env,
        )
        return json.loads(out.stdout)

    def test_proposal_and_cache_roots_are_independent(self, tmp_path):
        proposal_root = tmp_path / "wt"
        cache_root = tmp_path / "main"
        (proposal_root / "openspec" / "changes" / "ch-x").mkdir(parents=True)
        (proposal_root / "openspec" / "changes" / "ch-x" / "proposal.md").write_text(
            "## Acceptance Criteria\n- AC-1: works\n", encoding="utf-8")
        # The cache is in the OTHER root and covers AC-1.
        _write_cache(cache_root, "ch-x", "sha")
        cache_file = cache_root / ".rddf" / "state" / "verifier" / ".ac-verdict-ch-x.json"
        doc = json.loads(cache_file.read_text())
        doc["verdict"] = [{"ac_id": "AC-1", "status": "pass",
                            "confidence": 0.9, "evidence": [{"tool": "Grep"}],
                            "reasoning": "ok"}]
        cache_file.write_text(json.dumps(doc), encoding="utf-8")

        result = self._run(proposal_root, cache_root, "ch-x")
        assert result["complete"] is True, result

    def test_cache_missing_in_the_declared_cache_root(self, tmp_path):
        proposal_root = tmp_path / "wt"
        cache_root = tmp_path / "main"
        (proposal_root / "openspec" / "changes" / "ch-x").mkdir(parents=True)
        (proposal_root / "openspec" / "changes" / "ch-x" / "proposal.md").write_text(
            "## Acceptance Criteria\n- AC-1: works\n", encoding="utf-8")
        # A cache in the OTHER root must NOT be picked up implicitly.
        _write_cache(proposal_root, "ch-x", "sha")

        result = self._run(proposal_root, cache_root, "ch-x")
        assert result["complete"] is False, result
        assert "cache missing" in result["problems"][0]
