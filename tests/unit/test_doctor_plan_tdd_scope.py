"""plan-tdd：活跃 change 的 plan 必查；历史 plan（git age > 30 天）跳过。

import 模式（必须照抄既有做法，见 tests/unit/test_plan_tdd_check.py:8-13）：
`skills/rdd-doctor` 目录名含**连字符** → `from skills.rdd-doctor... import` 是
**SyntaxError**（连字符被解析成减号）。正确做法是把 `skills/rdd-doctor/scripts`
插进 sys.path 后按包路径 `from checks.plan_tdd_check import run` 导入。
conftest 的 dash-bridge 不含 `rdd-doctor`，救不了这个 import。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HISTORICAL_DAYS = 30
OLD_DATE = "2020-01-01T00:00:00"

_SCRIPTS_DIR = REPO_ROOT / "skills" / "rdd-doctor" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _git(root: Path, *args: str, when: str | None = None):
    env = dict(os.environ)
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    subprocess.run(["git", *args], cwd=str(root), check=True, env=env,
                   capture_output=True)


def _init_repo(root: Path):
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")


def _write_state(root: Path, changes):
    state = root / ".rddf" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "iteration.json").write_text(json.dumps({"version": 7, "changes": changes}))


def _write_plan(root: Path, stem: str) -> Path:
    plans = root / ".rddf" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    p = plans / f"{stem}.md"
    p.write_text("# plan without TDD markers\n")
    return p


def test_active_plan_is_flagged(tmp_path, monkeypatch):
    from checks.plan_tdd_check import run as run_check

    _write_plan(tmp_path, "live-change")
    _write_state(tmp_path, [{"name": "live-change", "status": "in_worktree"}])

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings = run_check(tmp_path)
    assert len(findings) == 1, findings


def test_historical_plan_of_archived_change_is_skipped(tmp_path, monkeypatch):
    """归档 change 的旧 plan → 跳过，不产生 finding（本 change 的降噪目标）。"""
    from checks.plan_tdd_check import run as run_check

    _init_repo(tmp_path)
    _write_plan(tmp_path, "old-change")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "old plan", when=OLD_DATE)
    _write_state(tmp_path, [{"name": "old-change", "status": "archived"}])

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    assert run_check(tmp_path) == []


def test_active_change_plan_is_checked_even_when_old(tmp_path, monkeypatch):
    """活跃 change 优先于年龄判据 —— 休眠很久后被重新激活的 change 不能被漏掉。"""
    from checks.plan_tdd_check import run as run_check

    _init_repo(tmp_path)
    _write_plan(tmp_path, "revived-change")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "old plan", when=OLD_DATE)
    _write_state(tmp_path, [{"name": "revived-change", "status": "in_worktree"}])

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    assert len(run_check(tmp_path)) == 1


def test_recent_unregistered_plan_is_flagged(tmp_path, monkeypatch):
    """近期新增但未登记的 plan 仍要检查（保守方向）。"""
    from checks.plan_tdd_check import run as run_check

    _init_repo(tmp_path)
    _write_plan(tmp_path, "orphan-plan")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "plan")
    _write_state(tmp_path, [{"name": "other-change", "status": "archived"}])

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings = run_check(tmp_path)
    assert len(findings) == 1, findings


def test_open_openspec_change_dir_counts_as_active(tmp_path, monkeypatch):
    """iteration.json 是 gitignored 运行时文件，会 drift；未归档的 change 目录也算活跃。"""
    from checks.plan_tdd_check import run as run_check

    _init_repo(tmp_path)
    _write_plan(tmp_path, "dir-only-change")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "old plan", when=OLD_DATE)
    (tmp_path / "openspec" / "changes" / "dir-only-change").mkdir(parents=True)
    _write_state(tmp_path, [{"name": "dir-only-change", "status": "archived"}])

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings = run_check(tmp_path)
    assert len(findings) == 1, findings


def test_archived_change_plan_is_checked_when_git_age_unavailable(tmp_path, monkeypatch):
    """git age 不可得（这里是非 git 目录）→ 按「近期」处理，仍然检查。"""
    from checks.plan_tdd_check import run as run_check

    _write_plan(tmp_path, "old-change")
    _write_state(tmp_path, [{"name": "old-change", "status": "archived"}])

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    assert len(run_check(tmp_path)) == 1


def test_missing_or_broken_state_is_not_fatal(tmp_path, monkeypatch):
    """iteration.json 缺失 / 损坏 → 不得 raise。"""
    from checks.plan_tdd_check import run as run_check

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    assert run_check(tmp_path) == []                   # 缺失

    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    (state / "iteration.json").write_text("{ not json")
    assert run_check(tmp_path) == []                   # 损坏
