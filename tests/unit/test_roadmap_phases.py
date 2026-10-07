"""Unit tests for skills/rdd-doctor/scripts/checks/roadmap_phases_check.py."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from checks.roadmap_phases_check import run  # noqa: E402


def _setup_repo(tmp_path: Path, *, phase_files: dict[str, str], main_doc: str) -> Path:
    """Create a minimal repo with phases/*.md + .rddf/roadmap.md under tmp_path."""
    repo = tmp_path
    phases_dir = repo / ".rddf" / "roadmap" / "phases"
    phases_dir.mkdir(parents=True, exist_ok=True)
    for name, body in phase_files.items():
        (phases_dir / name).write_text(body, encoding="utf-8")
    (repo / ".rddf").mkdir(exist_ok=True)
    (repo / ".rddf" / "roadmap.md").write_text(main_doc, encoding="utf-8")
    return repo


def test_roadmap_phases_happy(tmp_path: Path):
    """All phases present, frontmatter complete, AUTO-INDEX matches."""
    main_doc = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 提案生成 | active | | |
| phase-2 | 阶段步骤化 | active | | |

<!-- AUTO-INDEX -->

### Phases
- `phase-1` — 提案生成
- `phase-2` — 阶段步骤化
"""
    repo = _setup_repo(tmp_path, phase_files={
        "phase-1.md": "---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n主题: 提案生成\n---\nbody\n",
        "phase-2.md": "---\nid: phase-2\nkind: phase\nstatus: active\nphase_refs: []\n主题: 阶段步骤化\n---\nbody\n",
    }, main_doc=main_doc)
    findings = run(project_root=repo)
    assert findings == [], f"expected clean, got: {findings}"


def test_roadmap_phases_missing_frontmatter_field(tmp_path: Path):
    """Phase file missing 'status' field → CRITICAL."""
    main_doc = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 提案生成 | active | | |

<!-- AUTO-INDEX -->

### Phases
- `phase-1` — 提案生成
"""
    repo = _setup_repo(tmp_path, phase_files={
        "phase-1.md": "---\nid: phase-1\nkind: phase\nphase_refs: []\n主题: 提案生成\n---\nbody\n",
    }, main_doc=main_doc)
    findings = run(project_root=repo)
    assert any(f.severity == Severity.CRITICAL and "status" in f.snippet for f in findings), \
        f"expected CRITICAL missing-status, got: {findings}"


def test_roadmap_phases_auto_index_drift(tmp_path: Path):
    """Phase file on disk but missing from AUTO-INDEX → CRITICAL."""
    main_doc = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | T | active | | |

<!-- AUTO-INDEX -->

### Phases
"""
    repo = _setup_repo(tmp_path, phase_files={
        "phase-1.md": "---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n主题: T\n---\nbody\n",
    }, main_doc=main_doc)
    findings = run(project_root=repo)
    assert any(f.severity == Severity.CRITICAL and "phase-1" in f.snippet for f in findings), \
        f"expected CRITICAL AUTO-INDEX drift, got: {findings}"


def test_roadmap_phases_main_doc_missing(tmp_path: Path):
    """Phase referenced in main doc but no phase file → CRITICAL."""
    main_doc = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-99 | T | active | | |

<!-- AUTO-INDEX -->

### Phases
- `phase-99` — phantom
"""
    repo = _setup_repo(tmp_path, phase_files={}, main_doc=main_doc)
    findings = run(project_root=repo)
    assert any(f.severity == Severity.CRITICAL and "phase-99" in f.snippet for f in findings), \
        f"expected CRITICAL main-doc missing phase-99, got: {findings}"