"""Tests for populate-roadmap-from-arch (Step 1-3: catalog / classify / generate_body).

Per skill metadata: version 1.0.

Tests cover:
- catalog_sources: extracts AdrRecord / ArchDocRecord / PhaseRecord from a tmp_path fixture
- classify_adrs_by_phase: maps ADRs to phases based on theme keywords
- generate_phase_body: produces valid markdown with 6 sections + atomic frontmatter preservation
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "populate-roadmap-from-arch" / "scripts"))

from populate_lib import (
    AdrRecord,
    ArchDocRecord,
    PhaseRecord,
    catalog_sources,
    classify_adrs_by_phase,
    generate_phase_body,
)


# ---- Fixtures ----

@pytest.fixture
def project_root_with_adrs(tmp_path):
    """Create a tmp_path project with 4 ADRs + 1 arch doc + main doc + .arch-handoff.json v2."""
    # .arch-handoff.json v2 (ADR-0016)
    handoff_dir = tmp_path / ".rddf" / "state"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / ".arch-handoff.json").write_text(
        '{"version": 2, "adr_dir": "docs/adr", "roadmap_path": ".rddf/roadmap.md", '
        '"architecture_dir": "docs/architecture", "roadmap_fragments_dir": ".rddf/roadmap"}',
        encoding="utf-8",
    )

    # docs/adr/
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "README.md").write_text(
        "| 状态 | ADR |\n|------|-----|\n"
        "| 已实施（v2.0.0+） | ADR-0001, ADR-0002 |\n"
        "| 已实施（v2.0.1+） | ADR-0003 |\n"
        "| 占位（v3.0 候选） | ADR-0099 |",
        encoding="utf-8",
    )
    (adr_dir / "ADR-0001-multi-session.md").write_text(
        "# ADR-0001 多会话管理\n\n## 状态\n\n已采纳\n\n## 关键决策\n\n引入多 session 管理。\n",
        encoding="utf-8",
    )
    (adr_dir / "ADR-0002-design-stage.md").write_text(
        "# ADR-0002 Design 阶段\n\n## 状态\n\n已采纳\n\n## 关键决策\n\n提案审批交互独立成 design 阶段。\n",
        encoding="utf-8",
    )
    (adr_dir / "ADR-0003-execution-mode.md").write_text(
        "# ADR-0003 执行模式\n\n## 状态\n\n已采纳\n\n## 关键决策\n\nplan 阶段决定执行模式。\n",
        encoding="utf-8",
    )
    (adr_dir / "ADR-0099-scheduled-triggers.md").write_text(
        "# ADR-0099 定时循环与事件触发\n\n## 状态\n\n已采纳（v3.0 候选）\n\n## 关键决策\n\n占位 ADR，待 v3.0 实施。\n",
        encoding="utf-8",
    )

    # docs/architecture/
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir(parents=True)
    (arch_dir / "overview.md").write_text(
        "# Overview\n\nThis is the top-level architecture overview for the project.\n",
        encoding="utf-8",
    )

    # .rddf/roadmap.md
    main_doc = tmp_path / ".rddf" / "roadmap.md"
    main_doc.parent.mkdir(parents=True, exist_ok=True)
    main_doc.write_text(
        "# Roadmap\n\n"
        "## Phase Skeleton\n"
        "| Phase | Theme | Status | Started | Done |\n"
        "|-------|-------|--------|---------|------|\n"
        "| phase-1 | 完整多会话支持 | active | | |\n"
        "| phase-1 | 定时循环与事件触发 | active | | |\n"
        "| phase-2 | 审批交互 | active | | |\n"
        "| phase-2 | 编排能力 | active | | |\n"
        "| phase-3 | 流程定制层 | active | | |\n"
        "| phase-4 | 多方对称 | active | | |\n",
        encoding="utf-8",
    )

    # .rddf/roadmap/{phases,features,archive}/
    roadmap_dir = tmp_path / ".rddf" / "roadmap"
    for sub in ("phases", "features", "archive"):
        (roadmap_dir / sub).mkdir(parents=True)
    for phase in ("phase-1", "phase-2", "phase-3", "phase-4"):
        (roadmap_dir / "phases" / f"{phase}.md").write_text(
            f"---\nid: {phase}\nkind: phase\nstatus: active\nphase_refs: []\n主题: TBD\n---\n\n"
            f"## {phase} content (migrated from root roadmap.md)\n",
            encoding="utf-8",
        )

    return tmp_path


# ---- catalog_sources ----

def test_catalog_sources_extracts_adrs(project_root_with_adrs):
    adrs, arch_docs, main_doc_phases = catalog_sources(project_root_with_adrs)

    assert len(adrs) == 4, f"expected 4 ADRs, got {len(adrs)}"
    assert adrs[0].id == "ADR-0001"
    assert "多会话" in adrs[0].title
    assert adrs[0].status == "已采纳"
    assert adrs[0].implementation_version == "v2.0.0+"  # parsed from README 状态段


def test_catalog_sources_marks_placeholder(project_root_with_adrs):
    adrs, _, _ = catalog_sources(project_root_with_adrs)
    placeholder_adr = next(a for a in adrs if a.id == "ADR-0099")
    assert "占位" in placeholder_adr.status or "v3.0" in placeholder_adr.status
    assert placeholder_adr.is_placeholder_or_design() is True


def test_catalog_sources_extracts_arch_docs(project_root_with_adrs):
    _, arch_docs, _ = catalog_sources(project_root_with_adrs)
    assert len(arch_docs) == 1
    assert arch_docs[0].title == "Overview"
    assert "top-level architecture" in arch_docs[0].summary.lower()


def test_catalog_sources_extracts_main_doc_phases(project_root_with_adrs):
    _, _, main_doc_phases = catalog_sources(project_root_with_adrs)
    assert len(main_doc_phases) == 6  # 4 phase-1 + 4 phase-2 + ... wait it's 2+2+1+1 = 6
    phase_ids = {ph.phase_id for ph in main_doc_phases}
    assert phase_ids == {"phase-1", "phase-2", "phase-3", "phase-4"}


# ---- classify_adrs_by_phase ----

def test_classify_adrs_by_phase_phase1_multi_session(project_root_with_adrs):
    adrs, _, main_doc_phases = catalog_sources(project_root_with_adrs)
    classified = classify_adrs_by_phase(adrs, main_doc_phases)

    # ADR-0001 (multi-session) should map to phase-1 (theme: 完整多会话支持)
    phase1_adrs = classified["phase-1"]
    phase1_ids = {a.id for a in phase1_adrs}
    assert "ADR-0001" in phase1_ids


def test_classify_adrs_by_phase_phase2_design(project_root_with_adrs):
    adrs, _, main_doc_phases = catalog_sources(project_root_with_adrs)
    classified = classify_adrs_by_phase(adrs, main_doc_phases)

    # ADR-0002 (design) and ADR-0003 (execution mode / deps) should map to phase-2
    phase2_ids = {a.id for a in classified["phase-2"]}
    assert "ADR-0002" in phase2_ids


def test_classify_adrs_by_phase_placeholder_phase1(project_root_with_adrs):
    """ADR-0099 (占位/定时循环) theme keyword '触发' should match phase-1 '定时循环与事件触发'."""
    adrs, _, main_doc_phases = catalog_sources(project_root_with_adrs)
    classified = classify_adrs_by_phase(adrs, main_doc_phases)

    placeholder = next(a for a in classified["phase-1"] if a.id == "ADR-0099")
    assert placeholder.is_placeholder_or_design() is True


# ---- generate_phase_body ----

def test_generate_phase_body_has_6_sections(project_root_with_adrs):
    adrs, arch_docs, main_doc_phases = catalog_sources(project_root_with_adrs)
    classified = classify_adrs_by_phase(adrs, main_doc_phases)

    body = generate_phase_body(
        phase_id="phase-1",
        classified_adrs=classified,
        arch_docs=arch_docs,
        main_doc_phases=main_doc_phases,
        project_root=project_root_with_adrs,
        next_phase_id="phase-2",
    )

    # Required sections
    assert "## phase-1 概览" in body
    assert "## 已实施能力" in body
    assert "## 架构文档锚点" in body
    assert "## 占位 / 未实施" in body
    assert "## 主题注册表映射" in body
    assert "## 下一步" in body


def test_generate_phase_body_includes_adr_links(project_root_with_adrs):
    adrs, arch_docs, main_doc_phases = catalog_sources(project_root_with_adrs)
    classified = classify_adrs_by_phase(adrs, main_doc_phases)

    body = generate_phase_body(
        phase_id="phase-1",
        classified_adrs=classified,
        arch_docs=arch_docs,
        main_doc_phases=main_doc_phases,
        project_root=project_root_with_adrs,
    )

    # ADR links should be relative paths from fragment (../../docs/adr/...)
    assert "../../docs/adr/ADR-0001-multi-session.md" in body
    # Architecture anchor links
    assert "../../docs/architecture/overview.md" in body


def test_generate_phase_body_placeholder_section_present(project_root_with_adrs):
    adrs, arch_docs, main_doc_phases = catalog_sources(project_root_with_adrs)
    classified = classify_adrs_by_phase(adrs, main_doc_phases)

    body = generate_phase_body(
        phase_id="phase-1",
        classified_adrs=classified,
        arch_docs=arch_docs,
        main_doc_phases=main_doc_phases,
        project_root=project_root_with_adrs,
    )

    # 占位 ADR should appear in "## 占位 / 未实施" section
    assert "## 占位 / 未实施" in body
    assert "ADR-0099" in body
    assert "占位" in body or "未实施" in body


def test_generate_phase_body_final_phase_no_next(project_root_with_adrs):
    adrs, arch_docs, main_doc_phases = catalog_sources(project_root_with_adrs)
    classified = classify_adrs_by_phase(adrs, main_doc_phases)

    body = generate_phase_body(
        phase_id="phase-4",
        classified_adrs=classified,
        arch_docs=arch_docs,
        main_doc_phases=main_doc_phases,
        project_root=project_root_with_adrs,
        next_phase_id=None,
    )

    assert "（本阶段为最终 phase，无下一步）" in body


def test_generate_phase_body_preserves_no_frontmatter(project_root_with_adrs):
    """Body should NOT include --- frontmatter lines (caller adds them)."""
    adrs, arch_docs, main_doc_phases = catalog_sources(project_root_with_adrs)
    classified = classify_adrs_by_phase(adrs, main_doc_phases)

    body = generate_phase_body(
        phase_id="phase-1",
        classified_adrs=classified,
        arch_docs=arch_docs,
        main_doc_phases=main_doc_phases,
        project_root=project_root_with_adrs,
    )

    # No leading frontmatter
    assert not body.startswith("---\n")
    # But should reference 主题 in body if needed
    assert "## phase-1 概览" in body
