"""The disk status derivation has exactly ONE implementation.

`rddf status` (Mode A/B) and the verifier queue discovery must not keep two
copies of "what is this change's on-disk status" — that is the drift surface
this change removes. The assertion is *object identity* (the same function
object is imported under the name `_derive` in both modules), never
"looks the same".
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _lib.cli.status_cmd as status_cmd  # noqa: E402
import _lib.verifier.discovery as discovery  # noqa: E402


def _mk_change(root: Path, name: str, *, done: bool) -> Path:
    d = root / "openspec" / "changes" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "tasks.md").write_text("- [x] a\n" if done else "- [ ] a\n", encoding="utf-8")
    return d


def test_derive_status_completed_when_all_tasks_checked(tmp_path):
    _mk_change(tmp_path, "c1", done=True)
    assert status_cmd._derive(str(tmp_path), "c1") == "completed"


def test_derive_status_planned_when_tasks_incomplete(tmp_path):
    _mk_change(tmp_path, "c1", done=False)
    assert status_cmd._derive(str(tmp_path), "c1") == "planned"


def test_derive_status_planned_when_tasks_file_missing(tmp_path):
    (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
    assert status_cmd._derive(str(tmp_path), "c1") == "planned"


def test_derive_status_in_worktree_wins_over_completed(tmp_path):
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "x@x"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "x"], check=True)
    _mk_change(tmp_path, "c1", done=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "branch", "openspec/c1"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "worktree", "add", "-q", str(tmp_path / "wt"), "openspec/c1"],
        check=True,
    )
    assert status_cmd._derive(str(tmp_path), "c1") == "in_worktree"


def test_derive_status_uses_the_shared_module():
    """The derivation lives in `_lib/change_status.py` — one definition point."""
    from _lib import change_status

    assert status_cmd._derive is change_status.derive_status
    assert discovery._derive is change_status.derive_status
