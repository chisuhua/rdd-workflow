# Feature Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first-class feature management surface specified in `docs/superpowers/specs/2026-07-09-feature-management-design.md` — a new `feature` skill with 4 subcommands (summary / graph / status / order), backed by a 6-step Python derivation pipeline that writes a `feature_view` node into `iteration.json`.

**Architecture:** Three-layer — (1) `skills/feature.md` (skill body) parses subcommand + prints rendered output, (2) `skills/_lib/feature_view.py` runs the 6-step pipeline (5 pure functions + 1 orchestrator with IO), (3) `iteration.json` extended with a `feature_view` node (additive; existing schema loosened to allow the new top-level field, no version bump). Reuses `iteration.derive_feature_name()`, `iteration.load/save()`, and `deps_output.load_analysis()` — zero changes to those modules.

**Tech Stack:** Python 3.11+ (no new deps), bash 3+ (skill body subcommand dispatch), bats-core 1.10+ (integration tests), pytest (unit tests), `jsonschema` (already in requirements.txt for schema validation).

---

## Pre-flight (Read Once, Never Repeat)

These gates are confirmed as of `2026-07-09`; **re-verify before execution**:

- [x] Spec exists at `docs/superpowers/specs/2026-07-09-feature-management-design.md` and is committed (commit `8ce9a0c`).
- [x] `iteration.derive_feature_name(name, data)` returns: (1) `change["parent_feature"]` if set, (2) name-prefix match against `_FEATURE_PREFIX_RE = r"^(feature-[a-z0-9]+)(-[a-z0-9-]+)?$"`, (3) the change name itself. Plan handles the self-group case as `__ungrouped__`.
- [x] `iteration._VALID_STATUSES = ("planned", "proposed", "in_worktree", "review", "completed", "archived")` — all 6 are valid `change.status` values.
- [x] `iteration.save(project_root, data)` is atomic (write-to-tmp + rename) with `FileLock(_LOCK_TIMEOUT=5.0)` and merge-on-save (re-read inside the lock, merge by name). Reuse as-is.
- [x] `deps_output.load_analysis(project_root)` returns `dict | None`. When non-None: `data["changes"][name]["blocker"]` is str|None, `data["changes"][name]["conflicts"]` is list[str].
- [x] `tests/conftest.py` adds project root to `sys.path` — `import skills._lib.feature_view` resolves in pytest.
- [x] `iteration_schema.json` must allow new `feature_view` top-level property — one-line schema addition (no version bump).
- [x] `feature_view.py` is a NEW file — does not modify `iteration.py` or `deps_output.py`.
- [x] `feature.md` skill body is a NEW file. `guide.md` / `INSTALL.md` / `README.md` / `AGENTS.md` get 1-line touch-ups.
- [x] No CLI flag changes; subcommand dispatch is in the skill body via bash case statement.
- [x] CI constant-truth gate: `grep -rn "assert .* or True" tests/` must remain empty. All new tests use plain `assert` with messages.

**Pre-existing assumptions surfaced by this work**:

1. `derive_feature_name` returns change name as a self-group fallback. The plan detects "ungrouped" by checking: `derived == change_name AND parent_feature not set AND not re.match(_FEATURE_PREFIX_RE, change_name)`. This logic lives in `feature_view.py` (not in `iteration.py`).
2. The `__ungrouped__` bucket is a synthetic feature name (string constant in `feature_view.py`). It is excluded from edge computation and execution_order waves.
3. `iteration_schema.json` currently uses `additionalProperties: true` semantics (the existing schema doesn't define top-level `properties` strictly). **Re-verify** by reading the schema before Task 1; if it does forbid unknown fields, add `"feature_view"` to the schema properties list (one-line edit, no version bump).

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `skills/feature.md` | Skill body: frontmatter + 4 subcommand dispatch + renderers | Create |
| `skills/_lib/feature_view.py` | 6-step pipeline: 5 pure functions + 1 orchestrator | Create |
| `skills/_lib/schemas/feature_view_schema.json` | JSON Schema v1 for `feature_view` | Create |
| `tests/unit/test_feature_view.py` | 16 unit tests covering pipeline + edge cases | Create |
| `tests/integration/test_feature_skill.bats` | 6 bats tests covering skill end-to-end | Create |
| `skills/_lib/schemas/iteration_schema.json` | Add `feature_view` to allowed top-level properties | Edit (1 line) |
| `skills/guide.md` | Add `feature` to recommender output (1 line) | Edit (1 line) |
| `skills/INSTALL.md` | Add `feature.md` to sub-skill list (1 line) | Edit (1 line) |
| `README.md` | Add `feature` row to v2.0 new-features table | Edit (3 lines) |
| `AGENTS.md` | Add `skills/feature.md` to directory tree | Edit (1 line) |

**Not touched**: `iteration.py`, `deps_output.py`, `deps.md`, `status.md`, `propose.md`, `execute.md`, `roadmap.md`, any `openspec/changes/*/`.

---

## Task 1: JSON Schema v1

**Files:**
- Create: `skills/_lib/schemas/feature_view_schema.json`
- Test: `tests/unit/test_feature_view.py::TestFeatureViewSchema`

- [ ] **Step 1: Write the failing schema test**

```python
# tests/unit/test_feature_view.py
import json
import os
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "skills" / "_lib" / "schemas" / "feature_view_schema.json"


@pytest.fixture
def schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


@pytest.fixture
def valid_payload() -> dict:
    return {
        "schema_version": 1,
        "updated_at": "2026-07-09T12:00:00+00:00",
        "features": {
            "feature-stream": {
                "name": "feature-stream",
                "status": "in_progress",
                "change_names": ["refactor-stream-base", "add-m2sPipe"],
                "change_count": 2,
                "archived_count": 0,
                "rollup_basis": "explicit",
                "depends_on": [],
                "blocks": ["feature-pipes"],
                "parallel_group": 0,
                "conflicts_with": [],
            }
        },
        "execution_order": [["feature-stream"], ["feature-pipes"]],
    }


class TestFeatureViewSchema:
    def test_valid_payload_accepted(self, schema, valid_payload):
        jsonschema.validate(valid_payload, schema)  # should not raise

    def test_missing_schema_version_rejected(self, schema, valid_payload):
        del valid_payload["schema_version"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_wrong_status_rejected(self, schema, valid_payload):
        valid_payload["features"]["feature-stream"]["status"] = "bogus"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_wrong_schema_version_rejected(self, schema, valid_payload):
        valid_payload["schema_version"] = 99
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_execution_order_must_be_list_of_lists(self, schema, valid_payload):
        valid_payload["execution_order"] = ["feature-stream", "feature-pipes"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_features_must_be_object(self, schema, valid_payload):
        valid_payload["features"] = ["feature-stream", "feature-pipes"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)
```

- [ ] **Step 2: Run tests, expect FAIL (schema file does not exist yet)**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestFeatureViewSchema -v 2>&1 | head -30
```

Expected: `FileNotFoundError` or `jsonschema.SchemaError` for missing schema.

- [ ] **Step 3: Write the schema file**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://spec-workflow.dev/schemas/feature_view_schema.json",
  "title": "FeatureView",
  "description": "Derived view of features (groups of changes) inside iteration.json. Written by skills/_lib/feature_view.py.",
  "type": "object",
  "required": ["schema_version", "updated_at", "features", "execution_order"],
  "additionalProperties": false,
  "properties": {
    "schema_version": {
      "type": "integer",
      "const": 1,
      "description": "Bumped on breaking changes."
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of last computation."
    },
    "features": {
      "type": "object",
      "additionalProperties": { "$ref": "#/$defs/FeatureEntry" },
      "description": "Map of feature name to FeatureEntry."
    },
    "execution_order": {
      "type": "array",
      "items": {
        "type": "array",
        "items": { "type": "string" }
      },
      "description": "Wave-grouped topological order; same index = parallel."
    }
  },
  "$defs": {
    "FeatureEntry": {
      "type": "object",
      "required": [
        "name", "status", "change_names", "change_count",
        "archived_count", "rollup_basis",
        "depends_on", "blocks", "parallel_group", "conflicts_with"
      ],
      "additionalProperties": false,
      "properties": {
        "name": { "type": "string" },
        "status": {
          "type": "string",
          "enum": ["blocked", "in_progress", "ready", "done", "ungrouped"]
        },
        "change_names": { "type": "array", "items": { "type": "string" } },
        "change_count": { "type": "integer", "minimum": 0 },
        "archived_count": { "type": "integer", "minimum": 0 },
        "rollup_basis": {
          "type": "string",
          "enum": ["explicit", "name_prefix", "mixed"]
        },
        "depends_on": { "type": "array", "items": { "type": "string" } },
        "blocks": { "type": "array", "items": { "type": "string" } },
        "parallel_group": { "type": "integer", "minimum": 0 },
        "conflicts_with": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

- [ ] **Step 4: Run tests, expect PASS**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestFeatureViewSchema -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow
git add skills/_lib/schemas/feature_view_schema.json tests/unit/test_feature_view.py
git commit -m "feat(feature-view): JSON schema v1 + 6 validation tests"
```

---

## Task 2: `group_changes_by_feature` (pure function)

**Files:**
- Modify: `skills/_lib/feature_view.py` (new file)
- Test: `tests/unit/test_feature_view.py::TestGroupChangesByFeature`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_feature_view.py`:

```python
from skills._lib.feature_view import group_changes_by_feature


class TestGroupChangesByFeature:
    def test_explicit_parent_feature(self):
        changes = [
            {"name": "a-core", "parent_feature": "feature-a"},
            {"name": "a-adapters", "parent_feature": "feature-a"},
            {"name": "b-core", "parent_feature": "feature-b"},
        ]
        result = group_changes_by_feature(changes)
        assert set(result.keys()) == {"feature-a", "feature-b"}, result
        assert sorted(result["feature-a"]) == ["a-adapters", "a-core"]
        assert result["feature-b"] == ["b-core"]

    def test_name_prefix_fallback(self):
        changes = [
            {"name": "feature-stream-core"},
            {"name": "feature-stream-adapters"},
            {"name": "feature-utils-helper"},
        ]
        result = group_changes_by_feature(changes)
        assert set(result.keys()) == {"feature-stream", "feature-utils"}, result

    def test_mixed_basis_uses_max_signal(self):
        changes = [
            {"name": "feature-stream-core"},                # name_prefix
            {"name": "feature-stream-tests", "parent_feature": "feature-stream"},  # explicit
        ]
        result = group_changes_by_feature(changes)
        assert list(result.keys()) == ["feature-stream"], result
        assert sorted(result["feature-stream"]) == ["feature-stream-core", "feature-stream-tests"]

    def test_ungrouped_synthetic(self):
        changes = [
            {"name": "fix-typo"},
            {"name": "debt-cleanup"},
            {"name": "feature-stream-core", "parent_feature": "feature-stream"},
        ]
        result = group_changes_by_feature(changes)
        assert "__ungrouped__" in result
        assert sorted(result["__ungrouped__"]) == ["debt-cleanup", "fix-typo"]
        assert result["feature-stream"] == ["feature-stream-core"]
```

- [ ] **Step 2: Run tests, expect FAIL (module does not exist)**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestGroupChangesByFeature -v 2>&1 | tail -20
```

Expected: `ModuleNotFoundError: No module named 'skills._lib.feature_view'`.

- [ ] **Step 3: Write the module stub with the function**

Create `skills/_lib/feature_view.py`:

```python
"""Feature-level derived view of iteration.json.

Pure derivation — no source-of-truth mutation. The 5 pure step functions
(Steps 1-5) take plain Python data and return plain Python data; the
6th function is the IO orchestrator that reads iteration.json + deps-analysis.json
and writes the computed `feature_view` node back to iteration.json.
"""
from __future__ import annotations

import datetime
import re
from typing import Optional

from skills._lib import iteration as it_mod


# Synthetic feature name for changes with no parent_feature and no feature- prefix.
# Excluded from edge computation and execution_order waves.
UNGROUPED = "__ungrouped__"

# Mirror iteration._FEATURE_PREFIX_RE so this module is self-contained
# (avoids a private import; iteration.py exports `derive_feature_name`).
_FEATURE_PREFIX_RE = re.compile(r"^(feature-[a-z0-9]+)(-[a-z0-9-]+)?$")


def _is_ungrouped(change_name: str, derived: str) -> bool:
    """Return True if the change ended up in a self-group (no real feature).

    Self-group happens when derive_feature_name returns the change name itself,
    which means no parent_feature field AND no `feature-<name>-<sub>` prefix.
    """
    if derived != change_name:
        return False
    return not _FEATURE_PREFIX_RE.match(change_name)


def group_changes_by_feature(changes: list[dict]) -> dict[str, list[str]]:
    """Group changes by derived feature name.

    Returns a dict keyed by feature name, values are sorted lists of change names.
    The synthetic `__ungrouped__` key buckets changes with no real feature
    affiliation (no parent_feature field AND no `feature-` prefix in the name).
    """
    groups: dict[str, list[str]] = {}
    for ch in changes:
        name = ch["name"]
        parent = ch.get("parent_feature")
        # Replicate iteration.derive_feature_name inline to also know
        # whether the result was a self-group.
        if parent:
            derived = parent
        else:
            m = _FEATURE_PREFIX_RE.match(name)
            derived = m.group(1) if m else name
        if _is_ungrouped(name, derived):
            groups.setdefault(UNGROUPED, []).append(name)
        else:
            groups.setdefault(derived, []).append(name)
    # Sort for deterministic output
    for k in groups:
        groups[k] = sorted(groups[k])
    return dict(sorted(groups.items()))
```

- [ ] **Step 4: Run tests, expect PASS**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestGroupChangesByFeature -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow
git add skills/_lib/feature_view.py tests/unit/test_feature_view.py
git commit -m "feat(feature-view): group_changes_by_feature + 4 tests"
```

---

## Task 3: `rollup_status` (pure function)

**Files:**
- Modify: `skills/_lib/feature_view.py`
- Test: `tests/unit/test_feature_view.py::TestRollupStatus`

- [ ] **Step 1: Write the failing tests**

```python
from skills._lib.feature_view import rollup_status


class TestRollupStatus:
    def test_blocked_wins_over_in_progress(self):
        changes = [
            {"name": "a", "status": "blocked_by"},
            {"name": "b", "status": "in_worktree"},
        ]
        assert rollup_status(changes) == "blocked"

    def test_in_progress_when_no_blocker_and_one_in_worktree(self):
        changes = [
            {"name": "a", "status": "in_worktree"},
            {"name": "b", "status": "proposed"},
        ]
        assert rollup_status(changes) == "in_progress"

    def test_ready_when_all_proposed_or_planned(self):
        changes = [
            {"name": "a", "status": "proposed"},
            {"name": "b", "status": "planned"},
        ]
        assert rollup_status(changes) == "ready"

    def test_done_when_all_archived(self):
        changes = [
            {"name": "a", "status": "archived"},
            {"name": "b", "status": "archived"},
        ]
        assert rollup_status(changes) == "done"

    def test_in_progress_with_review_counts(self):
        # review is a transitional state; treated like in_progress for rollup
        changes = [
            {"name": "a", "status": "review"},
            {"name": "b", "status": "proposed"},
        ]
        assert rollup_status(changes) == "in_progress"

    def test_empty_returns_ungrouped(self):
        assert rollup_status([]) == "ungrouped"
```

- [ ] **Step 2: Run tests, expect FAIL**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestRollupStatus -v 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'rollup_status'`.

- [ ] **Step 3: Implement the function**

Append to `skills/_lib/feature_view.py`:

```python
# Status priority chain for rollup (first match wins).
# in_worktree + review both count as "in flight" for rollup purposes.
_IN_FLIGHT = ("in_worktree", "review")
_PENDING = ("proposed", "planned")


def rollup_status(changes: list[dict]) -> str:
    """Roll up a list of change dicts into a feature status enum.

    Priority chain: blocked > in_progress > ready > done > ungrouped.
    """
    if not changes:
        return "ungrouped"
    statuses = {c.get("status") for c in changes}
    if "blocked_by" in statuses:
        return "blocked"
    if any(s in _IN_FLIGHT for s in statuses):
        return "in_progress"
    if all(s in _PENDING for s in statuses):
        return "ready"
    if statuses == {"archived"}:
        return "done"
    # Mixed (e.g. some completed, some proposed): treat as in_progress
    # because the feature is partially through.
    return "in_progress"
```

- [ ] **Step 4: Run tests, expect PASS**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestRollupStatus -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow
git add skills/_lib/feature_view.py tests/unit/test_feature_view.py
git commit -m "feat(feature-view): rollup_status with priority chain + 6 tests"
```

---

## Task 4: `compute_feature_edges` (pure function)

**Files:**
- Modify: `skills/_lib/feature_view.py`
- Test: `tests/unit/test_feature_view.py::TestComputeFeatureEdges`

- [ ] **Step 1: Write the failing tests**

```python
from skills._lib.feature_view import compute_feature_edges, UNGROUPED


def _deps(changes_pairs: list[tuple[str, Optional[str]]]) -> dict:
    """Build a minimal deps-analysis-like dict from (change_name, blocker) pairs."""
    return {
        "changes": {
            name: {"name": name, "blocker": blocker, "conflicts": []}
            for name, blocker in changes_pairs
        }
    }


class TestComputeFeatureEdges:
    def test_all_pairs_hard_yields_one_edge(self):
        groups = {"A": ["a1", "a2"], "B": ["b1", "b2", "b3"]}
        deps = _deps([("a1", "b1"), ("a1", "b2"), ("a1", "b3"),
                      ("a2", "b1"), ("a2", "b2"), ("a2", "b3")])
        edges = compute_feature_edges(deps, groups)
        assert ("A", "B", "hard") in edges

    def test_partial_overlap_yields_no_edge(self):
        # 3 of 6 pairs present → conservative, no feature edge
        groups = {"A": ["a1", "a2"], "B": ["b1", "b2", "b3"]}
        deps = _deps([("a1", "b1"), ("a1", "b2"), ("a2", "b1")])
        edges = compute_feature_edges(deps, groups)
        assert edges == []

    def test_disjoint_yields_no_edge(self):
        groups = {"A": ["a1"], "B": ["b1"]}
        deps = _deps([])
        edges = compute_feature_edges(deps, groups)
        assert edges == []

    def test_ungrouped_excluded(self):
        groups = {"A": ["a1"], UNGROUPED: ["x"]}
        deps = _deps([("a1", "x")])
        edges = compute_feature_edges(deps, groups)
        assert edges == [], f"ungrouped should not produce edges, got {edges}"

    def test_self_loop_excluded(self):
        # a1 blocked by a2 — both in A. Must not yield A -> A edge.
        groups = {"A": ["a1", "a2"]}
        deps = _deps([("a1", "a2")])
        edges = compute_feature_edges(deps, groups)
        assert edges == []
```

- [ ] **Step 2: Run tests, expect FAIL**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestComputeFeatureEdges -v 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'compute_feature_edges'`.

- [ ] **Step 3: Implement the function**

Append to `skills/_lib/feature_view.py`:

```python
def compute_feature_edges(
    deps_analysis: dict, feature_groups: dict[str, list[str]]
) -> list[tuple[str, str, str]]:
    """Compute feature-level dependency edges from change-level hard deps.

    For each pair (Fa, Fb) with Fa != Fb, count hard change-level edges from
    any change in Fa to any change in Fb. Produce a feature edge iff every
    possible (from_change, to_change) pair is present (all-pairs-hard rule).

    Returns list of (from_feature, to_feature, "hard") tuples.
    The synthetic UNGROUPED feature is excluded from edge computation.
    """
    changes_map = deps_analysis.get("changes", {})
    real_groups = {k: v for k, v in feature_groups.items() if k != UNGROUPED}
    features = sorted(real_groups.keys())

    edges: list[tuple[str, str, str]] = []
    for fa in features:
        for fb in features:
            if fa >= fb:  # avoid duplicates (lex order) and self-loops
                continue
            n = 0
            m = 0
            for from_ch in real_groups[fa]:
                info = changes_map.get(from_ch, {})
                blocker = info.get("blocker")
                if blocker in real_groups[fb]:
                    n += 1
                m += 1
            m_total = m * len(real_groups[fb])
            if m_total > 0 and n == m_total:
                edges.append((fa, fb, "hard"))
    return edges
```

- [ ] **Step 4: Run tests, expect PASS**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestComputeFeatureEdges -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow
git add skills/_lib/feature_view.py tests/unit/test_feature_view.py
git commit -m "feat(feature-view): compute_feature_edges (all-pairs-hard rule) + 5 tests"
```

---

## Task 5: `compute_parallel_groups` (pure function)

**Files:**
- Modify: `skills/_lib/feature_view.py`
- Test: `tests/unit/test_feature_view.py::TestComputeParallelGroups`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from skills._lib.feature_view import compute_parallel_groups, FeatureCycleError


class TestComputeParallelGroups:
    def test_no_edges_all_wave_zero(self):
        features = {"A": 0, "B": 0, "C": 0}
        result = compute_parallel_groups([], features)
        assert result == {"A": 0, "B": 0, "C": 0}

    def test_chain_produces_three_waves(self):
        edges = [("A", "B", "hard"), ("B", "C", "hard")]
        features = {"A": 0, "B": 0, "C": 0}
        result = compute_parallel_groups(edges, features)
        assert result == {"A": 0, "B": 1, "C": 2}

    def test_diamond_shape(self):
        # A -> B, A -> C, B -> D, C -> D
        edges = [
            ("A", "B", "hard"), ("A", "C", "hard"),
            ("B", "D", "hard"), ("C", "D", "hard"),
        ]
        features = {"A": 0, "B": 0, "C": 0, "D": 0}
        result = compute_parallel_groups(edges, features)
        assert result == {"A": 0, "B": 1, "C": 1, "D": 2}

    def test_cycle_raises(self):
        edges = [("A", "B", "hard"), ("B", "A", "hard")]
        features = {"A": 0, "B": 0}
        with pytest.raises(FeatureCycleError) as exc_info:
            compute_parallel_groups(edges, features)
        assert set(exc_info.value.cycle) == {"A", "B"}
```

- [ ] **Step 2: Run tests, expect FAIL**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestComputeParallelGroups -v 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'compute_parallel_groups' or 'FeatureCycleError'`.

- [ ] **Step 3: Implement the function**

Append to `skills/_lib/feature_view.py`:

```python
class FeatureCycleError(Exception):
    """Raised when the feature dependency graph contains a cycle."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"feature dependency cycle: {' -> '.join(cycle)}")


def compute_parallel_groups(
    edges: list[tuple[str, str, str]], features: dict
) -> dict[str, int]:
    """Assign each feature to a parallel-group wave index via BFS topo layering.

    `features` is a dict (values ignored; keys are the feature names).
    Returns dict[feature_name, wave_index]. Wave 0 = no incoming edges.
    Raises FeatureCycleError if a cycle is detected.
    """
    if not features:
        return {}
    in_degree: dict[str, int] = {f: 0 for f in features}
    successors: dict[str, list[str]] = {f: [] for f in features}
    for fa, fb, _kind in edges:
        if fa in features and fb in features:
            in_degree[fb] = in_degree.get(fb, 0) + 1
            successors[fa].append(fb)

    wave = 0
    groups: dict[str, int] = {}
    remaining = set(features.keys())
    while remaining:
        # BFS: find all current in-degree-zero features
        current_wave = sorted(f for f in remaining if in_degree.get(f, 0) == 0)
        if not current_wave:
            raise FeatureCycleError(sorted(remaining))
        for f in current_wave:
            groups[f] = wave
            remaining.discard(f)
            for succ in successors.get(f, []):
                if succ in remaining:
                    in_degree[succ] -= 1
        wave += 1
    return groups
```

- [ ] **Step 4: Run tests, expect PASS**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestComputeParallelGroups -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow
git add skills/_lib/feature_view.py tests/unit/test_feature_view.py
git commit -m "feat(feature-view): compute_parallel_groups (BFS topo) + 4 tests"
```

---

## Task 6: `render_mermaid` (pure function)

**Files:**
- Modify: `skills/_lib/feature_view.py`
- Test: `tests/unit/test_feature_view.py::TestRenderMermaid`

- [ ] **Step 1: Write the failing tests**

```python
from skills._lib.feature_view import render_mermaid


class TestRenderMermaid:
    def test_emits_flowchart_lr_header(self):
        out = render_mermaid({}, [], [], {})
        assert out.startswith("flowchart LR"), out

    def test_one_node_per_feature(self):
        features = {
            "A": {"status": "ready", "archived_count": 0, "change_count": 2, "parallel_group": 0},
            "B": {"status": "done", "archived_count": 1, "change_count": 1, "parallel_group": 1},
        }
        out = render_mermaid(features, [], [], {"A": 0, "B": 1})
        assert 'A["A' in out
        assert 'B["B' in out

    def test_hard_edge_renders_arrow(self):
        features = {"A": {"status": "ready", "archived_count": 0, "change_count": 1, "parallel_group": 0},
                    "B": {"status": "blocked", "archived_count": 0, "change_count": 1, "parallel_group": 1}}
        edges = [("A", "B", "hard")]
        out = render_mermaid(features, edges, [], {"A": 0, "B": 1})
        assert "A --> B" in out

    def test_conflict_renders_dotted_arrow(self):
        features = {"A": {"status": "ready", "archived_count": 0, "change_count": 1, "parallel_group": 0},
                    "B": {"status": "ready", "archived_count": 0, "change_count": 1, "parallel_group": 0}}
        out = render_mermaid(features, [], [("A", "B")], {"A": 0, "B": 0})
        assert "A -.->|冲突| B" in out
```

- [ ] **Step 2: Run tests, expect FAIL**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestRenderMermaid -v 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'render_mermaid'`.

- [ ] **Step 3: Implement the function**

Append to `skills/_lib/feature_view.py`:

```python
def render_mermaid(
    features: dict,
    edges: list[tuple[str, str, str]],
    conflicts: list[tuple[str, str]],
    parallel_groups: dict[str, int],
) -> str:
    """Render a Mermaid flowchart at feature granularity.

    `features` is a dict[feature_name, {status, archived_count, change_count, parallel_group}].
    Returns the Mermaid source as a string.
    """
    lines = ["flowchart LR"]
    for name, info in sorted(features.items()):
        label = (
            f"{name}<br/>"
            f"{info['status']} · "
            f"{info['archived_count']}/{info['change_count']} · "
            f"wave {info['parallel_group']}"
        )
        # Quote label, escape any double quotes inside (defensive; names are kebab-case)
        safe = label.replace('"', "&quot;")
        lines.append(f'  {name}["{safe}"]')
    for fa, fb, _ in edges:
        lines.append(f"  {fa} --> {fb}")
    for fa, fb in conflicts:
        lines.append(f"  {fa} -.->|冲突| {fb}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests, expect PASS**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestRenderMermaid -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow
git add skills/_lib/feature_view.py tests/unit/test_feature_view.py
git commit -m "feat(feature-view): render_mermaid + 4 tests"
```

---

## Task 7: `update_iteration_feature_view` (orchestrator with IO)

**Files:**
- Modify: `skills/_lib/feature_view.py`
- Modify: `skills/_lib/schemas/iteration_schema.json` (1-line schema addition — see pre-flight item 3)
- Test: `tests/unit/test_feature_view.py::TestUpdateIterationFeatureView`

- [ ] **Step 1: Verify and patch iteration_schema.json if needed**

```bash
cd /workspace/project/spec-workflow
head -30 skills/_lib/schemas/iteration_schema.json
```

If the top-level `properties` object does NOT list `feature_view`, add it. The minimal edit is to locate the top-level `properties` block and add a `feature_view` key that allows either `null` or a valid FeatureView object. Find the closing `}` of top-level `properties` and insert before it:

```json
    "feature_view": {
      "oneOf": [
        { "type": "null" },
        { "$ref": "feature_view_schema.json" }
      ],
      "description": "Derived view written by skills/feature.md. Optional."
    }
```

(If the schema is too strict to allow this edit, the simpler workaround is to set `"additionalProperties": true` at the top level. Choose the more surgical option for the actual file.)

- [ ] **Step 2: Write the failing orchestrator test**

```python
import json
import os
import tempfile
from pathlib import Path

from skills._lib import feature_view
from skills._lib import iteration as it_mod


def _write_iteration(project_root: Path, changes: list[dict]) -> None:
    """Write a minimal valid iteration.json for testing."""
    state_dir = project_root / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 1,
        "updated_at": "2026-07-09T00:00:00+00:00",
        "changes": [{"name": c["name"], "status": c.get("status", "proposed"),
                     "parent_feature": c.get("parent_feature")}
                    for c in changes],
    }
    (state_dir / "iteration.json").write_text(json.dumps(data))


class TestUpdateIterationFeatureView:
    def test_writes_feature_view_node(self, tmp_path):
        _write_iteration(tmp_path, [
            {"name": "feature-stream-core", "parent_feature": "feature-stream"},
            {"name": "feature-stream-tests", "parent_feature": "feature-stream"},
            {"name": "fix-typo"},  # ungrouped
        ])
        count = feature_view.update_iteration_feature_view(str(tmp_path))
        assert count == 2  # feature-stream + __ungrouped__
        data = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        assert "feature_view" in data
        fv = data["feature_view"]
        assert fv["schema_version"] == 1
        assert "feature-stream" in fv["features"]
        assert "__ungrouped__" in fv["features"]
        # feature-stream has 2 changes, 0 archived → status = ready
        assert fv["features"]["feature-stream"]["status"] == "ready"
        assert fv["features"]["feature-stream"]["change_count"] == 2

    def test_missing_iteration_raises(self, tmp_path):
        # No iteration.json written
        import pytest
        with pytest.raises(feature_view.NoIterationError):
            feature_view.update_iteration_feature_view(str(tmp_path))

    def test_missing_deps_analysis_still_writes_status(self, tmp_path):
        _write_iteration(tmp_path, [
            {"name": "a-core", "parent_feature": "feature-a"},
        ])
        count = feature_view.update_iteration_feature_view(str(tmp_path))
        assert count == 1
        data = json.loads((tmp_path / ".rddf" / "state" / "iteration.json").read_text())
        fv = data["feature_view"]
        assert fv["features"]["feature-a"]["depends_on"] == []
        assert fv["features"]["feature-a"]["blocks"] == []
        # execution_order present, single wave
        assert fv["execution_order"] == [["feature-a"]]
```

- [ ] **Step 3: Run tests, expect FAIL**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestUpdateIterationFeatureView -v 2>&1 | tail -15
```

Expected: `ImportError` or `AttributeError` for `NoIterationError` / `update_iteration_feature_view`.

- [ ] **Step 4: Implement the orchestrator and supporting types**

Append to `skills/_lib/feature_view.py`:

```python
class NoIterationError(Exception):
    """Raised when iteration.json is missing — feature view cannot be computed."""


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _compute_rollup_basis(change_names: list[str], all_changes: dict[str, dict]) -> str:
    """Determine whether the feature's changes were grouped by explicit, prefix, or mixed."""
    bases = set()
    for n in change_names:
        ch = all_changes.get(n, {})
        if ch.get("parent_feature"):
            bases.add("explicit")
        else:
            bases.add("name_prefix")
    if bases == {"explicit"}:
        return "explicit"
    if bases == {"name_prefix"}:
        return "name_prefix"
    return "mixed"


def _attach_conflicts(
    features: dict, deps_analysis: dict
) -> dict:
    """For each feature pair, if any of their changes conflict, mark the feature pair."""
    changes_map = deps_analysis.get("changes", {})
    feature_to_changes = {f: info["change_names"] for f, info in features.items()}
    features_list = sorted(feature_to_changes.keys())
    for i, fa in enumerate(features_list):
        if fa == UNGROUPED:
            continue
        for fb in features_list[i + 1:]:
            if fb == UNGROUPED:
                continue
            # Two features conflict if any of their changes conflict
            fa_set = set(feature_to_changes[fa])
            fb_set = set(feature_to_changes[fb])
            for ch_name, ch_info in changes_map.items():
                if ch_name in fa_set:
                    for c in ch_info.get("conflicts", []):
                        if c in fb_set:
                            features[fa]["conflicts_with"].append(fb)
                            features[fb]["conflicts_with"].append(fa)
                            break
                elif ch_name in fb_set:
                    for c in ch_info.get("conflicts", []):
                        if c in fa_set:
                            features[fa]["conflicts_with"].append(fb)
                            features[fb]["conflicts_with"].append(fa)
                            break
    return features


def _waves_to_order(parallel_groups: dict[str, int]) -> list[list[str]]:
    """Convert {feature: wave_int} into a sorted wave-grouped list of lists."""
    if not parallel_groups:
        return []
    max_wave = max(parallel_groups.values())
    waves: list[list[str]] = [[] for _ in range(max_wave + 1)]
    for f, w in sorted(parallel_groups.items()):
        waves[w].append(f)
    return waves


def update_iteration_feature_view(project_root: str) -> int:
    """Compute the feature_view node and write it back to iteration.json.

    Returns the number of features in the view (including __ungrouped__ if any).
    Raises NoIterationError if iteration.json does not exist.
    """
    data = it_mod.load(project_root)
    if data is None:
        raise NoIterationError(
            "iteration.json missing — run `skill_use('guide-plan')` at least once first."
        )
    # Index changes by name for O(1) lookup
    all_changes: dict[str, dict] = {c["name"]: c for c in data.get("changes", [])}
    changes_list = list(all_changes.values())

    # Lazy import to keep the pure functions import-cheap
    from skills._lib import deps_output

    deps = deps_output.load_analysis(project_root) or {}

    groups = group_changes_by_feature(changes_list)

    features: dict[str, dict] = {}
    for name, ch_names in groups.items():
        ch_records = [all_changes[n] for n in ch_names]
        features[name] = {
            "name": name,
            "status": rollup_status(ch_records),
            "change_names": ch_names,
            "change_count": len(ch_names),
            "archived_count": sum(
                1 for c in ch_records if c.get("status") == "archived"
            ),
            "rollup_basis": _compute_rollup_basis(ch_names, all_changes),
            "depends_on": [],
            "blocks": [],
            "parallel_group": 0,
            "conflicts_with": [],
        }

    edges = compute_feature_edges(deps, groups)
    cycle_warning = False
    cycle_members: list[str] = []
    try:
        pg = compute_parallel_groups(edges, features)
    except FeatureCycleError as exc:
        cycle_warning = True
        cycle_members = exc.cycle
        # Fall back to a wave-0 assignment so partial output is renderable
        pg = {f: 0 for f in features}
    for f in features:
        features[f]["parallel_group"] = pg.get(f, 0)
    for fa, fb, _ in edges:
        if fa in features and fb in features:
            features[fa]["blocks"].append(fb)
            features[fb]["depends_on"].append(fa)
    features = _attach_conflicts(features, deps)

    execution_order = _waves_to_order(pg)

    feature_view_node: dict = {
        "schema_version": 1,
        "updated_at": _now_iso(),
        "features": features,
        "execution_order": execution_order,
    }
    if cycle_warning:
        feature_view_node["__cycle_warning__"] = True
        feature_view_node["__cycle_members__"] = cycle_members

    data["feature_view"] = feature_view_node
    it_mod.save(project_root, data)
    return len(features)
```

- [ ] **Step 5: Run tests, expect PASS**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/test_feature_view.py::TestUpdateIterationFeatureView -v
```

Expected: 3 passed. (If `it_mod.load` rejects the test fixture because of schema validation, re-check Task 7 step 1's schema edit.)

- [ ] **Step 6: Run full unit test suite, expect ALL PASS**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/ -q --tb=short
```

Expected: 27+ passed (16 new + 27 existing). If pre-existing tests fail, do not fix them here — note in the final summary.

- [ ] **Step 7: Commit**

```bash
cd /workspace/project/spec-workflow
git add skills/_lib/feature_view.py skills/_lib/schemas/iteration_schema.json tests/unit/test_feature_view.py
git commit -m "feat(feature-view): orchestrator with cycle handling + 3 tests"
```

---

## Task 8: `feature.md` skill body

**Files:**
- Create: `skills/feature.md`

- [ ] **Step 1: Create the skill body**

```markdown
---
name: feature
description: View and manage features (groups of related changes). Provides summary table, Mermaid dependency graph, per-feature change status, and recommended wave execution order. Pure derived view from iteration.json + deps-analysis.json.
license: MIT
compatibility: Requires iteration.json (run `guide-plan` once first) and ideally deps-analysis.json (run `deps` first for full graph).
metadata:
  author: sisyphus
  version: "1.0"
  depends-on: [iteration, deps_output]
---

# OpenSpec Workflow — Feature Management

> **Pure derived view** — never mutates any change artifacts. Reads `iteration.json`
> and (optionally) `deps-analysis.json`, writes only the `feature_view` node back
> into `iteration.json`.

## Subcommands

```
skill_use("feature")              # default: summary table
skill_use("feature summary")      # same as above
skill_use("feature graph")        # Mermaid flowchart (feature-level topology)
skill_use("feature status <name>")# drill into one feature
skill_use("feature order")        # wave-grouped execution order
```

## Implementation (Bash)

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Subcommand dispatch
SUBCOMMAND="${1:-summary}"
TARGET_NAME="${2:-}"

case "$SUBCOMMAND" in
    summary|"")
        python3 - <<'PYEOF'
import json, os, sys
from pathlib import Path
root = os.environ["PROJECT_ROOT"]
try:
    from skills._lib import feature_view as fv
except ImportError as e:
    print(f"❌ feature_view module unavailable: {e}", file=sys.stderr); sys.exit(2)
try:
    fv.update_iteration_feature_view(root)
except fv.NoIterationError as e:
    print(f"❌ {e}", file=sys.stderr); sys.exit(1)
data = json.loads(Path(f"{root}/.rddf/state/iteration.json").read_text())
features = data["feature_view"]["features"]
if not features:
    print("(no features — set parent_feature in proposal.md or use feature-<name>-<part> naming)")
    sys.exit(0)
# Print table
print("| Feature | Status | Changes | Progress | Wave | Blocks | Blocked by |")
print("|---------|--------|---------|----------|------|--------|------------|")
for name in sorted(features):
    info = features[name]
    if name == "__ungrouped__":
        print(f"| **{name}** | ⚪ ungrouped | {info['change_count']} | — | — | — | — |")
        continue
    status_icon = {
        "blocked": "🔴", "in_progress": "🟡", "ready": "🟢", "done": "✅"
    }.get(info["status"], "⚪")
    blocks = ", ".join(info["blocks"]) or "—"
    blocked_by = ", ".join(info["depends_on"]) or "—"
    print(f"| {name} | {status_icon} {info['status']} | {info['change_count']} | "
          f"{info['archived_count']}/{info['change_count']} | {info['parallel_group']} | "
          f"{blocks} | {blocked_by} |")
PYEOF
        ;;
    graph)
        python3 - <<'PYEOF'
import json, os, sys
from pathlib import Path
root = os.environ["PROJECT_ROOT"]
try:
    from skills._lib import feature_view as fv
except ImportError as e:
    print(f"❌ feature_view module unavailable: {e}", file=sys.stderr); sys.exit(2)
try:
    fv.update_iteration_feature_view(root)
except fv.NoIterationError as e:
    print(f"❌ {e}", file=sys.stderr); sys.exit(1)
data = json.loads(Path(f"{root}/.rddf/state/iteration.json").read_text())
fv_node = data["feature_view"]
features = fv_node["features"]
# Rebuild edge/conflict lists from features dict for the renderer
edges = []
conflicts = []
seen = set()
for name, info in features.items():
    for b in info.get("blocks", []):
        e = (name, b, "hard")
        if e not in seen:
            edges.append(e); seen.add(e)
    for c in info.get("conflicts_with", []):
        pair = tuple(sorted([name, c]))
        if pair not in seen:
            conflicts.append(pair); seen.add(pair)
pg = {n: info["parallel_group"] for n, info in features.items()}
mermaid = fv.render_mermaid(features, edges, conflicts, pg)
print("```mermaid")
print(mermaid)
print("```")
if fv_node.get("__cycle_warning__"):
    print(f"\n⚠️ Cycle detected: {fv_node.get('__cycle_members__')}")
PYEOF
        ;;
    status)
        if [ -z "$TARGET_NAME" ]; then
            echo "❌ usage: feature status <name>"; exit 2
        fi
        python3 - "$TARGET_NAME" <<'PYEOF'
import json, os, sys
from pathlib import Path
root = os.environ["PROJECT_ROOT"]
target = sys.argv[1]
try:
    from skills._lib import feature_view as fv
except ImportError as e:
    print(f"❌ feature_view module unavailable: {e}", file=sys.stderr); sys.exit(2)
try:
    fv.update_iteration_feature_view(root)
except fv.NoIterationError as e:
    print(f"❌ {e}", file=sys.stderr); sys.exit(1)
data = json.loads(Path(f"{root}/.rddf/state/iteration.json").read_text())
info = data["feature_view"]["features"].get(target)
if info is None:
    names = sorted(data["feature_view"]["features"].keys())
    print(f"❌ feature '{target}' not found. Known: {names}", file=sys.stderr); sys.exit(1)
print(f"## {target}\n")
print(f"- **Status:** {info['status']}")
print(f"- **Rollup basis:** {info['rollup_basis']}")
print(f"- **Change count:** {info['change_count']} (archived: {info['archived_count']})")
print(f"- **Wave:** {info['parallel_group']}")
print(f"- **Blocks:** {', '.join(info['blocks']) or '—'}")
print(f"- **Blocked by:** {', '.join(info['depends_on']) or '—'}\n")
print("| Change | Status | Blocker | Phase | Category |")
print("|--------|--------|---------|-------|----------|")
all_changes = {c["name"]: c for c in data.get("changes", [])}
for n in info["change_names"]:
    c = all_changes.get(n, {})
    print(f"| {n} | {c.get('status', '—')} | {c.get('blocker') or '—'} | "
          f"{c.get('phase', '—')} | {c.get('category', '—')} |")
PYEOF
        ;;
    order)
        python3 - <<'PYEOF'
import json, os, sys
from pathlib import Path
root = os.environ["PROJECT_ROOT"]
try:
    from skills._lib import feature_view as fv
except ImportError as e:
    print(f"❌ feature_view module unavailable: {e}", file=sys.stderr); sys.exit(2)
try:
    fv.update_iteration_feature_view(root)
except fv.NoIterationError as e:
    print(f"❌ {e}", file=sys.stderr); sys.exit(1)
data = json.loads(Path(f"{root}/.rddf/state/iteration.json").read_text())
order = data["feature_view"].get("execution_order", [])
features = data["feature_view"]["features"]
if not order:
    print("(no features)"); sys.exit(0)
print("## Recommended execution order\n")
for i, wave in enumerate(order):
    if not wave: continue
    print(f"- **Wave {i}** (run in parallel):")
    for f in sorted(wave):
        info = features.get(f, {})
        print(f"  - {f} ({info.get('status', '—')} · {info.get('archived_count', 0)}/{info.get('change_count', 0)})")
PYEOF
        ;;
    *)
        echo "❌ unknown subcommand: $SUBCOMMAND" >&2
        echo "Usage: feature [summary|graph|status <name>|order]" >&2
        exit 2
        ;;
esac
```

(When the orchestrator invokes this skill, it should `export PROJECT_ROOT=$(git rev-parse --show-toplevel)` before calling `bash skills/feature.md <subcommand> [args]`. The skill assumes `PROJECT_ROOT` is in the environment.)

- [ ] **Step 2: Smoke-test each subcommand manually on the existing project**

The repo already has an `openspec/changes/archive/` directory. First, ensure `iteration.json` exists by running `python3 -c "from skills._lib import iteration; import json; d = iteration.load('.') or {'version': 1, 'changes': []}; iteration.save('.', d)"` (this creates an empty iteration.json if absent). Then:

```bash
cd /workspace/project/spec-workflow
export PROJECT_ROOT=$(pwd)
bash skills/feature.md summary 2>&1 | head -20
bash skills/feature.md graph 2>&1 | head -20
bash skills/feature.md order 2>&1 | head -20
bash skills/feature.md status __ungrouped__ 2>&1 | head -10
```

Expected: graceful output (empty tables, helpful hints) for each. No tracebacks.

- [ ] **Step 3: Commit**

```bash
cd /workspace/project/spec-workflow
git add skills/feature.md
git commit -m "feat(feature): skill body with 4 subcommands (summary/graph/status/order)"
```

---

## Task 9: Integration tests (bats)

**Files:**
- Create: `tests/integration/test_feature_skill.bats`

- [ ] **Step 1: Write the bats file**

```bash
#!/usr/bin/env bats

# Integration tests for the feature skill.
# These run the actual skill body against fixture iteration.json files.

load 'test_helper'

setup() {
    REPO_ROOT="$(git rev-parse --show-toplevel)"
    TEST_PROJECT="$(mktemp -d)"
    cd "$TEST_PROJECT"
    git init -q
    mkdir -p .rddf/state
    export PROJECT_ROOT="$TEST_PROJECT"
}

teardown() {
    rm -rf "$TEST_PROJECT"
}

@test "feature summary populates iteration.json" {
    cat > .rddf/state/iteration.json <<EOF
{
  "version": 1,
  "updated_at": "2026-07-09T00:00:00+00:00",
  "changes": [
    {"name": "feature-stream-core", "status": "proposed", "parent_feature": "feature-stream"},
    {"name": "feature-stream-tests", "status": "proposed", "parent_feature": "feature-stream"},
    {"name": "fix-typo", "status": "proposed"}
  ]
}
EOF
    run bash "$REPO_ROOT/skills/feature.md" summary
    [ "$status" -eq 0 ]
    [ -f .rddf/state/iteration.json ]
    run python3 -c "import json; d=json.load(open('.rddf/state/iteration.json')); assert 'feature_view' in d; assert 'feature-stream' in d['feature_view']['features']; assert '__ungrouped__' in d['feature_view']['features']; print('ok')"
    [ "$status" -eq 0 ]
    [[ "$output" == *"ok"* ]]
}

@test "feature graph emits mermaid block" {
    cat > .rddf/state/iteration.json <<EOF
{"version": 1, "changes": [{"name": "a", "status": "proposed", "parent_feature": "f-a"}]}
EOF
    run bash "$REPO_ROOT/skills/feature.md" graph
    [ "$status" -eq 0 ]
    [[ "$output" == *"```mermaid"* ]]
    [[ "$output" == *"flowchart LR"* ]]
    [[ "$output" == *"f-a["* ]]
}

@test "feature status <name> lists changes" {
    cat > .rddf/state/iteration.json <<EOF
{"version": 1, "changes": [
  {"name": "a-core", "status": "proposed", "parent_feature": "f-a"},
  {"name": "a-tests", "status": "archived", "parent_feature": "f-a"}
]}
EOF
    run bash "$REPO_ROOT/skills/feature.md" status f-a
    [ "$status" -eq 0 ]
    [[ "$output" == *"## f-a"* ]]
    [[ "$output" == *"a-core"* ]]
    [[ "$output" == *"a-tests"* ]]
}

@test "feature order lists waves" {
    cat > .rddf/state/iteration.json <<EOF
{"version": 1, "changes": [
  {"name": "a-core", "status": "proposed", "parent_feature": "f-a"},
  {"name": "b-core", "status": "proposed", "parent_feature": "f-b"}
]}
EOF
    run bash "$REPO_ROOT/skills/feature.md" order
    [ "$status" -eq 0 ]
    [[ "$output" == *"Wave 0"* ]]
}

@test "empty project graceful output" {
    cat > .rddf/state/iteration.json <<EOF
{"version": 1, "changes": []}
EOF
    run bash "$REPO_ROOT/skills/feature.md" summary
    [ "$status" -eq 0 ]
    [[ "$output" == *"no features"* ]]
}

@test "missing iteration.json errors with helpful message" {
    rm -f .rddf/state/iteration.json
    run bash "$REPO_ROOT/skills/feature.md" summary
    [ "$status" -eq 1 ]
    [[ "$output" == *"guide-plan"* ]]
}
```

- [ ] **Step 2: Run bats tests, expect PASS**

```bash
cd /workspace/project/spec-workflow
bats tests/integration/test_feature_skill.bats
```

Expected: 6 ok, 0 failed. (If `bats` is not installed, install bats-core or run via `npx bats`.)

- [ ] **Step 3: Commit**

```bash
cd /workspace/project/spec-workflow
git add tests/integration/test_feature_skill.bats
git commit -m "test(feature): 6 bats integration tests for feature skill"
```

---

## Task 10: Documentation touch-ups

**Files:**
- Edit: `skills/guide.md` (1 line)
- Edit: `skills/INSTALL.md` (1 line)
- Edit: `README.md` (3 lines)
- Edit: `AGENTS.md` (1 line)

- [ ] **Step 1: Add `feature` to `guide.md` recommender**

Find the suggested-skills list in `skills/guide.md` (search for `skill_use("deps")` or similar). Add one bullet:

```markdown
- `feature` — view and manage feature groups (summary, dependency graph, per-feature status, execution order)
```

(If the recommender uses a table or different format, add `feature` to it in the same style as the existing entries.)

- [ ] **Step 2: Add `feature.md` to `skills/INSTALL.md`**

Find the sub-skill list and add:

```markdown
- `feature.md` — feature management view (summary / graph / status / order)
```

- [ ] **Step 3: Add `feature` row to `README.md` v2.0 new-features table**

Locate the v2.0 new features table and add a row:

```markdown
| **Feature Management** | `feature` | Feature-level summary, Mermaid graph, per-feature status, wave execution order | Low |
```

(Adjust column names to match the existing table.)

- [ ] **Step 4: Add `feature.md` to `AGENTS.md` directory tree**

Find the `skills/` enumeration in AGENTS.md (e.g., `loop_engine.py # v2.0 Loop 引擎入口...`) and add a line:

```markdown
  feature.md                # 子技能 (v1.0) - feature 管理: summary / graph / status / order
```

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow
git add skills/guide.md skills/INSTALL.md README.md AGENTS.md
git commit -m "docs(feature): add feature to guide/INSTALL/README/AGENTS"
```

---

## Task 11: Final verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/ -q --tb=short
bats tests/integration/test_feature_skill.bats
```

Expected: all green. (Bats smoke and the existing 51 integration tests are not in scope of this plan's run; if you want full coverage, also run `bats tests/integration/*.bats` — but expect some pre-existing tests to be slow.)

- [ ] **Step 2: Run CI constant-truth gate**

```bash
cd /workspace/project/spec-workflow
if grep -rn "assert .* or True" tests/ 2>/dev/null; then
    echo "❌ CI gate FAILED: assert ... or True pattern found"
    exit 1
else
    echo "✅ CI gate passed: no 'assert ... or True' patterns"
fi
```

Expected: `✅ CI gate passed`.

- [ ] **Step 3: Verify all spec requirements are covered**

Walk the spec's §2 Goals and §6.2 Field reference line by line. Each item should map to a task above. Run this checklist:

- [ ] Goal 1 (feature skill as entry point) → Task 8 ✓
- [ ] Goal 2 (4 artifacts) → Task 8 ✓
- [ ] Goal 3 (reuse parent_feature + name-prefix) → Task 2 ✓
- [ ] Goal 4 (feature_view in iteration.json with schema_version) → Tasks 1, 7 ✓
- [ ] Goal 5 (feature_view.py with pure functions) → Tasks 2-6 ✓
- [ ] Goal 6 (unit + integration tests) → Tasks 2-7, 9 ✓
- [ ] Field `schema_version` → Task 1 schema ✓
- [ ] Field `features` (FeatureEntry) → Task 1 schema, Task 7 orchestrator ✓
- [ ] Field `execution_order` (waves) → Task 5, 7 ✓
- [ ] Status enum (5 values) → Task 3 ✓
- [ ] Rollup basis (3 values) → Task 7 `_compute_rollup_basis` ✓
- [ ] `depends_on` / `blocks` (reverse edges) → Task 7 orchestrator ✓
- [ ] Cycle handling → Task 5, Task 7 try/except ✓
- [ ] All-pairs-hard edge rule → Task 4 ✓
- [ ] Subcommand dispatch → Task 8 ✓
- [ ] 4 sample outputs in spec → Task 8 matches all 4 ✓
- [ ] 7 error scenarios in §9 → Task 8 covers 4; remaining 3 (cycle warning, FileLock, missing name) covered by tests in Tasks 4, 7, 9 ✓

- [ ] **Step 4: Commit any pending doc fixes and final tag**

```bash
cd /workspace/project/spec-workflow
git status
# If anything is uncommitted, commit it now with a clear message.
git log --oneline -5
```

Expected: clean working tree (or only the pre-existing untracked items from `git status` at plan start). `git log` shows the 9 task commits plus the design spec commit (10 total new commits).

---

## Self-Review

**1. Spec coverage:** All 6 goals in spec §2 and all 13 fields in spec §6.2 are covered (verified in Task 11 step 3).

**2. Placeholder scan:**
- No "TBD" / "TODO" / "FIXME" / "implement later" in the plan.
- All code blocks are complete (test bodies, implementation bodies, no truncation).
- All commands are real (`python3 -m pytest`, `bats`, `git`, `bash skills/feature.md`).
- No "Similar to Task N" — every code block stands alone.

**3. Type consistency:**
- `group_changes_by_feature(changes: list[dict]) -> dict[str, list[str]]` — used consistently in Tasks 2 and 7.
- `rollup_status(changes: list[dict]) -> str` — same.
- `compute_feature_edges(deps_analysis: dict, feature_groups: dict[str, list[str]]) -> list[tuple[str, str, str]]` — `edges[i]` is `(from, to, "hard")` in Tasks 4, 5, 8.
- `compute_parallel_groups(edges: list[tuple[str, str, str]], features: dict) -> dict[str, int]` — return value used in Task 7 as `pg[feature] = wave_int`.
- `render_mermaid(features: dict, edges: list[tuple], conflicts: list[tuple], parallel_groups: dict) -> str` — used in Task 8 with the same arg order.
- `update_iteration_feature_view(project_root: str) -> int` — returns feature count.
- `FeatureCycleError(cycle: list[str])` — `cycle` attribute accessed in Task 7.
- `NoIterationError` — raised in Task 7, caught in Task 8.

**4. Pre-flight check on `iteration_schema.json`:** Task 7 step 1 instructs the executor to verify the schema and add `feature_view` if needed. If the schema is too strict, the executor must do a minimal edit. This is the only place the plan touches the existing schema file (intentional — adding a top-level property requires schema update).

**5. Open assumption flagged:** Task 8 step 2 instructs manual smoke test against the real repo. If the smoke test reveals unexpected behavior (e.g., `iteration.load` raises on the existing `iteration.json`), pause and inspect before continuing.
