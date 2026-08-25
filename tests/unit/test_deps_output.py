"""Unit tests for _lib/deps_output.py — structured deps analysis."""
import json
import os
from pathlib import Path
import pytest

from skills.deps.scripts import deps_output as do
from skills._lib import iteration as it


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path):
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    return str(tmp_path)


# ---------------------------------------------------------------------------
# build_analysis
# ---------------------------------------------------------------------------

class TestBuildAnalysis:
    def test_minimal_record(self):
        out = do.build_analysis([{"name": "c1"}])
        assert out["version"] == 1
        assert out["fallback"] is True  # default
        assert "c1" in out["changes"]
        c = out["changes"]["c1"]
        assert c["status"] == "ready"
        assert c["parallel_group"] == 0
        assert c["blocker"] is None
        assert c["blocks"] == []
        assert c["conflicts"] == []
        assert c["confidence"] == "high"

    def test_full_record(self):
        out = do.build_analysis([{
            "name": "c2",
            "phase": "v2.1",
            "category": "loop-engine",
            "status": "blocked_by",
            "blocker": "c1",
            "blocks": ["c3"],
            "parallel_group": 2,
            "conflicts": ["c4"],
            "confidence": "low",
            "recommendation": "等 c1 完成后",
        }])
        c = out["changes"]["c2"]
        assert c["phase"] == "v2.1"
        assert c["category"] == "loop-engine"
        assert c["blocker"] == "c1"
        assert c["blocks"] == ["c3"]
        assert c["parallel_group"] == 2
        assert c["conflicts"] == ["c4"]
        assert c["confidence"] == "low"
        assert c["recommendation"] == "等 c1 完成后"

    def test_execution_order_default_is_input_order(self):
        out = do.build_analysis([
            {"name": "c1"},
            {"name": "c2"},
            {"name": "c3"},
        ])
        assert out["execution_order"] == ["c1", "c2", "c3"]

    def test_execution_order_filtered_to_known(self):
        out = do.build_analysis(
            [{"name": "c1"}, {"name": "c2"}],
            execution_order=["c1", "ghost", "c2"],
        )
        assert out["execution_order"] == ["c1", "c2"]

    def test_fallback_flag(self):
        out_full = do.build_analysis([{"name": "c1"}], fallback=False)
        out_fallback = do.build_analysis([{"name": "c1"}], fallback=True)
        assert out_full["fallback"] is False
        assert out_fallback["fallback"] is True

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="requires 'name'"):
            do.build_analysis([{"phase": "v2.1"}])

    def test_blocks_is_list_copy(self):
        """Mutating the input must not affect the stored analysis."""
        blocks = ["c2"]
        out = do.build_analysis([{"name": "c1", "blocks": blocks}])
        blocks.append("c3")
        assert out["changes"]["c1"]["blocks"] == ["c2"]  # not affected

    def test_conflicts_is_list_copy(self):
        conflicts = ["c2"]
        out = do.build_analysis([{"name": "c1", "conflicts": conflicts}])
        conflicts.append("c3")
        assert out["changes"]["c1"]["conflicts"] == ["c2"]


# ---------------------------------------------------------------------------
# write_analysis / load_analysis
# ---------------------------------------------------------------------------

class TestWriteLoadAnalysis:
    def test_write_creates_file(self, project_root):
        data = do.build_analysis([{"name": "c1"}])
        path = do.write_analysis(project_root, data)
        assert os.path.isfile(path)

    def test_load_returns_data(self, project_root):
        data = do.build_analysis([{"name": "c1", "blocker": "c0"}])
        do.write_analysis(project_root, data)
        loaded = do.load_analysis(project_root)
        assert loaded is not None
        assert loaded["changes"]["c1"]["blocker"] == "c0"

    def test_load_missing_returns_none(self, project_root):
        assert do.load_analysis(project_root) is None

    def test_load_corrupt_json_returns_none(self, project_root):
        path = os.path.join(project_root, do.ANALYSIS_PATH_TEMPLATE)
        with open(path, "w") as f:
            f.write("{ not valid json")
        assert do.load_analysis(project_root) is None

    def test_load_wrong_version_returns_none(self, project_root):
        path = os.path.join(project_root, do.ANALYSIS_PATH_TEMPLATE)
        with open(path, "w") as f:
            json.dump({"version": 999, "changes": {}}, f)
        assert do.load_analysis(project_root) is None

    def test_load_missing_changes_field_returns_none(self, project_root):
        path = os.path.join(project_root, do.ANALYSIS_PATH_TEMPLATE)
        with open(path, "w") as f:
            json.dump({"version": 1, "updated_at": "x", "fallback": False, "execution_order": []}, f)
        assert do.load_analysis(project_root) is None

    def test_atomic_write_no_tmp_left(self, project_root):
        data = do.build_analysis([{"name": "c1"}])
        do.write_analysis(project_root, data)
        path = os.path.join(project_root, do.ANALYSIS_PATH_TEMPLATE)
        assert not os.path.exists(path + ".tmp")


# ---------------------------------------------------------------------------
# sync_iteration_from_analysis
# ---------------------------------------------------------------------------

class TestSyncIterationFromAnalysis:
    def test_no_analysis_file_noop(self, project_root):
        """When deps-analysis.json doesn't exist, return 0 and don't touch iteration."""
        # Seed iteration with a change
        data = it.add_or_update_change(it.create_empty(), name="c1", status="proposed")
        it.save(project_root, data)

        count = do.sync_iteration_from_analysis(project_root, it)
        assert count == 0
        # iteration.json untouched
        loaded = it.load(project_root)
        assert loaded["changes"][0]["name"] == "c1"
        assert "blocker" not in loaded["changes"][0]

    def test_syncs_blocker_and_group(self, project_root):
        data = it.add_or_update_change(it.create_empty(), name="c1", status="proposed")
        it.save(project_root, data)

        analysis = do.build_analysis([
            {"name": "c1", "blocker": "c0", "parallel_group": 2, "conflicts": ["c2"]},
        ])
        do.write_analysis(project_root, analysis)

        count = do.sync_iteration_from_analysis(project_root, it)
        assert count == 1

        loaded = it.load(project_root)
        c = loaded["changes"][0]
        assert c["name"] == "c1"
        assert c["blocker"] == "c0"
        assert c["parallel_group"] == 2
        assert c["conflicts"] == ["c2"]
        assert c["last_deps_at"]  # timestamp recorded

    def test_syncs_multiple_changes(self, project_root):
        data = it.add_or_update_change(it.create_empty(), name="c1", status="proposed")
        data = it.add_or_update_change(data, name="c2", status="proposed")
        it.save(project_root, data)

        analysis = do.build_analysis([
            {"name": "c1", "blocker": None, "parallel_group": 0},
            {"name": "c2", "blocker": "c1", "parallel_group": 1},
        ])
        do.write_analysis(project_root, analysis)

        count = do.sync_iteration_from_analysis(project_root, it)
        assert count == 2

        loaded = it.load(project_root)
        by_name = {c["name"]: c for c in loaded["changes"]}
        assert by_name["c1"]["blocker"] is None
        assert by_name["c1"]["parallel_group"] == 0
        assert by_name["c2"]["blocker"] == "c1"
        assert by_name["c2"]["parallel_group"] == 1

    def test_creates_entry_for_new_change(self, project_root):
        """deps may surface a change that isn't in iteration.json yet.

        P0 fix-iteration-phantom-from-deps (2026-08-25): deps is now
        skip-on-missing — it does NOT auto-create lifecycle entries.
        propose.md owns lifecycle creation; deps only updates metadata
        for entries that already exist. Surfaced names that haven't been
        proposed via OpenSpec CLI must trigger a separate propose step,
        not phantom creation here.

        This test now verifies that the skip behavior preserves the
        empty state and returns count=0 (nothing actually written).
        """
        data = it.create_empty()  # empty
        it.save(project_root, data)

        analysis = do.build_analysis([{"name": "c-new", "blocker": None}])
        do.write_analysis(project_root, analysis)

        count = do.sync_iteration_from_analysis(project_root, it)
        # Skip-on-missing: count is 0 (no entry was actually updated)
        assert count == 0

        loaded = it.load(project_root)
        names = [c["name"] for c in loaded["changes"]]
        # No phantom entry created
        assert "c-new" not in names

    def test_preserves_iteration_status(self, project_root):
        """set_deps_info must NOT change the lifecycle status (it only updates deps metadata)."""
        data = it.add_or_update_change(it.create_empty(), name="c1", status="in_worktree")
        it.save(project_root, data)

        analysis = do.build_analysis([{"name": "c1", "blocker": None}])
        do.write_analysis(project_root, analysis)
        do.sync_iteration_from_analysis(project_root, it)

        loaded = it.load(project_root)
        assert loaded["changes"][0]["status"] == "in_worktree"


# ---------------------------------------------------------------------------
# parse_markdown_fallback (P3-4d: extracted from deps.md Step 6 inline heredoc)
# ---------------------------------------------------------------------------

class TestParseMarkdownFallback:
    """Parse the .deps-output.md human-readable report and extract change
    deps info. Returns a dict suitable for build_analysis() (list of change
    records with name/blocker/blocks/parallel_group/conflicts/confidence).
    Returns None when the file is missing, malformed, or has no Change table.
    """

    def _write_deps_output(self, project_root, content):
        path = Path(project_root) / ".rddf" / "state" / ".deps-output.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_missing_file_returns_none(self, project_root):
        result = do.parse_markdown_fallback(project_root)
        assert result is None

    def test_no_change_table_returns_none(self, project_root):
        self._write_deps_output(project_root, "# Empty report\n\nNo data here.\n")
        assert do.parse_markdown_fallback(project_root) is None

    def test_parses_status_table_with_no_blocker(self, project_root):
        md = """# Deps Report

## Change 状态表

| Change | Status | Blocker | Parallel Group | Conflicts |
|--------|--------|---------|----------------|-----------|
| c1 | ready | — | 0 | — |
| c2 | ready | — | 0 | — |
"""
        self._write_deps_output(project_root, md)
        result = do.parse_markdown_fallback(project_root)
        assert result is not None
        changes = {c["name"]: c for c in result}
        assert changes["c1"]["blocker"] is None
        assert changes["c1"]["parallel_group"] == 0
        assert changes["c1"]["conflicts"] == []
        assert changes["c1"]["status"] == "ready"
        assert changes["c2"]["parallel_group"] == 0

    def test_parses_blocker_chain_assigns_increasing_parallel_group(self, project_root):
        md = """## Change 状态表

| Change | Status | Blocker | Parallel Group | Conflicts |
|--------|--------|---------|----------------|-----------|
| c1 | blocked | c2 | — | — |
| c2 | blocked | c3 | — | — |
| c3 | ready | — | — | — |
"""
        self._write_deps_output(project_root, md)
        result = do.parse_markdown_fallback(project_root)
        changes = {c["name"]: c for c in result}
        assert changes["c1"]["blocker"] == "c2"
        assert changes["c1"]["status"] == "blocked_by"
        # Items with blockers get sequential parallel_group by table position
        assert changes["c1"]["parallel_group"] == 0
        assert changes["c2"]["parallel_group"] == 1
        # No blocker → group 0
        assert changes["c3"]["parallel_group"] == 0

    def test_parses_conflicts_section(self, project_root):
        md = """## Change 状态表

| Change | Status | Blocker | Parallel Group | Conflicts |
|--------|--------|---------|----------------|-----------|
| c1 | ready | — | 0 | — |
| c2 | ready | — | 0 | — |

## 冲突警告

c1 ←→ c2: shared file src/api.py
"""
        self._write_deps_output(project_root, md)
        result = do.parse_markdown_fallback(project_root)
        changes = {c["name"]: c for c in result}
        assert "c2" in changes["c1"]["conflicts"]
        assert "c1" in changes["c2"]["conflicts"]

    def test_conflicts_section_adds_changes_not_in_status_table(self, project_root):
        md = """## Change 状态表

| Change | Status | Blocker | Parallel Group | Conflicts |
|--------|--------|---------|----------------|-----------|
| c1 | ready | — | 0 | — |

## 冲突警告

c1 ←→ c2: shared file src/api.py
"""
        self._write_deps_output(project_root, md)
        result = do.parse_markdown_fallback(project_root)
        names = sorted(c["name"] for c in result)
        assert names == ["c1", "c2"]
        changes = {c["name"]: c for c in result}
        assert changes["c2"]["blocker"] is None
        assert changes["c2"]["parallel_group"] == 0

    def test_returns_changes_with_low_confidence(self, project_root):
        """Markdown fallback must be tagged low confidence (P3-4d)."""
        md = """## Change 状态表

| Change | Status | Blocker | Parallel Group | Conflicts |
|--------|--------|---------|----------------|-----------|
| c1 | ready | — | 0 | — |
"""
        self._write_deps_output(project_root, md)
        result = do.parse_markdown_fallback(project_root)
        assert result[0]["confidence"] == "low"

    def test_skips_empty_or_dash_rows_in_status_table(self, project_root):
        md = """## Change 状态表

| Change | Status | Blocker | Parallel Group | Conflicts |
|--------|--------|---------|----------------|-----------|
| — | — | — | — | — |
| c1 | ready | — | 0 | — |
"""
        self._write_deps_output(project_root, md)
        result = do.parse_markdown_fallback(project_root)
        names = [c["name"] for c in result]
        assert "c1" in names
        assert "—" not in names
        assert "" not in names

    def test_blocker_with_dash_treated_as_none(self, project_root):
        md = """## Change 状态表

| Change | Status | Blocker | Parallel Group | Conflicts |
|--------|--------|---------|----------------|-----------|
| c1 | ready | — | 0 | — |
| c2 | ready | — | 0 | — |
"""
        self._write_deps_output(project_root, md)
        result = do.parse_markdown_fallback(project_root)
        changes = {c["name"]: c for c in result}
        for name in ("c1", "c2"):
            assert changes[name]["blocker"] is None
            assert changes[name]["status"] == "ready"


# ---------------------------------------------------------------------------
# execution_mode_recommendations (ADR-0023)
# ---------------------------------------------------------------------------

class TestExecutionModeRecommendations:
    """Tests for analyze_execution_mode() and compute_execution_mode_recommendations()."""

    def test_analyze_small_change_recommends_lightweight(self, tmp_path):
        from skills.deps.scripts.deps_output import analyze_execution_mode
        change_dir = tmp_path / "openspec" / "changes" / "test-small"
        change_dir.mkdir(parents=True)
        (change_dir / "design.md").write_text("- Modify: src/main.py\n")
        (change_dir / "tasks.md").write_text("- [ ] task 1\n- [ ] task 2\n")
        (change_dir / "proposal.md").write_text("simple fix\n")

        result = analyze_execution_mode("test-small", str(tmp_path))
        assert result["mode"] == "lightweight", f"expected lightweight, got {result['mode']}"
        assert result["details"]["change_size"] == "small"

    def test_analyze_large_change_recommends_worktree(self, tmp_path):
        from skills.deps.scripts.deps_output import analyze_execution_mode
        change_dir = tmp_path / "openspec" / "changes" / "test-large"
        change_dir.mkdir(parents=True)
        (change_dir / "design.md").write_text(
            "- Modify: src/a.py\n- Modify: src/b.py\n- Modify: src/c.py\n"
            "- Modify: src/d.py\n- Modify: src/e.py\n- Modify: src/f.py\n"
        )
        (change_dir / "tasks.md").write_text("\n".join(f"- [ ] task {i}" for i in range(7)) + "\n")
        (change_dir / "proposal.md").write_text("large refactor\n")

        result = analyze_execution_mode("test-large", str(tmp_path))
        assert result["mode"] == "worktree", f"expected worktree, got {result['mode']}"
        assert result["details"]["change_size"] == "large"

    def test_analyze_risky_keyword_forces_worktree(self, tmp_path):
        from skills.deps.scripts.deps_output import analyze_execution_mode
        change_dir = tmp_path / "openspec" / "changes" / "test-risky"
        change_dir.mkdir(parents=True)
        (change_dir / "design.md").write_text("- Modify: src/main.py\n")
        (change_dir / "tasks.md").write_text("- [ ] task 1\n")
        (change_dir / "proposal.md").write_text("refactor the entire module\n")

        result = analyze_execution_mode("test-risky", str(tmp_path))
        assert result["mode"] == "worktree", f"expected worktree for risky, got {result['mode']}"
        assert result["details"]["is_risky"] is True

    def test_analyze_medium_change_defaults_lightweight(self, tmp_path):
        from skills.deps.scripts.deps_output import analyze_execution_mode
        change_dir = tmp_path / "openspec" / "changes" / "test-medium"
        change_dir.mkdir(parents=True)
        (change_dir / "design.md").write_text(
            "- Modify: src/a.py\n- Modify: src/b.py\n- Modify: src/c.py\n"
        )
        (change_dir / "tasks.md").write_text(
            "- [ ] task 1\n- [ ] task 2\n- [ ] task 3\n- [ ] task 4\n"
        )
        (change_dir / "proposal.md").write_text("feature addition\n")

        result = analyze_execution_mode("test-medium", str(tmp_path))
        assert result["mode"] == "lightweight"
        assert result["details"]["change_size"] == "medium"

    def test_compute_recommendations_with_conflicts_forces_worktree(self, tmp_path):
        from skills.deps.scripts.deps_output import compute_execution_mode_recommendations
        change_dir = tmp_path / "openspec" / "changes" / "c1"
        change_dir.mkdir(parents=True)
        (change_dir / "design.md").write_text("- Modify: src/main.py\n")
        (change_dir / "tasks.md").write_text("- [ ] task 1\n")
        (change_dir / "proposal.md").write_text("simple fix\n")

        changes = [{"name": "c1", "conflicts": ["c2"]}]
        recs = compute_execution_mode_recommendations(changes, str(tmp_path))
        assert recs["c1"]["mode"] == "worktree", "conflicts should force worktree"

    def test_build_analysis_includes_recommendations_with_project_root(self, tmp_path):
        from skills.deps.scripts.deps_output import build_analysis
        change_dir = tmp_path / "openspec" / "changes" / "c1"
        change_dir.mkdir(parents=True)
        (change_dir / "design.md").write_text("- Modify: src/main.py\n")
        (change_dir / "tasks.md").write_text("- [ ] task 1\n")
        (change_dir / "proposal.md").write_text("simple fix\n")

        result = build_analysis([{"name": "c1"}], project_root=str(tmp_path))
        assert "execution_mode_recommendations" in result
        assert result["execution_mode_recommendations"]["c1"]["mode"] == "lightweight"


# ---------------------------------------------------------------------------
# render_markdown_report (P3-4e: extracted from deps.md Step 5 lines 483-642)
# ---------------------------------------------------------------------------

class TestRenderMarkdownReport:
    """render_markdown_report encapsulates deps.md Step 5 (lines 483-642,
    160-line inline bash block). Generates complete markdown report with:
    - Header + candidate count
    - Mermaid dependency graph
    - Phase precheck table
    - Change status table
    - Recommended execution order
    - Conflict warnings (placeholder)
    - AI analysis suggestions (or fallback message)

    Returns full markdown as a string. Caller writes to file.
    """

    def test_returns_header_with_candidate_count(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        out = do.render_markdown_report(
            candidates=["c1", "c2", "c3"],
            project_root=str(tmp_path),
        )
        assert "# 依赖分析报告" in out
        assert "候选 changes: 3" in out

    def test_includes_mermaid_flowchart_with_all_nodes(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        out = do.render_markdown_report(
            candidates=["c1", "c2"],
            project_root=str(tmp_path),
        )
        assert "```mermaid" in out
        assert "flowchart LR" in out
        # c1 and c2 should appear as nodes
        assert "c1" in out
        assert "c2" in out

    def test_marks_skeleton_changes_with_double_brackets(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        # c1 has design.md (full), c2 doesn't (skeleton)
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        (tmp_path / "openspec" / "changes" / "c1" / "design.md").write_text("# design")
        (tmp_path / "openspec" / "changes" / "c2").mkdir(parents=True)
        out = do.render_markdown_report(
            candidates=["c1", "c2"],
            project_root=str(tmp_path),
        )
        # c1 should have normal brackets [c1]
        assert "c1[c1]" in out
        # c2 should have double brackets [[c2]] (skeleton marker)
        assert "c2[[c2]]" in out

    def test_phase_precheck_table_within_current_phase(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        # c1 has roadmap-meta.yaml with phase=phase-1, matches ROADMAP_CURRENT_PHASE
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        (tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml").write_text(
            'roadmap:\n  phase: "phase-1"\n  category: "general"\n'
        )
        out = do.render_markdown_report(
            candidates=["c1"],
            project_root=str(tmp_path),
            roadmap_current_phase="phase-1",
        )
        assert "## 阶段预检" in out
        assert "| c1 | phase-1 | general | ✅ 在阶段内 |" in out

    def test_phase_precheck_marks_out_of_phase_change(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        # c1 has phase=phase-2, but current is phase-1
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        (tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml").write_text(
            'roadmap:\n  phase: "phase-2"\n  category: "core-impl"\n'
        )
        out = do.render_markdown_report(
            candidates=["c1"],
            project_root=str(tmp_path),
            roadmap_current_phase="phase-1",
        )
        assert "| c1 | phase-2 | core-impl | ⚠️ 不在当前阶段 (phase-1) |" in out

    def test_phase_precheck_marks_missing_roadmap_meta_as_compat(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        # No roadmap-meta.yaml
        out = do.render_markdown_report(
            candidates=["c1"],
            project_root=str(tmp_path),
            roadmap_current_phase="phase-1",
        )
        assert "| c1 | (compat) | (compat) | ⚠️ 无 roadmap-meta |" in out

    def test_change_status_table_shows_ready_when_no_ai_blocker(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        out = do.render_markdown_report(
            candidates=["c1"],
            project_root=str(tmp_path),
            ai_result_file=None,  # No AI result
        )
        assert "## Change 状态表" in out
        assert "| c1 | ✅ ready | 第 1 |" in out

    def test_change_status_table_marks_skeleton_in_status(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        # No design.md → skeleton
        out = do.render_markdown_report(
            candidates=["c1"],
            project_root=str(tmp_path),
        )
        assert "📋 skeleton" in out

    def test_change_status_table_uses_ai_blocker_when_present(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        # AI result file marking c2 as blocked by c1
        ai_file = tmp_path / ".rddf" / "state" / ".deps-ai-result.json"
        ai_file.parent.mkdir(parents=True)
        ai_file.write_text('{"ai_deps": [{"from": "c1", "to": "c2", "kind": "hard"}]}')
        out = do.render_markdown_report(
            candidates=["c1", "c2"],
            project_root=str(tmp_path),
            ai_result_file=str(ai_file),
        )
        assert "| c2 | ⚠️ blocked_by | c1 |" in out
        # c1 is not blocked, shows ready
        assert "| c1 | ✅ ready" in out

    def test_ai_blocker_only_for_hard_kind_not_soft(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        ai_file = tmp_path / "ai.json"
        # kind is "soft" (not hard) — should NOT trigger blocked_by
        ai_file.write_text('{"ai_deps": [{"from": "c1", "to": "c2", "kind": "soft"}]}')
        out = do.render_markdown_report(
            candidates=["c1", "c2"],
            project_root=str(tmp_path),
            ai_result_file=str(ai_file),
        )
        # Both should be ready
        assert "| c1 | ✅ ready" in out
        assert "| c2 | ✅ ready" in out

    def test_recommended_execution_order_section(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        out = do.render_markdown_report(
            candidates=["first-c", "second-c"],
            project_root=str(tmp_path),
        )
        assert "## 推荐执行顺序" in out
        assert "`first-c`" in out
        assert "第一个候选" in out

    def test_conflict_warnings_placeholder(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        out = do.render_markdown_report(
            candidates=["c1"],
            project_root=str(tmp_path),
        )
        assert "## 冲突警告" in out
        assert "（如有文件冲突将列于此处）" in out

    def test_ai_section_renders_with_ai_data(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        ai_file = tmp_path / "ai.json"
        ai_file.write_text("""{
  "ai_deps": [
    {"from": "c1", "to": "c2", "kind": "soft", "reason": "implicit dep"}
  ],
  "suggestions": [
    {"change": "c1", "action": "拆分", "reason": "too large"}
  ]
}""")
        out = do.render_markdown_report(
            candidates=["c1"],
            project_root=str(tmp_path),
            ai_result_file=str(ai_file),
        )
        assert "## 🧠 AI 分析建议" in out
        assert "**子代理语义分析结果**" in out
        assert "`c1` → `c2` (soft)" in out
        assert "拆分" in out

    def test_ai_section_fallback_when_no_ai_result(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        out = do.render_markdown_report(
            candidates=["c1"],
            project_root=str(tmp_path),
            ai_result_file=None,
        )
        assert "## 🧠 AI 分析建议" in out
        assert "AI 语义分析未启用 (fallback)" in out

    def test_ai_section_handles_malformed_ai_json_gracefully(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        ai_file = tmp_path / "ai.json"
        ai_file.write_text("not valid json {{{")
        # Should not raise; should fallback gracefully
        out = do.render_markdown_report(
            candidates=["c1"],
            project_root=str(tmp_path),
            ai_result_file=str(ai_file),
        )
        # Falls back to the fallback message (no ai_deps rendered)
        assert "AI 语义分析未启用 (fallback)" in out

    def test_ai_section_suggestions_with_parent_feature(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        ai_file = tmp_path / "ai.json"
        ai_file.write_text("""{
  "suggestions": [
    {"change": "c1", "action": "合并", "reason": "duplicate work", "parent_feature": "core"}
  ]
}""")
        out = do.render_markdown_report(
            candidates=["c1"],
            project_root=str(tmp_path),
            ai_result_file=str(ai_file),
        )
        assert "(parent_feature: core)" in out

    def test_returns_complete_document_for_full_scenario(self, tmp_path):
        from skills.deps.scripts import deps_output as do
        # Realistic scenario: 2 candidates, 1 skeleton, AI blockers
        (tmp_path / "openspec" / "changes" / "c1").mkdir(parents=True)
        (tmp_path / "openspec" / "changes" / "c1" / "design.md").write_text("# c1 design")
        (tmp_path / "openspec" / "changes" / "c1" / "roadmap-meta.yaml").write_text(
            'roadmap:\n  phase: "phase-1"\n  category: "core-impl"\n'
        )
        (tmp_path / "openspec" / "changes" / "c2").mkdir(parents=True)
        # c2 has no design.md → skeleton
        ai_file = tmp_path / "ai.json"
        ai_file.write_text('{"ai_deps": [{"from": "c1", "to": "c2", "kind": "hard"}]}')
        out = do.render_markdown_report(
            candidates=["c1", "c2"],
            project_root=str(tmp_path),
            ai_result_file=str(ai_file),
            roadmap_current_phase="phase-1",
        )
        # All sections present
        assert "# 依赖分析报告" in out
        assert "## 依赖图 (Mermaid)" in out
        assert "## 阶段预检" in out
        assert "## Change 状态表" in out
        assert "## 推荐执行顺序" in out
        assert "## 冲突警告" in out
        assert "## 🧠 AI 分析建议" in out
        # Specific content
        assert "候选 changes: 2" in out
        assert "c1[c1]" in out  # full change, normal brackets
        assert "c2[[c2]]" in out  # skeleton, double brackets
        assert "| c1 | phase-1 | core-impl | ✅ 在阶段内 |" in out
        assert "| c2 | (compat) | (compat) | ⚠️ 无 roadmap-meta |" in out
        assert "| c1 | ✅ ready" in out  # not blocked
        assert "| c2 | ⚠️ blocked_by | c1 |" in out  # blocked by c1
