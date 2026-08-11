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


def test_untracked_file_is_reported_info(tmp_path: Path) -> None:
    """Untracked file in tracked dir is reported. .rddf/improvements/ is git-tracked,
    so files there are reported (the dotfile filter targets .venv/.pytest_cache, etc.)."""
    _git_init(tmp_path)
    (tmp_path / "proposals").mkdir()
    (tmp_path / "proposals" / "foo.md").write_text("new\n" * 100)

    issues = _detect_working_tree_issues(str(tmp_path))

    assert len(issues) == 1
    assert issues[0].category == "untracked_file"
    assert issues[0].path == "proposals/foo.md"
    assert issues[0].severity == "info"


def test_large_untracked_directory_is_safe_auto_fix(tmp_path: Path) -> None:
    _git_init(tmp_path)
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "big.bin").write_bytes(b"0" * (50 * 1024 * 1024))

    issues = _detect_working_tree_issues(str(tmp_path))

    assert len(issues) == 1
    assert issues[0].category == "untracked_dirs"
    assert issues[0].path == "build/"
    assert issues[0].severity == "safe_auto_fix"
    assert issues[0].fix_command == 'echo "build/" >> .gitignore'


def test_hidden_directory_is_not_reported(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "python").write_text("bin\n")

    issues = _detect_working_tree_issues(str(tmp_path))

    assert not any(issue.path.startswith(".venv") for issue in issues)


def test_gitignored_directory_is_not_reported(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / ".gitignore").write_text("node_modules/\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg").write_text("pkg\n")

    issues = _detect_working_tree_issues(str(tmp_path))

    assert not any(issue.path.startswith("node_modules") for issue in issues)
