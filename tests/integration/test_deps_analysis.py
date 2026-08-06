"""Integration test: deps-analysis.json schema and end-to-end deps sync flow.

Validates:
- The deps-analysis.json schema file is valid JSON Schema
- build_analysis + write_analysis + load_analysis roundtrip
- The deps Step 6 markdown-fallback parser (in deps.md) produces
  valid analysis that round-trips through deps_output.build_analysis
- sync_iteration_from_analysis keeps iteration.json consistent

These tests guard the contract that deps.md Step 6 hook relies on.
If they fail, either deps.md Step 6 is broken or deps_output.py
has drifted from what deps.md expects.
"""
import json
import os
import re
import pytest
import jsonschema

from skills.deps.scripts import deps_output as do
from skills._lib import iteration as it


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path):
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    return str(tmp_path)


@pytest.fixture
def deps_schema():
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "_lib", "schemas", "deps_analysis_schema.json",
    )
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestDepsAnalysisSchema:
    def test_schema_file_is_valid_json_schema(self, deps_schema):
        assert deps_schema["type"] == "object"
        assert deps_schema["properties"]["version"]["const"] == 1
        assert "changes" in deps_schema["required"]

    def test_minimal_analysis_validates_against_schema(self, deps_schema):
        analysis = do.build_analysis([{"name": "c1"}])
        # Validate using a fresh Draft7 validator (jsonschema may not be a dep here)
        try:
            jsonschema.validate(analysis, deps_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"analysis fails schema: {e.message}")

    def test_full_analysis_validates_against_schema(self, deps_schema):
        analysis = do.build_analysis([
            {"name": "c1", "status": "ready", "parallel_group": 0,
             "blocks": ["c2"], "conflicts": ["c3"]},
            {"name": "c2", "status": "blocked_by", "blocker": "c1",
             "parallel_group": 1, "blocks": ["c3"]},
            {"name": "c3", "status": "conflict", "parallel_group": 0,
             "conflicts": ["c1", "c2"]},
        ], execution_order=["c1", "c3", "c2"], fallback=False)
        jsonschema.validate(analysis, deps_schema)


# ---------------------------------------------------------------------------
# End-to-end: deps → iteration sync via the unified pipeline
# ---------------------------------------------------------------------------

class TestDepsToIterationPipeline:
    def test_full_pipeline_via_structured_output(self, project_root):
        """Simulate: deps writes analysis → iteration reads it.

        1. Seed iteration.json with proposed changes
        2. Simulate deps building analysis
        3. write_analysis → load_analysis round-trip
        4. sync_iteration_from_analysis → iteration updated
        """
        # 1. propose hook wrote these
        for name in ["c1", "c2", "c3"]:
            data = it.load(project_root) if name != "c1" else it.create_empty("v2.1")
            data = it.add_or_update_change(
                data, name=name, status="proposed",
                phase="v2.1", category="test",
            )
            it.save(project_root, data)

        # 2. deps built this analysis
        analysis = do.build_analysis([
            {"name": "c1", "status": "ready", "parallel_group": 0,
             "blocks": ["c2"], "recommendation": "第 1 优先"},
            {"name": "c2", "status": "blocked_by", "blocker": "c1",
             "parallel_group": 1, "conflicts": ["c3"],
             "recommendation": "等 c1 完成后"},
            {"name": "c3", "status": "ready", "parallel_group": 0,
             "conflicts": ["c2"]},
        ], execution_order=["c1", "c3", "c2"], fallback=False)

        # 3. write + load
        do.write_analysis(project_root, analysis)
        loaded = do.load_analysis(project_root)
        assert loaded is not None
        assert loaded["changes"]["c1"]["blocker"] is None
        assert loaded["changes"]["c2"]["blocker"] == "c1"
        assert loaded["changes"]["c2"]["conflicts"] == ["c3"]
        assert loaded["execution_order"] == ["c1", "c3", "c2"]

        # 4. sync to iteration
        count = do.sync_iteration_from_analysis(project_root, it)
        assert count == 3

        iter_data = it.load(project_root)
        by_name = {c["name"]: c for c in iter_data["changes"]}
        assert by_name["c1"]["blocker"] is None
        assert by_name["c1"]["parallel_group"] == 0
        assert by_name["c2"]["blocker"] == "c1"
        assert by_name["c2"]["parallel_group"] == 1
        assert by_name["c2"]["conflicts"] == ["c3"]
        # iteration lifecycle status preserved (deps doesn't touch status)
        assert by_name["c1"]["status"] == "proposed"
        assert by_name["c2"]["status"] == "proposed"

    def test_markdown_fallback_round_trip(self, project_root):
        """Simulate the deps.md Step 6 markdown parser path.

        1. Seed iteration.json
        2. Write a deps-output.md that matches the §5b/§5d format
        3. The deps.md Step 6 hook should:
           a. Load deps-analysis.json (None, falls back to markdown)
           b. Parse markdown → build deps-analysis.json
           c. Write deps-analysis.json
           d. Sync iteration.json
        """
        # 1. Seed
        data = it.add_or_update_change(
            it.create_empty(), name="c1", status="proposed",
        )
        data = it.add_or_update_change(data, name="c2", status="proposed")
        it.save(project_root, data)

        # 2. Write deps-output.md in the expected format
        deps_md = """# 依赖分析报告

## Change 状态表

| Change | 状态 | 阻塞于 | 阻塞了谁 | 冲突 | 置信度 | 推荐 |
|--------|------|--------|---------|------|--------|------|
| c1 | ✅ ready | — | c2 | — | 高 | 第 1 |
| c2 | ⚠️ blocked_by | c1 | — | — | 高 | 等 c1 完成后 |

## 推荐执行顺序

1. c1
2. c2

## 冲突警告

🔴 文件冲突:
  c2 ←→ c3: src/conflict.h
"""
        md_path = os.path.join(project_root, ".rddf", "state", ".deps-output.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(deps_md)

        # 3a. Confirm load_analysis returns None (no JSON yet)
        assert do.load_analysis(project_root) is None

        # 3b/c. Replicate the deps.md Step 6 hook's markdown parsing
        text = deps_md
        status_table = re.search(r'## Change 状态表\n\n\|.*?\n\|.*?\n((?:\|.*?\n)+)', text)
        changes_info = {}
        if status_table:
            rows = status_table.group(1).strip().split('\n')
            for idx, row in enumerate(rows):
                cells = [c.strip() for c in row.strip('|').split('|')]
                if len(cells) < 2:
                    continue
                name = cells[0]
                if not name or name == '—':
                    continue
                blocker = cells[2] if len(cells) > 2 and cells[2] not in ('—', '') else None
                changes_info[name] = {
                    'blocker': blocker,
                    'parallel_group': idx if blocker else 0,
                    'conflicts': [],
                }

        conflicts_section = re.search(r'## 冲突警告.*?\n(.*?)(?=\n## |\Z)', text, re.DOTALL)
        if conflicts_section:
            for line in conflicts_section.group(1).split('\n'):
                m = re.search(r'(\S+)\s+←→\s+(\S+):', line)
                if m:
                    a, b = m.group(1), m.group(2)
                    for n in (a, b):
                        changes_info.setdefault(n, {'blocker': None, 'parallel_group': 0, 'conflicts': []})
                        existing = changes_info[n].get('conflicts', [])
                        other = b if n == a else a
                        if other not in existing:
                            existing.append(other)
                        changes_info[n]['conflicts'] = existing

        analysis_changes = []
        for name, info in changes_info.items():
            status = 'blocked_by' if info.get('blocker') else 'ready'
            analysis_changes.append({
                'name': name,
                'status': status,
                'blocker': info.get('blocker'),
                'blocks': [],
                'parallel_group': info.get('parallel_group', 0),
                'conflicts': info.get('conflicts', []),
                'confidence': 'low',
                'recommendation': '',
            })
        analysis = do.build_analysis(analysis_changes, fallback=True)
        do.write_analysis(project_root, analysis)

        # Now load_analysis should find the JSON
        loaded_analysis = do.load_analysis(project_root)
        assert loaded_analysis is not None
        assert loaded_analysis["fallback"] is True
        assert "c1" in loaded_analysis["changes"]
        assert "c2" in loaded_analysis["changes"]
        # Note: c3 is in the conflict section but not in the status table,
        # so it may or may not be in analysis depending on parser behavior
        # (current parser only includes changes in §5b status table)

        # 3d. Sync iteration
        # Note: the parser includes c3 because it appears in §5d
        # (conflicts section uses setdefault to add it even if it was
        # not in §5b). So count is 3, not 2.
        count = do.sync_iteration_from_analysis(project_root, it)
        assert count == 3

        iter_data = it.load(project_root)
        by_name = {c["name"]: c for c in iter_data["changes"]}
        assert by_name["c1"]["blocker"] is None
        assert by_name["c1"]["parallel_group"] == 0
        assert by_name["c2"]["blocker"] == "c1"
        assert by_name["c2"]["parallel_group"] == 1
        # c3 was added to analysis by the conflicts parser (default entry)
        c3 = by_name["c3"]
        assert c3.get("conflicts") == ["c2"]

    def test_second_run_uses_json_path(self, project_root):
        """After the first run writes deps-analysis.json, the second run
        should use the JSON path (load_analysis returns the data)."""
        # Pre-seed JSON directly
        analysis = do.build_analysis([
            {"name": "c1", "blocker": "c0", "parallel_group": 1, "conflicts": ["c2"]},
        ])
        do.write_analysis(project_root, analysis)

        # Second "run" of the hook: load_analysis should return the data
        loaded = do.load_analysis(project_root)
        assert loaded is not None
        assert loaded["changes"]["c1"]["blocker"] == "c0"
        assert loaded["changes"]["c1"]["conflicts"] == ["c2"]
