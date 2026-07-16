"""Unit tests for skills/_lib/deps_output.py — structured deps analysis."""
import json
import os
from pathlib import Path
import pytest

from skills._lib import deps_output as do
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
        """deps may surface a change that isn't in iteration.json yet. The hook
        should still create an entry (with status=proposed)."""
        data = it.create_empty()  # empty
        it.save(project_root, data)

        analysis = do.build_analysis([{"name": "c-new", "blocker": None}])
        do.write_analysis(project_root, analysis)

        count = do.sync_iteration_from_analysis(project_root, it)
        assert count == 1

        loaded = it.load(project_root)
        names = [c["name"] for c in loaded["changes"]]
        assert "c-new" in names

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
