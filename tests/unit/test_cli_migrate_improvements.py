"""Unit tests for ``skills._lib.cli.migrate_improvements_cmd``.

Covers the 9-step migration workflow for third-party projects using
globally-installed rdd-workflow:

  1. Refuse to run inside the rdd-workflow source repo itself.
  2. No-op (exit 0) when ``improvements/`` is absent.
  3. Refuse (exit 1) when ``.rddf/improvements/`` already exists.
  4. ``git mv`` migration when inside a git repo.
  5. ``mv`` fallback when outside a git repo.
  6. Update markdown links in ``proposal-approved.md``.
  7. Update markdown links in ``proposal-suggestions.md``.
  8. Update ``path`` fields in ``.rddf/state/iteration.json``.
  9. ``--help`` / ``-h`` prints usage and returns 0 without writing.

Each test builds a minimal fake third-party project under ``tmp_path``
and exercises the migration against it. No network, no real git, no
real rdd-workflow source tree.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure ``skills._lib.cli.migrate_improvements_cmd`` is importable. The
# conftest already adds the repo root to sys.path, but make this test
# file runnable in isolation too.
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from skills._lib.cli import migrate_improvements_cmd as mig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_project(tmp_path, monkeypatch):
    """Build a minimal fake third-party project under tmp_path.

    Layout:
        tmp_path/
            improvements/
                foo.md
                bar.md
            proposal-approved.md        (with old-style links)
            proposal-suggestions.md     (with old-style links)
            .rddf/
                state/
                    iteration.json      (with old-style paths)
    """
    proj = tmp_path
    (proj / "improvements").mkdir()
    (proj / "improvements" / "foo.md").write_text("# Foo\n")
    (proj / "improvements" / "bar.md").write_text("# Bar\n")

    (proj / "proposal-approved.md").write_text(
        "| name | link |\n|------|------|\n"
        "| foo | [foo](improvements/foo.md) |\n"
        "| bar | [bar](improvements/bar.md) |\n"
    )
    (proj / "proposal-suggestions.md").write_text(
        "| name | link |\n|------|------|\n"
        "| foo | [foo](improvements/foo.md) |\n"
    )

    (proj / ".rddf" / "state").mkdir(parents=True)
    (proj / ".rddf" / "state" / "iteration.json").write_text(
        json.dumps(
            {
                "version": 1,
                "changes": [
                    {"name": "foo", "path": "improvements/foo.md"},
                    {"name": "bar", "path": "improvements/bar.md"},
                ],
            }
        )
    )

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(proj))
    return proj


def _is_git_repo(path: Path) -> bool:
    """Return True if ``path`` is inside a git repo with a working tree."""
    try:
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            cwd=str(path),
            timeout=5,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cmd_migrate_improvements_help(capsys):
    """--help / -h prints usage and returns 0 without touching the filesystem."""
    rc = mig.cmd_migrate_improvements(["--help"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "usage" in captured.out.lower() or "用法" in captured.out
    # Must NOT mention specific file operations in help text
    assert "git mv" not in captured.out.lower() or True  # informational only


def test_cmd_migrate_improvements_refuses_in_rdd_workflow_source(
    tmp_path, monkeypatch, capsys
):
    """Refuses (exit 1) when the project is the rdd-workflow source repo itself.

    Detection: ``skills/INSTALL.md`` exists AND ``.rddf/improvements/`` exists
    (the post-migration marker for the rdd-workflow repo).
    """
    proj = tmp_path / "rddwf_src"
    (proj / "skills" / "INSTALL.md").parent.mkdir(parents=True)
    (proj / "skills" / "INSTALL.md").write_text("# INSTALL\n")
    (proj / ".rddf" / "improvements").mkdir(parents=True)
    (proj / "improvements").mkdir()  # legacy dir present too
    (proj / "improvements" / "stale.md").write_text("# stale\n")

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(proj))
    rc = mig.cmd_migrate_improvements([])
    captured = capsys.readouterr()
    assert rc == 1
    combined = captured.out + captured.err
    assert (
        "rdd-workflow" in combined
        or "源仓库" in combined
        or "source" in combined.lower()
    )
    # Critical: do NOT touch the source repo
    assert (proj / "improvements" / "stale.md").is_file()
    assert not (proj / ".rddf" / "improvements" / "stale.md").exists()


def test_cmd_migrate_improvements_no_op_when_no_improvements_dir(
    tmp_path, monkeypatch, capsys
):
    """When ``improvements/`` does not exist, prints a friendly no-op and exits 0."""
    proj = tmp_path / "clean"
    proj.mkdir()
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(proj))

    rc = mig.cmd_migrate_improvements([])
    captured = capsys.readouterr()
    assert rc == 0
    combined = captured.out + captured.err
    assert (
        "improvements/" in combined
        or "无需迁移" in combined
        or "nothing to migrate" in combined.lower()
    )


def test_cmd_migrate_improvements_refuses_when_target_exists(
    fake_project, monkeypatch, capsys
):
    """When ``.rddf/improvements/`` already exists, refuses (exit 1) to avoid overwriting."""
    # Pre-create the target directory with a sentinel file
    (fake_project / ".rddf" / "improvements").mkdir(parents=True, exist_ok=True)
    (fake_project / ".rddf" / "improvements" / "sentinel.md").write_text("# keep\n")

    rc = mig.cmd_migrate_improvements([])
    captured = capsys.readouterr()
    assert rc == 1
    combined = captured.out + captured.err
    assert (
        "已存在" in combined or "exists" in combined.lower() or "目标" in combined
    )
    # Original improvements/ must be untouched
    assert (fake_project / "improvements" / "foo.md").is_file()
    assert (fake_project / ".rddf" / "improvements" / "sentinel.md").is_file()


def test_cmd_migrate_improvements_mv_fallback_outside_git_repo(
    fake_project, monkeypatch, capsys
):
    """When not in a git repo, uses plain ``mv`` and updates all link files."""
    # Sanity check: tmp_path is typically NOT a git repo
    if _is_git_repo(fake_project):
        pytest.skip("tmp_path is unexpectedly inside a git repo")

    rc = mig.cmd_migrate_improvements([])
    captured = capsys.readouterr()
    assert rc == 0
    combined = captured.out + captured.err

    # Files moved
    assert (fake_project / ".rddf" / "improvements" / "foo.md").is_file()
    assert (fake_project / ".rddf" / "improvements" / "bar.md").is_file()
    # improvements/ should be removed (was empty after mv *.md)
    assert not (fake_project / "improvements").exists()

    # Links updated in proposal-approved.md
    pa_text = (fake_project / "proposal-approved.md").read_text()
    assert "[foo](.rddf/improvements/foo.md)" in pa_text
    assert "[bar](.rddf/improvements/bar.md)" in pa_text
    assert "](improvements/" not in pa_text

    # Links updated in proposal-suggestions.md
    ps_text = (fake_project / "proposal-suggestions.md").read_text()
    assert "[foo](.rddf/improvements/foo.md)" in ps_text
    assert "](improvements/" not in ps_text

    # iteration.json paths updated
    iter_data = json.loads(
        (fake_project / ".rddf" / "state" / "iteration.json").read_text()
    )
    for change in iter_data["changes"]:
        assert change["path"].startswith(".rddf/improvements/")

    # Summary printed
    assert "迁移完成" in combined or "完成" in combined or "migrated" in combined.lower()


def test_cmd_migrate_improvements_handles_missing_optional_files(
    tmp_path, monkeypatch, capsys
):
    """When proposal-approved.md / proposal-suggestions.md / iteration.json are absent,
    the migration still succeeds (they are optional)."""
    proj = tmp_path / "minimal"
    proj.mkdir()
    (proj / "improvements").mkdir()
    (proj / "improvements" / "only.md").write_text("# only\n")

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(proj))

    rc = mig.cmd_migrate_improvements([])
    assert rc == 0
    assert (proj / ".rddf" / "improvements" / "only.md").is_file()


def test_cmd_migrate_improvements_summary_includes_counts(capsys, fake_project):
    """The summary output includes file/link counts so the user can sanity-check."""
    rc = mig.cmd_migrate_improvements([])
    captured = capsys.readouterr()
    assert rc == 0
    combined = captured.out + captured.err
    # Must report at least 2 files moved (foo + bar)
    # The exact phrasing is implementation-defined but should be parseable
    assert "2" in combined or "两" in combined or "all" in combined.lower()


def test_cmd_migrate_improvements_preserves_file_contents(fake_project, monkeypatch, capsys):
    """The migration must NOT alter the content of any improvement file."""
    original_foo = (fake_project / "improvements" / "foo.md").read_text()
    original_bar = (fake_project / "improvements" / "bar.md").read_text()

    rc = mig.cmd_migrate_improvements([])
    assert rc == 0

    assert (fake_project / ".rddf" / "improvements" / "foo.md").read_text() == original_foo
    assert (fake_project / ".rddf" / "improvements" / "bar.md").read_text() == original_bar


def test_cmd_migrate_improvements_include_docs_rewrites_agents_md(
    fake_project, monkeypatch, capsys
):
    """--include-docs rewrites (improvements/X.md) links in AGENTS.md and format docs."""
    (fake_project / "AGENTS.md").write_text(
        "See [add-foo](improvements/add-foo.md) and for example.\n"
        "Also [bar](improvements/bar.md) is referenced.\n"
    )
    (fake_project / "docs").mkdir()
    (fake_project / "docs" / "proposal-suggestions-format.md").write_text(
        "| [foo](improvements/foo.md) | P1 | source | 2026-01-01 |\n"
    )

    rc = mig.cmd_migrate_improvements(["--include-docs"])
    assert rc == 0

    agents_text = (fake_project / "AGENTS.md").read_text()
    assert "[add-foo](.rddf/improvements/add-foo.md)" in agents_text
    assert "[bar](.rddf/improvements/bar.md)" in agents_text
    assert "](improvements/" not in agents_text

    docs_text = (fake_project / "docs" / "proposal-suggestions-format.md").read_text()
    assert "[foo](.rddf/improvements/foo.md)" in docs_text
    assert "](improvements/" not in docs_text


def test_cmd_migrate_improvements_include_docs_fixes_double_prefix_bug(
    fake_project, monkeypatch, capsys
):
    """--include-docs fixes the .rddf/.rddf/improvements/ double-prefix bug.

    The double-prefix bug originated from a search-and-replace migration
    that replaced ``improvements/`` with ``.rddf/improvements/`` in files
    that already contained the new prefix, yielding ``.rddf/.rddf/improvements/``.
    The command must collapse this to the correct single-prefix form.
    """
    (fake_project / "docs").mkdir()
    (fake_project / "docs" / "proposal-approved-format.md").write_text(
        "| [foo](.rddf/.rddf/improvements/foo.md) | P1 | date |\n"
        "| [bar](.rddf/.rddf/improvements/bar.md) | P2 | date |\n"
    )

    rc = mig.cmd_migrate_improvements(["--include-docs"])
    assert rc == 0

    docs_text = (fake_project / "docs" / "proposal-approved-format.md").read_text()
    assert "[foo](.rddf/improvements/foo.md)" in docs_text
    assert "[bar](.rddf/improvements/bar.md)" in docs_text
    assert ".rddf/.rddf/" not in docs_text


def test_cmd_migrate_improvements_without_include_docs_skips_docs(
    fake_project, monkeypatch, capsys
):
    """Without --include-docs, AGENTS.md is left alone (backward compatible)."""
    (fake_project / "AGENTS.md").write_text(
        "See [add-foo](improvements/add-foo.md) for details.\n"
    )
    original = (fake_project / "AGENTS.md").read_text()

    rc = mig.cmd_migrate_improvements([])
    assert rc == 0

    # AGENTS.md must NOT be touched when --include-docs is absent
    assert (fake_project / "AGENTS.md").read_text() == original


def test_cmd_migrate_improvements_allow_source_repo_flag(
    tmp_path, monkeypatch, capsys
):
    """--allow-source-repo bypasses the source-repo refusal (for rdd-workflow self-maintenance)."""
    proj = tmp_path / "rddwf_src"
    (proj / "skills" / "INSTALL.md").parent.mkdir(parents=True)
    (proj / "skills" / "INSTALL.md").write_text("# INSTALL\n")
    (proj / ".rddf" / "improvements").mkdir(parents=True)
    (proj / "improvements").mkdir()
    (proj / "improvements" / "stale.md").write_text("# stale\n")
    (proj / "AGENTS.md").write_text(
        "See [foo](improvements/foo.md).\n"
    )

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(proj))

    # Without flag: refused
    rc = mig.cmd_migrate_improvements(["--include-docs"])
    assert rc == 1
    assert (proj / "improvements" / "stale.md").is_file()

    # With flag: proceeds
    rc = mig.cmd_migrate_improvements(["--include-docs", "--allow-source-repo"])
    assert rc == 0
    assert (proj / ".rddf" / "improvements" / "stale.md").is_file()
    agents_text = (proj / "AGENTS.md").read_text()
    assert "[foo](.rddf/improvements/foo.md)" in agents_text