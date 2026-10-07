"""Unit tests for _lib/roadmap_md_integrity.py — pure parsing helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from _lib.roadmap_md_integrity import (
    parse_main_doc_table,
    parse_auto_index_segments,
    validate_adr_links,
    validate_index_segment_sync,
)


GOOD_MAIN = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 完整多会话支持 | active | | |
| phase-1 | 定时循环 | active | | |
| phase-2 | 编排能力 | active | | |

<!-- AUTO-INDEX -->

### Phases
- `phase-1` — 完整多会话支持
- `phase-2` — 编排能力

### Features
- `feat-a` — A (refs: phase-1)

### Objectives
- `objective-y` — O

<!-- AUTO-SPRINT-START -->
## Current Sprint
| Project | Phase |
|---------|-------|
| rdd-workflow | phase-1 |
"""


def test_parse_main_doc_table_happy():
    rows = parse_main_doc_table(Path("/tmp/x.md"), GOOD_MAIN)
    assert rows == [
        ("phase-1", "完整多会话支持", "active", "", ""),
        ("phase-1", "定时循环", "active", "", ""),
        ("phase-2", "编排能力", "active", "", ""),
    ]


def test_parse_main_doc_table_bad_columns(tmp_path: Path):
    body = """## Phase Skeleton
| Phase | Theme | Done |
|-------|-------|------|
| phase-1 | T | |
"""
    rows = parse_main_doc_table(tmp_path / "x.md", body)
    assert rows == []  # wrong column count → no parse


def test_parse_auto_index_segments_happy():
    segs = parse_auto_index_segments(GOOD_MAIN)
    assert "Phases" in segs and "Features" in segs and "Objectives" in segs
    assert "phase-1" in segs["Phases"]
    assert "feat-a" in segs["Features"]


def test_parse_auto_index_segments_missing_objectives():
    body = """<!-- AUTO-INDEX -->

### Phases
- `phase-1` — T
"""
    segs = parse_auto_index_segments(body)
    assert "Phases" in segs
    assert "Objectives" not in segs  # missing segment


def test_validate_adr_links_valid(tmp_path: Path):
    adr = tmp_path / "ADR-0010-foo.md"
    adr.write_text("x", encoding="utf-8")
    body = "| T | [ADR-0010](../../docs/adr/{}) | |".format(adr.name)
    findings = validate_adr_links(body, adr_docs_dir=tmp_path)
    assert findings == []


def test_validate_adr_links_broken(tmp_path: Path):
    body = "| T | [ADR-9999](../../docs/adr/ADR-9999-ghost.md) | |"
    findings = validate_adr_links(body, adr_docs_dir=tmp_path)
    assert any("ADR-9999" in f["snippet"] for f in findings)


def test_validate_index_segment_sync_happy(tmp_path: Path):
    """Phases segment + phases dir agree."""
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-1.md").write_text("x", encoding="utf-8")
    segs = {"Phases": {"phase-1"}, "Features": set(), "Objectives": set()}
    findings = validate_index_segment_sync(segs, tmp_path / ".rddf" / "roadmap")
    assert findings == []


def test_validate_index_segment_sync_drift(tmp_path: Path):
    """Disk phase file present but missing from segment → CRITICAL finding dict."""
    segs = {"Phases": set(), "Features": set(), "Objectives": set()}
    findings = validate_index_segment_sync(segs, tmp_path / ".rddf" / "roadmap")
    # No phase files on disk → no drift in either direction
    assert findings == []
    # Now add a phantom on disk (disk has phase-2, seg doesn't)
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-2.md").write_text("x", encoding="utf-8")
    findings = validate_index_segment_sync(segs, tmp_path / ".rddf" / "roadmap")
    assert any("phase-2" in f["snippet"] for f in findings)