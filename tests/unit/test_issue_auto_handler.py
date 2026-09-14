"""Unit tests for tools/issue-auto-handler.py (auto-triage + auto-proposal).

Mocks ``gh`` subprocess calls via monkeypatched ``_run_gh``. No network /
real GitHub access. Covers:
  - G2 repo allowlist gate (pass / reject)
  - G3 daily cap gate (boundary)
  - dedup against existing proposal (from_issue.check_dedup)
  - full L2 happy path: proposal + suggestion row + comment + label
  - dry-run: no writes to state / suggestions / proposal
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.issue_auto_handler as handler  # type: ignore[import-not-found]

from tools.issue_auto_handler import GateResult, RunResult, _gate_allowlist, _gate_daily_cap, run


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    (tmp_path / ".rddf" / "improvements").mkdir(parents=True)
    (tmp_path / "improvement-suggestions.md").write_text(
        "| 提案 | 优先级 | 来源 | 添加时间 | 状态 |\n"
        "|------|--------|------|----------|------|\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def sample_issue() -> dict:
    return {
        "number": 42,
        "title": "crash in skills/_lib/x.py",
        "body": "line 1\nline 2",
        "labels": [{"name": "auto-reported"}],
        "html_url": "https://github.com/chisuhua/rdd-workflow/issues/42",
        "createdAt": "2026-09-14T00:00:00Z",
    }


def _issue_list(num: int, title: str = "t") -> str:
    return json.dumps([{
        "number": num,
        "title": title,
        "body": "body",
        "labels": [{"name": "auto-reported"}],
        "html_url": f"https://github.com/x/y/issues/{num}",
        "createdAt": "2026-09-14T00:00:00Z",
    }])


# ── Gate tests ──────────────────────────────────────────────────────────


class TestAllowlistGate:
    def test_pass_when_repo_in_list(self) -> None:
        g = _gate_allowlist("chisuhua/rdd-workflow", "chisuhua/rdd-workflow,foo/bar")
        assert g.passed is True

    def test_reject_when_repo_absent(self) -> None:
        g = _gate_allowlist("evil/forks", "chisuhua/rdd-workflow")
        assert g.passed is False
        assert "not in allowlist" in g.reason

    def test_reject_when_allowlist_empty(self) -> None:
        g = _gate_allowlist("chisuhua/rdd-workflow", "")
        assert g.passed is False
        assert "allowlist empty" in g.reason


class TestDailyCapGate:
    def test_pass_below_cap(self) -> None:
        g = _gate_daily_cap(9, 10)
        assert g.passed is True

    def test_fail_at_cap(self) -> None:
        g = _gate_daily_cap(10, 10)
        assert g.passed is False
        assert "daily cap 10 reached" in g.reason

    def test_boundary_ok(self) -> None:
        g = _gate_daily_cap(0, 0)
        assert g.passed is False  # cap 0 = disabled


# ── Run-level tests (mock gh) ───────────────────────────────────────────


class TestRunGates:
    def test_repo_not_allowlisted_short_circuits(self, fake_project: Path) -> None:
        handler._run_gh = lambda _args: (_ for _ in ()).throw(  # pragma: no cover
            AssertionError("_run_gh must not be called when allowlist rejects")
        )
        result = run(
            repo="evil/forks",
            project_root=fake_project,
            allowlist="chisuhua/rdd-workflow",
            dry_run=True,
        )
        assert result.processed == []
        assert len(result.failed) == 1
        assert "G2-repo-allowlist" in result.failed[0]["reason"]

    def test_dedup_skips_existing_proposal(self, fake_project: Path, sample_issue: dict) -> None:
        # Pre-seed a proposal referencing issue 42 (mirrors check_dedup input)
        proposal = fake_project / ".rddf" / "improvements" / "existing-i42.md"
        proposal.write_text(
            "---\nissue_ref: 42\ngh_repo: chisuhua/rdd-workflow\n---\n# existing\n",
            encoding="utf-8",
        )
        calls: list[list[str]] = []

        def fake_gh(args: list[str]) -> str:
            calls.append(args)
            if args[0] == "issue" and args[1] == "list":
                return json.dumps([sample_issue])
            raise AssertionError(f"unexpected gh call: {args}")

        handler._run_gh = fake_gh
        result = run(
            repo="chisuhua/rdd-workflow",
            project_root=fake_project,
            allowlist="chisuhua/rdd-workflow",
            dry_run=True,
        )
        assert result.processed == []
        assert result.skipped == [{"issue": 42, "reason": "proposal already exists"}]

    def test_daily_cap_respected(self, fake_project: Path) -> None:
        issues = json.dumps([
            {"number": 1, "title": "a", "body": "", "labels": [], "html_url": "", "createdAt": ""},
            {"number": 2, "title": "b", "body": "", "labels": [], "html_url": "", "createdAt": ""},
        ])

        def fake_gh(args: list[str]) -> str:
            if args[0] == "issue" and args[1] == "list":
                return issues
            return "{}"

        handler._run_gh = fake_gh
        result = run(
            repo="chisuhua/rdd-workflow",
            project_root=fake_project,
            allowlist="chisuhua/rdd-workflow",
            daily_max=1,
            dry_run=True,
        )
        assert result.processed == [1]
        assert result.skipped == [{"issue": 2, "reason": "daily cap 1 reached"}]
        assert result.daily_remaining == 0


class TestHappyPath:
    def test_l2_full_flow(self, fake_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        issue = {
            "number": 11,
            "title": "[reflect] plan: plan:plan-done:general-error",
            "body": "Reflection Analysis body",
            "labels": [{"name": "auto-reported"}],
            "html_url": "https://github.com/chisuhua/rdd-workflow/issues/11",
            "createdAt": "2026-09-14T00:00:00Z",
        }
        gh_calls: list[list[str]] = []

        def fake_gh(args: list[str]) -> str:
            gh_calls.append(args)
            if args[0] == "issue" and args[1] == "list":
                return json.dumps([issue])
            return "ok"

        monkeypatch.setattr(handler, "_run_gh", fake_gh)
        result = run(
            repo="chisuhua/rdd-workflow",
            project_root=fake_project,
            allowlist="chisuhua/rdd-workflow",
            daily_max=10,
            dry_run=False,
        )

        # 1. processed
        assert result.processed == [11]
        assert result.daily_remaining == 9

        # 2. proposal file created under .rddf/improvements/
        proposal_files = list((fake_project / ".rddf" / "improvements").glob("*-i11.md"))
        assert len(proposal_files) == 1

        # 3. suggestion row appended
        suggestions = (fake_project / "improvement-suggestions.md").read_text(encoding="utf-8")
        assert "auto-handler from-issue (chisuhua/rdd-workflow#11)" in suggestions

        # 4. comment + label gh calls issued
        comment_calls = [c for c in gh_calls if c[:2] == ["issue", "comment"]]
        assert len(comment_calls) == 1
        label_calls = [c for c in gh_calls if c[:2] == ["issue", "edit"]]
        assert len(label_calls) == 1
        assert "triage-in-progress" in label_calls[0]

        # 5. state file persisted
        state = json.loads((fake_project / ".rddf" / "state" / ".issue-auto-handler.json").read_text())
        assert state["processed"] == [11]

    def test_dry_run_no_writes(self, fake_project: Path, sample_issue: dict) -> None:
        def fake_gh(args: list[str]) -> str:
            if args[0] == "issue" and args[1] == "list":
                return json.dumps([sample_issue])
            return "{}"

        handler._run_gh = fake_gh
        result = run(
            repo="chisuhua/rdd-workflow",
            project_root=fake_project,
            allowlist="chisuhua/rdd-workflow",
            dry_run=True,
        )
        assert result.processed == [42]
        assert not (fake_project / ".rddf" / "state" / ".issue-auto-handler.json").exists()
        assert list((fake_project / ".rddf" / "improvements").glob("*.md")) == []
        suggestions = (fake_project / "improvement-suggestions.md").read_text(encoding="utf-8")
        assert "auto-handler" not in suggestions