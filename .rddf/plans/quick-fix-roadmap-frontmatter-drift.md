# quick-fix-roadmap-frontmatter-drift — Roadmap Document System Drift Fixes

> rdd-quick plan (per ADR-0047): bypass openspec change, in-place execution.
> AC source = this file's `## Acceptance` section.

## Goal

Fix two confirmed drift bugs in the roadmap document system discovered during
pre-planning audit (2026-09-28):

1. **X1 — Silent data loss in phase fragment frontmatter**: parser
   `_lib/roadmap_state.py::_parse_fragment_file` is a naive line-based parser
   that **last-wins silently** on duplicate YAML keys. Phase fragments have
   2-3 duplicate `主题:` keys; only the last theme survives. AUTO-INDEX
   therefore shows only 1 theme per phase, while the main doc Phase Skeleton
   table lists 4 themes per phase.

2. **X3 — Two writers, 90 lines of duplicated code, one missing sentinel**:
   `AGENTS.md` has TWO `AUTO:` sentinel blocks (feature fragments + objectives)
   written by TWO different code paths:
   - feature fragments → `_lib/roadmap_state.py::update_agent_md`
   - objectives → `planner_stage_exit.sh` inline Python (~60 lines)
   And `planner_stage_entry.sh` + `planner_stage_exit.sh` each contain the
   same ~45 lines of inline Python that parses objectives and serializes
   them as JSON. Exit's comment self-acknowledges:
   `Mirrors the same parser logic in planner_stage_entry.sh`.

## Acceptance

- [ ] **AC-1**: `_parse_fragment_file` raises a clear error (or warning) when
  frontmatter contains duplicate keys; does NOT silently keep only the last
- [ ] **AC-2**: `_parse_fragment_file` correctly parses `主题: [a, b, c]` array
  syntax; returns `Fragment.themes` as a list (preserving all themes)
- [ ] **AC-3**: All 4 existing `.rddf/roadmap/phases/phase-N.md` files are
  migrated from multi-`主题:` lines to single `主题: [...]` array; AUTO-INDEX
  rendering shows all themes (not just the last)
- [ ] **AC-4**: Fragment writer template (currently `f"主题: {theme}\n"`)
  emits array form for multi-theme fragments
- [ ] **AC-5**: A new `_lib/objective_parser.py::collect_active_objectives(project_root)`
  function exists, returning the same JSON shape as the inline Python does
  today (`[{id, priority, status, review_by, theme, next_sprint_candidates}]`)
- [ ] **AC-6**: `planner_stage_entry.sh` and `planner_stage_exit.sh` no longer
  contain inline Python for objective parsing; both call
  `_lib.objective_parser.collect_active_objectives` (or shell equivalent)
- [ ] **AC-7**: A new `_lib/roadmap_state.py::update_objectives_sentinel(project_root)`
  function exists that mirrors the `update_agent_md` pattern; rewrites the
  AGENTS.md `<!-- AUTO: objectives start/end -->` block atomically
- [ ] **AC-8**: `planner_stage_exit.sh` no longer contains inline Python for
  AGENTS.md sentinel refresh; calls `_lib.roadmap_state.update_objectives_sentinel`
- [ ] **AC-9**: All existing tests still pass (`pytest tests/unit/ -q`); new
  tests cover AC-1 through AC-8
- [ ] **AC-10**: Existing behavior preserved: `rdd roadmap list-features`,
  `rdd roadmap validate-fragments`, `rddf planner handoff` all produce
  identical output for unchanged inputs

## Files

### Create
| Path | Purpose |
|------|---------|
| `_lib/objective_parser.py` | `collect_active_objectives(project_root)` — extracts active/deferred objectives from `.rddf/roadmap/objectives/` as JSON |
| `tests/unit/test_objective_parser.py` | ≥5 tests covering happy path, no objectives, malformed objective, N/A filtering, status filter |
| `tests/unit/test_roadmap_state_duplicate_keys.py` | ≥3 tests covering duplicate-key detection, array `主题:` parsing, multi-theme `Fragment.themes` return |

### Modify
| Path | Change |
|------|--------|
| `_lib/roadmap_state.py` | (1) Add duplicate-key detection in `_parse_fragment_file`; (2) Add `主题: [a, b, c]` array parsing; (3) Add `Fragment.themes: list[str]` field; (4) Update single-`主题:` writer template to emit array form; (5) Add `update_objectives_sentinel(project_root)` mirroring `update_agent_md` |
| `.rddf/roadmap/phases/phase-1.md` | Migrate 3 `主题:` lines → `主题: [完整多会话支持, 定时循环与事件触发, 提案生成阶段 — 自动跨仓分析]` |
| `.rddf/roadmap/phases/phase-2.md` | Migrate 3 `主题:` lines → array |
| `.rddf/roadmap/phases/phase-3.md` | Migrate 2 `主题:` lines → array |
| `.rddf/roadmap/phases/phase-4.md` | Migrate 2 `主题:` lines → array (note: contains near-duplicate "多方对称与回归" vs "多方对称 + 回归") |
| `skills/rdd-planner/scripts/planner_stage_entry.sh` | Remove L30-83 inline Python; call `_lib.objective_parser.collect_active_objectives` via small `python3 -c` shim |
| `skills/rdd-planner/scripts/planner_stage_exit.sh` | Remove L48-211 inline Python (objective parsing + AGENTS.md refresh); call `_lib.objective_parser.collect_active_objectives` and `_lib.roadmap_state.update_objectives_sentinel` |

## TDD 5-Step Tasks

### Task 1 — Fragment parser: duplicate-key detection + array support (X1 fix, AC-1/2/4)

**Files:**
- Modify: `_lib/roadmap_state.py:618-660` (`_parse_fragment_file`)
- Modify: `_lib/roadmap_state.py:894` (writer template)
- Test: `tests/unit/test_roadmap_state_duplicate_keys.py` (create)

- [ ] **Step 1: Write the failing test** — `test_parse_fragment_detects_duplicate_keys`:
  ```python
  def test_parse_fragment_detects_duplicate_keys(tmp_path):
      """Duplicate keys should be detected, not silently dropped."""
      md = tmp_path / "phase-bad.md"
      md.write_text(
          "---\n"
          "id: phase-bad\n"
          "kind: phase\n"
          "主题: first theme\n"
          "主题: second theme\n"
          "主题: third theme\n"
          "---\n\nbody\n",
          encoding="utf-8",
      )
      from _lib.roadmap_state import _parse_fragment_file
      with pytest.raises(ValueError, match="duplicate key"):
          _parse_fragment_file(md)
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/unit/test_roadmap_state_duplicate_keys.py::test_parse_fragment_detects_duplicate_keys -v`
  Expected: FAIL — current parser silently keeps the last value, no error raised.

- [ ] **Step 3: Write minimal implementation** — modify `_parse_fragment_file`:
  ```python
  # Replace the frontmatter loop (L637-654):
  seen_keys: set[str] = set()
  for line in fm_text.splitlines():
      if ":" not in line:
          continue
      k, v = line.split(":", 1)
      k, v = k.strip(), v.strip()
      if not k:
          continue
      if k in seen_keys:
          raise ValueError(
              f"duplicate frontmatter key {k!r} in {path}. "
              f"Use array syntax ({k}: [v1, v2, ...]) for repeated values."
          )
      seen_keys.add(k)
      # ... rest unchanged
  ```
  Also extend `Fragment` dataclass to add `themes: list[str] = field(default_factory=list)`;
  after the loop, populate `themes` from `主题` value (split list literal OR split multiple non-list values into list).

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/unit/test_roadmap_state_duplicate_keys.py -v`
  Expected: PASS for `test_parse_fragment_detects_duplicate_keys`,
  plus 2 more tests: `test_parse_fragment_array_theme_syntax`, `test_fragment_themes_field_preserves_order`.

- [ ] **Step 5: Defer commit**
  Skip per repo convention; commit happens after all 5 tasks land.

---

### Task 2 — Migrate phase-N.md files to array syntax (X1 data fix, AC-3)

**Files:**
- Modify: `.rddf/roadmap/phases/phase-1.md` (3 → array)
- Modify: `.rddf/roadmap/phases/phase-2.md` (3 → array)
- Modify: `.rddf/roadmap/phases/phase-3.md` (2 → array)
- Modify: `.rddf/roadmap/phases/phase-4.md` (2 → array, **includes near-duplicate** "多方对称与回归" vs "多方对称 + 回归 (P1-P3, 后续)" — flag for user review before merging)

- [ ] **Step 1: Write the failing test** — `test_phase_fragments_use_array_theme`:
  ```python
  def test_phase_fragments_use_array_theme():
      """All phase-N.md files use 主题: [array] syntax, no duplicate keys."""
      from pathlib import Path
      from collections import Counter
      phases_dir = Path(".rddf/roadmap/phases")
      assert phases_dir.is_dir()
      for phase_md in sorted(phases_dir.glob("phase-*.md")):
          content = phase_md.read_text(encoding="utf-8")
          fm = content.split("---", 2)[1]
          key_counts = Counter(line.split(":", 1)[0].strip() for line in fm.splitlines() if ":" in line)
          assert key_counts["主题"] <= 1, f"{phase_md}: duplicate 主题 keys"
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/unit/test_roadmap_state_duplicate_keys.py::test_phase_fragments_use_array_theme -v`
  Expected: FAIL — current phase-1..4 have 2-3 duplicate keys each.

- [ ] **Step 3: Migrate files** — for each phase-N.md, replace multiple `主题: <value>` lines with a single `主题: [<v1>, <v2>, ...]` array line. Use exact text from each file's current content (preserving order). Special handling for phase-4.md near-duplicates: keep both, but flag for user review in commit message.

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/unit/test_roadmap_state_duplicate_keys.py::test_phase_fragments_use_array_theme -v`
  Expected: PASS. Plus manually verify: `python3 -c "from _lib.roadmap_state import _parse_fragment_file; from pathlib import Path; [print(p.stem, _parse_fragment_file(p).themes) for p in sorted(Path('.rddf/roadmap/phases').glob('phase-*.md'))]"`

- [ ] **Step 5: Defer commit**

---

### Task 3 — Extract objective parser to `_lib/objective_parser.py` (X3 fix, AC-5)

**Files:**
- Create: `_lib/objective_parser.py`
- Create: `tests/unit/test_objective_parser.py`

- [ ] **Step 1: Write the failing test** — `test_collect_active_objectives_happy_path`:
  ```python
  def test_collect_active_objectives_happy_path(tmp_path):
      """Returns JSON list of active+deferred objectives with next_sprint_candidates."""
      obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
      obj_dir.mkdir(parents=True)
      (obj_dir / "objective-test.md").write_text(
          "---\n"
          "id: objective-test\nstatus: active\ncreated: 2026-09-28\n"
          "last_revised: 2026-09-28\nreview_by: 2026-12-27\nowner: rdd-planner\n"
          "priority: P1\nmanual_deps: []\ntheme: test theme\n"
          "---\n\n"
          "## 10. next_sprint_candidates\n- [ ] candidate A\n- [ ] candidate B\n",
          encoding="utf-8",
      )
      from _lib.objective_parser import collect_active_objectives
      import json
      result = json.loads(collect_active_objectives(tmp_path))
      assert len(result) == 1
      assert result[0]["id"] == "objective-test"
      assert result[0]["next_sprint_candidates"] == ["candidate A", "candidate B"]
  ```
  Plus 4 more tests: empty directory, malformed objective skipped, deferred+active filter, N/A filter.

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/unit/test_objective_parser.py -v`
  Expected: FAIL — `_lib.objective_parser` doesn't exist yet (ModuleNotFoundError).

- [ ] **Step 3: Implement** — `_lib/objective_parser.py`:
  ```python
  """Collect active/deferred objectives as JSON for LLM handoff payloads.

  Mirrors the inline Python previously in planner_stage_entry.sh and
  planner_stage_exit.sh (60 lines × 2 = 120 lines duplicated). Per add-improve
  X3: consolidate to single source of truth.
  """
  from __future__ import annotations
  import json
  import sys
  from pathlib import Path

  def collect_active_objectives(project_root: Path | str) -> str:
      """Return JSON string of active/deferred objectives for LLM consumption.

      Each record: {id, priority, status, review_by, theme, next_sprint_candidates}.
      Returns "[]" on any error (graceful degradation, mirrors previous behavior).
      Excludes archive/ subdirectory. Filters out 'N/A — <reason>' markers
      from next_sprint_candidates (per D9).
      """
      project_root = Path(project_root)
      obj_dir = project_root / ".rddf" / "roadmap" / "objectives"
      if not obj_dir.is_dir():
          return "[]"
      sys.path.insert(0, str(project_root))
      try:
          from _lib.objective import parse_objective
      except ImportError:
          return "[]"
      records = []
      for f in sorted(obj_dir.glob("*.md")):
          if f.parent.name == "archive":
              continue
          try:
              data = parse_objective(f)
          except (ValueError, OSError):
              continue
          fm = data.get("frontmatter", {})
          if fm.get("status") not in ("active", "deferred"):
              continue
          candidates = []
          sec10 = data.get("sections", {}).get("## 10.", "")
          for line in sec10.splitlines():
              s = line.strip()
              if s.startswith("- [ ]"):
                  candidates.append(s[5:].strip())
              elif s.startswith("- "):
                  candidates.append(s[2:].strip())
          candidates = [c for c in candidates if c and not c.startswith("N/A")]
          records.append({
              "id": fm.get("id", f.stem),
              "priority": fm.get("priority", "?"),
              "status": fm.get("status", "?"),
              "review_by": fm.get("review_by", ""),
              "theme": fm.get("theme", "")[:200],
              "next_sprint_candidates": candidates,
          })
      return json.dumps(records, ensure_ascii=False)
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/unit/test_objective_parser.py -v`
  Expected: 5 PASS.

- [ ] **Step 5: Defer commit**

---

### Task 4 — Unify AGENTS.md objectives sentinel writer (X3 second fix, AC-7)

**Files:**
- Modify: `_lib/roadmap_state.py` (add `update_objectives_sentinel` after `update_agent_md`)
- Test: `tests/unit/test_roadmap_state_duplicate_keys.py` (extend)

- [ ] **Step 1: Write the failing test** — `test_update_objectives_sentinel`:
  ```python
  def test_update_objectives_sentinel_writes_block(tmp_path):
      """update_objectives_sentinel writes the AUTO: objectives block to AGENTS.md."""
      obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
      obj_dir.mkdir(parents=True)
      (obj_dir / "objective-test.md").write_text(
          "---\n"
          "id: objective-test\nstatus: active\npriority: P1\ntheme: t\n"
          "---\n",
          encoding="utf-8",
      )
      agents = tmp_path / "AGENTS.md"
      agents.write_text("# AGENTS\n\n<!-- before -->\n", encoding="utf-8")
      from _lib.roadmap_state import update_objectives_sentinel
      update_objectives_sentinel(tmp_path)
      content = agents.read_text(encoding="utf-8")
      assert "<!-- AUTO: objectives start -->" in content
      assert "<!-- AUTO: objectives end -->" in content
      assert "objective-test" in content
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest tests/unit/test_roadmap_state_duplicate_keys.py::test_update_objectives_sentinel_writes_block -v`
  Expected: FAIL — `update_objectives_sentinel` doesn't exist (ImportError).

- [ ] **Step 3: Implement** — append to `_lib/roadmap_state.py` after `update_agent_md`:
  ```python
  AGENTS_OBJECTIVES_SENTINEL_START = "<!-- AUTO: objectives start -->"
  AGENTS_OBJECTIVES_SENTINEL_END = "<!-- AUTO: objectives end -->"

  def update_objectives_sentinel(project_root: Path | str) -> bool:
      """Rewrite AGENTS.md AUTO: objectives sentinel block.

      Mirrors update_agent_md() pattern. Reads .rddf/roadmap/objectives/*.md,
      generates a table (id | priority | status | theme | review_by), and
      replaces the sentinel block atomically. Returns True on success.

      Per rdd-planner SKILL.md L157: only rdd-planner invokes this.
      """
      from _lib.objective import parse_objective  # stdlib re + yaml in _lib/objective.py
      project_root = Path(project_root)
      obj_dir = project_root / ".rddf" / "roadmap" / "objectives"
      agents_md = project_root / "AGENTS.md"
      if not obj_dir.is_dir() or not agents_md.exists():
          return False
      rows = []
      for f in sorted(obj_dir.glob("*.md")):
          if f.parent.name == "archive":
              continue
          try:
              data = parse_objective(f)
          except (ValueError, OSError):
              continue
          fm = data.get("frontmatter", {})
          if fm.get("status") not in ("active", "deferred", "completed"):
              continue
          rows.append(
              f"| {fm.get('id', f.stem)} | {fm.get('priority', '?')} | "
              f"{fm.get('status', '?')} | {fm.get('theme', '')[:80]} | "
              f"{fm.get('review_by', '')} |"
          )
      table = (
          "| ID | Priority | Status | Theme | Review By |\n"
          "|-----|----------|--------|-------|-----------|"
          + ("\n" + "\n".join(rows) if rows else "\n_(none)_")
      )
      new_block = (
          f"{AGENTS_OBJECTIVES_SENTINEL_START}\n\n"
          f"{table}\n\n"
          f"{AGENTS_OBJECTIVES_SENTINEL_END}"
      )
      # Atomic rewrite of sentinel block (mirrors update_agent_md pattern, L1071-1100)
      content = agents_md.read_text(encoding="utf-8")
      if AGENTS_OBJECTIVES_SENTINEL_START in content and AGENTS_OBJECTIVES_SENTINEL_END in content:
          start_idx = content.index(AGENTS_OBJECTIVES_SENTINEL_START)
          end_idx = content.index(AGENTS_OBJECTIVES_SENTINEL_END, start_idx) + len(AGENTS_OBJECTIVES_SENTINEL_END)
          new_content = content[:start_idx] + new_block + content[end_idx:]
      else:
          # Append at end if no existing block (idempotent bootstrap)
          new_content = content.rstrip() + "\n\n" + new_block + "\n"
      agents_md.write_text(new_content, encoding="utf-8")
      return True
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `pytest tests/unit/test_roadmap_state_duplicate_keys.py::test_update_objectives_sentinel_writes_block -v`
  Expected: PASS.

- [ ] **Step 5: Defer commit**

---

### Task 5 — Strip inline Python from planner stage scripts (X3 third fix, AC-6/8)

**Files:**
- Modify: `skills/rdd-planner/scripts/planner_stage_entry.sh:30-83`
- Modify: `skills/rdd-planner/scripts/planner_stage_exit.sh:48-211`
- Test: `tests/integration/test_planner_stage_scripts.sh` (or extend existing)

- [ ] **Step 1: Write the failing test** — `test_planner_stage_scripts_no_inline_python`:
  ```bash
  #!/usr/bin/env bats
  @test "planner_stage_entry.sh has no inline Python for objective parsing" {
      ! grep -q "from _lib.objective import parse_objective" skills/rdd-planner/scripts/planner_stage_entry.sh
  }
  @test "planner_stage_exit.sh has no inline Python for objective parsing" {
      ! grep -q "from _lib.objective import parse_objective" skills/rdd-planner/scripts/planner_stage_exit.sh
  }
  @test "planner_stage_exit.sh has no inline Python for AGENTS.md sentinel" {
      ! grep -q "AGENTS_OBJECTIVES_SENTINEL_START\|AUTO: objectives start" skills/rdd-planner/scripts/planner_stage_exit.sh
  }
  @test "planner_stage_entry.sh ACTIVE_OBJECTIVES_JSON still populated" {
      # Mock rddf CLI + run stage entry, assert ACTIVE_OBJECTIVES_JSON contains expected JSON
      cd "$TEST_TMPDIR"
      mkdir -p .rddf/roadmap/objectives
      cat > .rddf/roadmap/objectives/objective-x.md <<EOF
  ---
  id: objective-x
  status: active
  priority: P1
  theme: test
  ---
  ## 10. next_sprint_candidates
  - [ ] c1
  EOF
      source skills/rdd-planner/scripts/planner_stage_entry.sh test-change 2>/dev/null
      [ -n "$ACTIVE_OBJECTIVES_JSON" ]
      echo "$ACTIVE_OBJECTIVES_JSON" | grep -q "objective-x"
  }
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `bats tests/integration/test_planner_stage_scripts_no_inline_python.sh -v`
  Expected: FAIL — current scripts contain inline Python.

- [ ] **Step 3: Refactor scripts**:
  - In `planner_stage_entry.sh`: replace L30-83 (~45 lines inline Python) with:
    ```bash
    ACTIVE_OBJECTIVES_JSON=$(PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
    import os, sys
    sys.path.insert(0, os.environ.get('PROJECT_ROOT', '.'))
    from _lib.objective_parser import collect_active_objectives
    print(collect_active_objectives(os.environ.get('PROJECT_ROOT', '.')))
    " 2>/dev/null || echo "[]")
    ```
  - In `planner_stage_exit.sh`: replace L48-118 (~45 lines inline Python) with the same shim, plus replace L120-211 (AGENTS.md refresh) with:
    ```bash
    PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
    import os, sys
    sys.path.insert(0, os.environ.get('PROJECT_ROOT', '.'))
    from _lib.roadmap_state import update_objectives_sentinel
    update_objectives_sentinel(os.environ.get('PROJECT_ROOT', '.'))
    " 2>/dev/null || true
    ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `bats tests/integration/test_planner_stage_scripts_no_inline_python.sh -v`
  Expected: 4 PASS.

- [ ] **Step 5: Defer commit**

---

## Verification (after all 5 tasks)

```bash
# Unit tests
python3 -m pytest tests/unit/test_roadmap_state_duplicate_keys.py tests/unit/test_objective_parser.py -v

# Full unit baseline (must stay green)
python3 -m pytest tests/unit/ -q --tb=line

# Integration tests for planner stage scripts
bats tests/integration/test_planner_stage_scripts_no_inline_python.sh -v

# Manual smoke
cd "$(mktemp -d)" && git clone -q "$(git -C /workspace/project/rdd-workflow rev-parse --show-toplevel)" rdd-clone
cd rdd-clone
# Verify phase fragments parse with all themes
python3 -c "from _lib.roadmap_state import _parse_fragment_file; from pathlib import Path; [print(p.stem, _parse_fragment_file(p).themes) for p in sorted(Path('.rddf/roadmap/phases').glob('phase-*.md'))]"
# Verify objectives sentinel refresh
python3 -c "from _lib.roadmap_state import update_objectives_sentinel; update_objectives_sentinel('.')"

# Regression baseline
./test.sh --quick
```

## Commit Strategy

Per repo convention, single aggregate commit at end (not per-task). Commit
message format:

```
fix(roadmap): phase fragment duplicate-key detection + objectives parser extraction

Two drift bugs confirmed via pre-planning audit (2026-09-28):

X1: phase frontmatter duplicate YAML keys silently last-wins
  - _lib/roadmap_state.py::_parse_fragment_file naive parser kept only the
    last `主题:` value, dropping 1-2 themes per phase fragment
  - AUTO-INDEX rendering showed 1 theme per phase; main doc Phase Skeleton
    listed 2-4 themes per phase
  - Fixed by adding duplicate-key detection + array syntax support
  - All 4 phase-N.md files migrated to `主题: [a, b, c]` array form

X3: AGENTS.md dual sentinel writers + duplicated Python
  - Feature fragments sentinel: _lib/roadmap_state.py::update_agent_md
  - Objectives sentinel: planner_stage_exit.sh inline Python (~60 lines)
  - planner_stage_entry.sh + planner_stage_exit.sh each had ~45 lines
    identical inline Python for objective parsing
  - Fixed by extracting _lib/objective_parser.py::collect_active_objectives
    and _lib/roadmap_state.py::update_objectives_sentinel
  - Both stage scripts now call the unified helpers

No public API change; backwards compatible (Fragment.themes defaults to [],
existing single-value fragments continue to work).

Refs: pre-planning audit 2026-09-28 (Oracle + Metis review).
```

## Non-Goals

- **Do NOT** add new frontmatter fields beyond what AC-2 specifies
- **Do NOT** change parser to use PyYAML globally (objective.py already uses
  PyYAML — fragment parser is intentionally naive for backward compat)
- **Do NOT** rename `主题` to `theme` (would break existing fragments)
- **Do NOT** fix the near-duplicate themes in phase-4.md (flag in commit, defer)
- **Do NOT** touch the OPENSPEC workflow or rdd-planner stage state machine

## Risks

- **Low**: Existing phase fragments with single `主题:` continue to work
  (Fragment.themes defaults to [single_value])
- **Low**: AGENTS.md sentinel rewrite is atomic and idempotent
- **Medium**: phase-4.md has near-duplicate themes ("多方对称与回归" vs
  "多方对称 + 回归 (P1-P3, 后续)") — flag in commit, don't auto-dedupe
- **Low**: Tests in `tests/unit/test_roadmap_state_fragments.py` already
  exercise `phase_refs: []` semantics; no breakage expected
