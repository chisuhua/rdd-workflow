"""Unit tests for _lib/roadmap_state.py.

Extracted from skills/roadmap/SKILL.md L248-657 — covers init_state,
render_status_view, validate_change, add_phase, advance_phase,
update_roadmap_marker, get_phase_categories, update_change_count.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from skills._lib import roadmap_state


@pytest.fixture
def tmp_roadmap_repo():
    """Create a scratch repo with a minimal roadmap.md + .rddf/state/."""
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp)
        rddf_state = proj / ".rddf" / "state"
        rddf_state.mkdir(parents=True)
        state_file = str(rddf_state / "roadmap-state.json")
        roadmap_file = str(proj / "roadmap.md")
        Path(roadmap_file).write_text(
            "**当前阶段**: phase-1\n\n"
            "### Phase 1: 基础架构 (phase-1)\n"
            "**状态**: ⏳ 未开始\n\n"
            "#### 任务分类\n"
            "| 分类ID | 名称 | 描述 | 优先级 |\n"
            "|--------|------|------|--------|\n"
            "| arch-design | 架构设计 | 系统架构 | P0 |\n"
            "| infra-setup | 基础设施 | CI/CD 等 | P0 |\n"
            "\n### Phase 2: 核心功能 (phase-2)\n"
            "**状态**: ⏳ 未开始\n\n"
            "#### 任务分类\n"
            "| 分类ID | 名称 | 描述 | 优先级 |\n"
            "|--------|------|------|--------|\n"
            "| core-impl | 核心实现 | 主体逻辑 | P0 |\n"
            "\n### Phase 3: 高级特性 (phase-3)\n"
            "**状态**: ⏳ 未开始\n\n"
            "#### 任务分类\n"
            "| 分类ID | 名称 | 描述 | 优先级 |\n"
            "|--------|------|------|--------|\n"
            "| advanced | 高级功能 | 高级业务 | P0 |\n"
        )
        yield {
            "proj": str(proj),
            "state_file": state_file,
            "roadmap_file": roadmap_file,
        }


# ----- init_state -----

def test_init_state_creates_default_3_phase_template(tmp_roadmap_repo):
    state_file = tmp_roadmap_repo["state_file"]
    state = roadmap_state.init_state(state_file)

    assert state["version"] == 1
    assert state["current_phase"] == "phase-1"
    assert set(state["phases"].keys()) == {"phase-1", "phase-2", "phase-3"}
    assert state["phases"]["phase-1"]["status"] == "in_progress"
    assert state["phases"]["phase-2"]["status"] == "pending"
    assert state["phases"]["phase-3"]["status"] == "pending"
    assert os.path.isfile(state_file)

    # Categories preserved from original template
    assert "arch-design" in state["phases"]["phase-1"]["categories"]
    assert "advanced" in state["phases"]["phase-3"]["categories"]

    # Gate checklist (only phase-1 has checks)
    assert "核心接口定义完成" in state["phases"]["phase-1"]["gate_status"]["checklist"]
    assert state["phases"]["phase-2"]["gate_status"]["checklist"] == {}


def test_init_state_idempotent_overwrite(tmp_roadmap_repo):
    """Calling init twice overwrites (matches original behavior)."""
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_state.init_state(state_file)
    roadmap_state.init_state(state_file, current_phase="phase-2")
    with open(state_file) as f:
        state = json.load(f)
    assert state["current_phase"] == "phase-2"


# ----- read_state -----

def test_read_state_returns_empty_dict_when_missing(tmp_roadmap_repo):
    """Empty-dict fallback matches original bash behavior at roadmap.md L348-351."""
    state = roadmap_state.read_state("/nonexistent/path.json")
    assert state == {}


def test_read_state_loads_valid_json(tmp_roadmap_repo):
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_state.init_state(state_file)
    state = roadmap_state.read_state(state_file)
    assert state["current_phase"] == "phase-1"


# ----- render_status_view -----

def test_render_status_view_returns_1_when_roadmap_missing(tmp_roadmap_repo, capsys):
    rc = roadmap_state.render_status_view("/nonexistent/roadmap.md", tmp_roadmap_repo["state_file"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "roadmap.md 不存在" in out
    assert 'skill_use("roadmap", "init")' in out


def test_render_status_view_emits_expected_sections(tmp_roadmap_repo, capsys):
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_file = tmp_roadmap_repo["roadmap_file"]
    roadmap_state.init_state(state_file)

    rc = roadmap_state.render_status_view(roadmap_file, state_file)
    out = capsys.readouterr().out
    assert rc == 0
    assert "📊 路线图状态" in out
    assert "当前阶段: phase-1" in out
    assert "phase-1:" in out
    assert "阶段门控:" in out


# ----- validate_change -----

def test_validate_change_returns_1_when_meta_missing(tmp_roadmap_repo, capsys):
    rc = roadmap_state.validate_change(
        tmp_roadmap_repo["roadmap_file"],
        "/nonexistent/roadmap-meta.yaml",
        "test-change",
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "test-change" in out
    assert "不存在" in out


def test_validate_change_passes_for_valid_change(tmp_roadmap_repo, capsys):
    """Change whose meta references an existing phase+category should validate."""
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_file = tmp_roadmap_repo["roadmap_file"]
    roadmap_state.init_state(state_file)

    change_dir = Path(tmp_roadmap_repo["proj"]) / "openspec" / "changes" / "test-change"
    change_dir.mkdir(parents=True)
    meta_file = str(change_dir / "roadmap-meta.yaml")
    Path(meta_file).write_text(
        "roadmap:\n  phase: phase-1\n  category: arch-design\n"
    )

    rc = roadmap_state.validate_change(roadmap_file, meta_file, "test-change")
    out = capsys.readouterr().out
    assert rc == 0
    assert "test-change" in out
    assert "✅" in out


def test_validate_change_warns_on_unknown_category(tmp_roadmap_repo, capsys):
    """Phase exists but category doesn't → returns 1 + lists valid cats."""
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_file = tmp_roadmap_repo["roadmap_file"]
    roadmap_state.init_state(state_file)

    change_dir = Path(tmp_roadmap_repo["proj"]) / "openspec" / "changes" / "test-change"
    change_dir.mkdir(parents=True)
    meta_file = str(change_dir / "roadmap-meta.yaml")
    Path(meta_file).write_text(
        "roadmap:\n  phase: phase-1\n  category: nonexistent-cat\n"
    )

    rc = roadmap_state.validate_change(roadmap_file, meta_file, "test-change")
    out = capsys.readouterr().out
    assert rc == 1
    assert "不存在" in out or "不在" in out
    assert "arch-design" in out  # valid cat listed


# ----- add_phase -----

def test_add_phase_appends_to_roadmap_and_state(tmp_roadmap_repo, capsys):
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_file = tmp_roadmap_repo["roadmap_file"]
    roadmap_state.init_state(state_file)

    rc = roadmap_state.add_phase(roadmap_file, state_file, "phase-4", "高级扩展", "phase-3")
    assert rc == 0

    # roadmap.md has new section
    content = Path(roadmap_file).read_text()
    assert "### 高级扩展 (phase-4)" in content
    assert "**前置阶段**: phase-3" in content

    # state has new phase
    state = roadmap_state.read_state(state_file)
    assert "phase-4" in state["phases"]
    assert state["phases"]["phase-4"]["status"] == "pending"


def test_add_phase_rejects_empty_ids(tmp_roadmap_repo):
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_file = tmp_roadmap_repo["roadmap_file"]
    rc = roadmap_state.add_phase(roadmap_file, state_file, "", "test", "")
    assert rc == 1


# ----- advance_phase -----

def test_advance_phase_fails_when_no_state(tmp_roadmap_repo, capsys):
    rc = roadmap_state.advance_phase(
        tmp_roadmap_repo["roadmap_file"],
        "/nonexistent/state.json",
    )
    assert rc == 1


def test_advance_phase_fails_when_phase_incomplete(tmp_roadmap_repo, capsys):
    """Pre-check: if no changes are tracked, advance should fail."""
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_file = tmp_roadmap_repo["roadmap_file"]
    roadmap_state.init_state(state_file)

    rc = roadmap_state.advance_phase(roadmap_file, state_file)
    out = capsys.readouterr().out
    assert rc == 1
    assert "未完成" in out or "门控" in out


def test_advance_phase_succeeds_when_complete(tmp_roadmap_repo, capsys):
    """When all changes complete and gate checks satisfied, advance succeeds."""
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_file = tmp_roadmap_repo["roadmap_file"]
    state = roadmap_state.init_state(state_file)

    # Mark phase-1 complete: all changes empty (none to complete) + gate items checked
    phase1 = state["phases"]["phase-1"]
    for cat_id, cat_data in phase1["categories"].items():
        cat_data["completed_changes"] = cat_data.get("changes", [])
    phase1["gate_status"]["all_changes_complete"] = True
    for check in phase1["gate_status"]["checklist"]:
        phase1["gate_status"]["checklist"][check] = True
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

    rc = roadmap_state.advance_phase(roadmap_file, state_file)
    out = capsys.readouterr().out
    assert rc == 0
    assert "已推进" in out
    assert "phase-2" in out

    # State updated
    state = roadmap_state.read_state(state_file)
    assert state["current_phase"] == "phase-2"
    assert state["phases"]["phase-1"]["status"] == "completed"
    assert state["phases"]["phase-2"]["status"] == "in_progress"

    # roadmap.md updated (update_roadmap_marker was folded in)
    content = Path(roadmap_file).read_text()
    assert "**当前阶段**: phase-2" in content


# ----- update_roadmap_marker -----

def test_update_roadmap_marker_replaces_current_phase_line(tmp_roadmap_repo, capsys):
    roadmap_file = tmp_roadmap_repo["roadmap_file"]
    rc = roadmap_state.update_roadmap_marker(roadmap_file, "phase-1", "phase-2")
    assert rc == 0

    content = Path(roadmap_file).read_text()
    assert "**当前阶段**: phase-2" in content
    assert "**当前阶段**: phase-1" not in content.split("\n", 1)[1]


def test_update_roadmap_marker_returns_1_when_roadmap_missing(tmp_roadmap_repo, capsys):
    rc = roadmap_state.update_roadmap_marker("/nonexistent/roadmap.md", "phase-1", "phase-2")
    out = capsys.readouterr().out
    assert rc == 1
    assert "不存在" in out


# ----- get_phase_categories -----

def test_get_phase_categories_prints_cat_lines(tmp_roadmap_repo, capsys):
    roadmap_file = tmp_roadmap_repo["roadmap_file"]
    rc = roadmap_state.get_phase_categories(roadmap_file, "phase-1")
    out = capsys.readouterr().out
    assert rc == 0
    assert "arch-design:架构设计" in out
    assert "infra-setup:基础设施" in out


def test_get_phase_categories_empty_for_unknown_phase(tmp_roadmap_repo, capsys):
    roadmap_file = tmp_roadmap_repo["roadmap_file"]
    rc = roadmap_state.get_phase_categories(roadmap_file, "phase-99")
    out = capsys.readouterr().out
    assert rc == 0
    assert out.strip() == ""


# ----- update_change_count -----

def test_update_change_count_adds_change(tmp_roadmap_repo):
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_state.init_state(state_file)

    rc = roadmap_state.update_change_count(state_file, "new-change", "phase-1", "arch-design", "add")
    assert rc == 0

    state = roadmap_state.read_state(state_file)
    assert "new-change" in state["phases"]["phase-1"]["categories"]["arch-design"]["changes"]


def test_update_change_count_remove_silently_no_ops_unknown(tmp_roadmap_repo):
    """Original behavior: silent no-op if phase/category missing."""
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_state.init_state(state_file)

    rc = roadmap_state.update_change_count(
        state_file, "x", "phase-99", "nope", "add",
    )
    assert rc == 0  # silent success


def test_update_change_count_remove_clears_change(tmp_roadmap_repo):
    state_file = tmp_roadmap_repo["state_file"]
    roadmap_state.init_state(state_file)

    # Add then remove
    roadmap_state.update_change_count(state_file, "c1", "phase-1", "arch-design", "add")
    roadmap_state.update_change_count(state_file, "c1", "phase-1", "arch-design", "remove")

    state = roadmap_state.read_state(state_file)
    assert "c1" not in state["phases"]["phase-1"]["categories"]["arch-design"]["changes"]