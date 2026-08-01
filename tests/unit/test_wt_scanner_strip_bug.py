import subprocess
from pathlib import Path

from skills._lib.workflow_synthesizer import _detect_working_tree_issues


def _git_init(tmpdir: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmpdir)], check=True)
    subprocess.run(
        ["git", "-C", str(tmpdir), "config", "user.email", "t@t"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmpdir), "config", "user.name", "t"],
        check=True,
    )
    (tmpdir / "init").write_text("init\n")
    subprocess.run(["git", "-C", str(tmpdir), "add", "init"], check=True)
    subprocess.run(
        ["git", "-C", str(tmpdir), "commit", "-q", "-m", "init"],
        check=True,
    )


def _track_file(tmpdir: Path, relative_path: str) -> Path:
    path = tmpdir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("base\n")
    subprocess.run(
        ["git", "-C", str(tmpdir), "add", relative_path],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmpdir), "commit", "-q", "-m", f"track {relative_path}"],
        check=True,
    )
    return path


def test_working_tree_only_modification_is_modified(tmp_path: Path) -> None:
    _git_init(tmp_path)
    tracked_file = _track_file(tmp_path, "foo.md")
    tracked_file.write_text("changed\n")

    issues = _detect_working_tree_issues(str(tmp_path))

    assert len(issues) == 1
    assert issues[0].category == "modified"
    assert issues[0].path == "foo.md"
    assert issues[0].severity == "needs_review"


def test_staged_modification_is_staged(tmp_path: Path) -> None:
    _git_init(tmp_path)
    tracked_file = _track_file(tmp_path, "foo.md")
    tracked_file.write_text("changed\n")
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "foo.md"],
        check=True,
    )

    issues = _detect_working_tree_issues(str(tmp_path))

    assert len(issues) == 1
    assert issues[0].category == "staged"
    assert issues[0].path == "foo.md"
    assert issues[0].severity == "needs_review"


def test_path_is_not_truncated_for_working_tree_only(tmp_path: Path) -> None:
    _git_init(tmp_path)
    tracked_file = _track_file(tmp_path, "improvements/proposal.md")
    tracked_file.write_text("changed\n")

    issues = _detect_working_tree_issues(str(tmp_path))

    assert len(issues) == 1
    assert issues[0].path == "improvements/proposal.md"
    assert issues[0].path[0] == "i"
