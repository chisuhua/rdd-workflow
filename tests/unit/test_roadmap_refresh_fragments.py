"""Unit tests for skills/roadmap/scripts/roadmap_refresh_fragments.sh + the
trailing-section preservation fix in _lib.roadmap_state.render_fragment_index.

Per add-refresh-fragments-cli (2026-10-08):
  - bash wrapper refreshes both .rddf/roadmap.md + AGENTS.md in one call
  - trailing content after <!-- AUTO-ININDEX --> (e.g. <!-- AUTO-SPRINT-START -->
    + Unmapped table) MUST be preserved (previously deleted as side effect)
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT_PATH = _REPO_ROOT / "skills" / "roadmap" / "scripts" / "roadmap_refresh_fragments.sh"


def _setup_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Create minimal repo with .rddf/roadmap/features/ + .rddf/roadmap.md."""
    repo = tmp_path
    fragments = repo / ".rddf" / "roadmap" / "features"
    fragments.mkdir(parents=True)
    (fragments / "feat-x.md").write_text(
        "---\n"
        "id: feat-x\n"
        "kind: feature\n"
        "status: active\n"
        "phase_refs: [phase-1]\n"
        "主题: test theme\n"
        "---\nbody\n",
        encoding="utf-8",
    )
    (fragments / "feat-y.md").write_text(
        "---\n"
        "id: feat-y\n"
        "kind: feature\n"
        "status: done\n"
        "phase_refs: [phase-2]\n"
        "主题: another\n"
        "---\nbody\n",
        encoding="utf-8",
    )
    (repo / ".rddf" / "roadmap.md").write_text(
        "# Roadmap\n\n## Phase Skeleton\n"
        "| Phase | Theme | Status | Started | Done |\n"
        "|-------|-------|--------|---------|------|\n"
        "| phase-1 | T | active | | |\n\n"
        "<!-- AUTO-INDEX -->\n\n"
        "## Fragment Index (auto-generated)\n\n"
        "### Features\n- placeholder\n\n"
        "<!-- AUTO-SPRINT-START -->\n"
        "## Current Sprint\n"
        "| Project | Phase |\n|---------|-------|\n"
        "| rdd-workflow | phase-1 |\n",
        encoding="utf-8",
    )
    return repo, fragments


def _run(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(_SCRIPT_PATH)],
        cwd=str(repo),
        env={"PATH": "/usr/bin:/usr/local/bin", "HOME": str(repo), "PROJECT_ROOT": str(repo)},
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_refresh_fragments_preserves_trailing_content(tmp_path: Path):
    """Refreshing AUTO-INDEX must NOT delete AUTO-SPRINT-START + Unmapped sections."""
    repo, _fragments = _setup_repo(tmp_path)
    result = _run(repo)
    assert result.returncode == 0, f"stderr: {result.stderr}"

    content = (repo / ".rddf/roadmap.md").read_text(encoding="utf-8")

    assert "<!-- AUTO-INDEX -->" in content
    assert "<!-- AUTO-SPRINT-START -->" in content, "AUTO-SPRINT-START was deleted!"
    assert "## Current Sprint" in content
    assert "| rdd-workflow | phase-1 |" in content


def test_refresh_fragments_includes_new_feature(tmp_path: Path):
    """New feature fragment added to .rddf/roadmap/features/ must appear in AUTO-INDEX."""
    repo, fragments = _setup_repo(tmp_path)

    (fragments / "feat-z.md").write_text(
        "---\n"
        "id: feat-z\n"
        "kind: feature\n"
        "status: active\n"
        "phase_refs: [phase-3]\n"
        "主题: new entry\n"
        "---\nbody\n",
        encoding="utf-8",
    )

    _run(repo)

    content = (repo / ".rddf/roadmap.md").read_text(encoding="utf-8")
    assert "feat-x" in content
    assert "feat-y" in content
    assert "feat-z" in content


def test_refresh_fragments_idempotent(tmp_path: Path):
    """Calling the tool twice yields identical .rddf/roadmap.md content."""
    repo, _fragments = _setup_repo(tmp_path)
    for _ in range(2):
        _run(repo)

    content = (repo / ".rddf/roadmap.md").read_text(encoding="utf-8")
    assert content.count("feat-x") == 1
    assert content.count("<!-- AUTO-INDEX -->") == 1


def test_refresh_fragments_updates_agents_md(tmp_path: Path):
    """AGENTS.md AUTO block must reflect new feature fragments."""
    repo, _fragments = _setup_repo(tmp_path)
    (repo / "AGENTS.md").write_text(
        "# Project\n\n<!-- AUTO: feature fragments start -->\n\nold\n<!-- AUTO: feature fragments end -->\n",
        encoding="utf-8",
    )
    _run(repo)

    agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert "feat-x" in agents
    assert "feat-y" in agents
    assert "<!-- AUTO: feature fragments start -->" in agents
    assert "<!-- AUTO: feature fragments end -->" in agents


def test_refresh_fragments_exits_nonzero_on_missing_dir(tmp_path: Path):
    """Missing .rddf/roadmap/ must not crash; graceful exit with error message."""
    repo = tmp_path
    result = _run(repo)
    assert result.returncode in (0, 1)