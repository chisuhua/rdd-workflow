# rdd-planner Stage 2.5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复并补全 rdd-planner Stage 2 的契约缺陷，先交付 P0 Wave 1 的单一 AUTO-SPRINT 写者、feedback resolve 闭环和强校验的 planner attach；P1/P2 作为明确依赖的后续 wave。

**Architecture:** Stage 2.5 不新增 workflow phase。P0-1 将 `roadmap_sprint.py` 作为 AUTO-SPRINT 的唯一渲染/写入内核，扩展其支持 project 形数据并迁移现有 change 表消费者。P0-2 保持反馈条目原地 resolution 更新，parser 用 frontmatter `last_feedback_id` 定位最新条目，schema 增加 `noted` enum。P0-3 通过显式人工 `planner attach` 修改单个 improvement 的 `roadmap_ref`，修订 ADR-0038 说明该例外，project_id 校验对齐 Phase Skeleton Theme / fragments 主题。

**Tech Stack:** Python 3.11+, PyYAML, jsonschema, pytest, bats-core, existing `_lib.core.atomic_write` and `FileLock`.

**Scope:** Wave 1 executes P0-1, P0-2, P0-3 as separately reviewable units. Wave 2 records P1 audit/diff/incremental-warning/ADR-index hardening. Wave 3 records P2 sprint lifecycle. Stage 3 `guide-arch → rdd-arch` rename and roadmap handover are explicitly out of scope.

---

## Confirmed decisions and non-negotiable invariants

1. **Delivery:** three P0 units in Wave 1; P1 and P2 are later waves, not silently implemented in Wave 1.
2. **AUTO-SPRINT ownership:** one writer, one renderer. Unique rendering contract: **project table** (per design spec §3.6). `roadmap_sprint` gains a project-shape renderer in addition to its existing change-shape renderer; planner data drives AUTO-SPRINT via this new path. `test_iteration_lifecycle.py` is migrated to the same renderer with data shape unchanged for its change-shape assertions.
3. **actions.py boundary:** `action_update_roadmap` (in `_lib/loop/actions.py`) writes `.rddf/state/roadmap-state.json` (no sentinels, no lock). It does **not** reach AUTO-SPRINT. Wave 1 does not delegate or modify it; no shared lock test is added because the premise is false.
4. **Feedback resolve:** update the selected entry's `resolution: open` to `resolved` in place; record `resolved_at` and `resolved_by` (per `feedback_entry_schema`). The parser must resolve the newest entry, not merely reorder regex checks. `noted` is added to `planner_state_schema.json` and `improvement_frontmatter_schema.json` `feedback_status` enums.
5. **Planner attach:** explicit command may update one improvement's `roadmap_ref`; ADR-0038 documents this write exception. Validate project_id against the Phase Skeleton Theme column (and phase fragments `主题` field as backup), and validate phase against `Phase Skeleton` Phase column or `.rddf/roadmap/phases/*.md` frontmatter `id`.
6. **Improvement safety:** no bulk rewrite. Attach changes only the selected file, preserves unrelated frontmatter keys, and fails before writing on malformed frontmatter or invalid mapping.
7. **Schema compatibility:** schema version remains `1`; the `noted` enum addition is additive (no version bump).
8. **Stage 3 boundary:** no guide rename, phase transition, or roadmap ownership transfer.

## File map

### Wave 1 P0-1 — single AUTO-SPRINT writer

- Modify: `_lib/roadmap_sprint.py` — add `render_project_table` and a `update_roadmap(roadmap_path, data, *, table="project"|"changes")` dispatch; both share `_split_around_sentinels` and locked atomic write. Lock path: `Path(roadmap_path).with_suffix(".lock")`.
- Modify: `_lib/planner_sync.py` — remove `_render_sprint_block` and `_merge_sprint_block`; in `apply_state`, call `update_roadmap(str(roadmap_path), state, table="project")` and drop local FileLock + atomic write.
- Modify: `tests/unit/test_roadmap_sprint.py` — add `test_render_project_table_shape`, `test_update_roadmap_dispatches_to_project_table`, `test_update_roadmap_acquires_roadmap_lock`.
- Modify: `tests/integration/test_iteration_lifecycle.py` — keep change-shape assertions; add project-shape test using planner-shaped `data` (no frontmatter mismatch — `data` is iteration.json shape, project shape comes from planner sync).
- Modify: `tests/unit/test_planner_sync.py` — remove tests for `_render_sprint_block` / `_merge_sprint_block`; replace with `test_apply_state_calls_roadmap_sprint_update_roadmap`.
- Modify: `docs/adr/ADR-0038-rdd-planner-crosscutting.md` — accurate writer matrix; no false "reused" claim; document single render contract.
- Modify: `docs/adr/README.md` — regenerate ADR index (ADR-0036/37/38 already absent).

### Wave 1 P0-2 — feedback resolve and latest-entry parsing

- Modify: `_lib/feedback_appender.py` — add `resolve_feedback(*, target_path, feedback_id, resolved_by="human")` using the existing per-file lock and atomic write.
- Modify: `_lib/cli/feedback_cmd.py` — replace silent placeholder; success prints proposal + feedback_id; unknown id returns `1`.
- Modify: `_lib/planner_sync.py` — `parse_feedback_status` isolates `## Feedback` up to next `##`; uses `last_feedback_id` to pick entry (fallback to last block only if pointer absent; fail-closed if pointer points to missing entry); precedence: resolution first, then kind; map to `{none, needs-revision, rejected, resolved, noted}`.
- Modify: `_lib/schemas/planner_state_schema.json` — `active_projects[].feedback_status` enum adds `"noted"`.
- Modify: `_lib/schemas/improvement_frontmatter_schema.json` — `feedback_status` enum adds `"noted"`.
- Modify: `tests/unit/test_feedback_appender.py`, `tests/unit/test_feedback_cli.py`, `tests/unit/test_planner_sync.py` — lock, resolution, malformed input, mixed-history fixtures; new test: mapped+noted feedback → sync --apply succeeds.
- Modify: `tests/integration/test_feedback_cmd.bats` — add resolve success/not-found cases.
- Modify: `docs/adr/ADR-0037-feedback-contract.md` — document in-place resolution exception, last_feedback_id authority, status precedence.

### Wave 1 P0-3 — explicit planner attach

- Create: `_lib/planner_attach.py` — focused module with `attach_proposal(*, project_root, proposal, project_id, phase, theme=None)`; reads Phase Skeleton Theme column + `.rddf/roadmap/phases/*.md` `id`/`主题`; preserves unrelated frontmatter; per-file lock + atomic write; idempotent identical mapping; rejects path traversal, unknown project_id/phase, malformed frontmatter before write.
- Modify: `_lib/cli/planner_cmd.py` — register `attach <proposal> --project-id X --phase Y [--theme Z]`; return `0` success / `1` validation / `2` I/O.
- Modify: `tests/unit/test_planner_attach.py` — validation, idempotency, malformed frontmatter, no other-file modifications, project_id from Theme column, phase from skeleton.
- Modify: `tests/integration/test_planner_cmd.bats` — add attach success/failure cases.
- Modify: `docs/adr/ADR-0038-rdd-planner-crosscutting.md` — manual attach exception clause.

### Wave 2 P1 — planner hardening (planned, not Wave 1 execution)

- Modify: `_lib/cli/planner_cmd.py` — `audit` and `diff` subcommands.
- Modify: `_lib/planner_state.py`, `_lib/schemas/planner_state_schema.json`, `_lib/planner_sync.py` — additive `previous_unmapped` baseline and incremental warning semantics (keep version 1).
- Modify: `docs/adr/README.md` — synchronized ADR index gate.

### Wave 3 P2 — sprint lifecycle (planned, not Wave 1 execution)

- Modify: planner state/history modules and CLI — `advance-sprint` and `history` only after persistence semantics are approved.
- Add tests and ADR/design updates for retention, reset, and history storage.

## Dependency graph

```text
P0-1 single writer ───────────────┬──> P1 sentinel hardening / ADR index
                                  └──> Stage 3 roadmap handover
P0-2 feedback resolve/latest parse ───> P1 incremental warning
P0-3 planner attach ───────────────┬──> P1 audit
                                  └──> P1 diff (optional shared view)
P0-1 + P0-2 + P0-3 ────────────────> Wave 2
Wave 2 stable state contract ──────> Wave 3 history/advance
```

# Wave 1 execution tasks

## Task 1: P0-1 — single AUTO-SPRINT writer with project table

**Files:**
- Modify: `_lib/roadmap_sprint.py`
- Modify: `_lib/planner_sync.py`
- Test: `tests/unit/test_roadmap_sprint.py`
- Test: `tests/unit/test_planner_sync.py`
- Test: `tests/integration/test_iteration_lifecycle.py`
- Modify: `docs/adr/ADR-0038-rdd-planner-crosscutting.md`
- Modify: `docs/adr/README.md`

- [ ] **Step 1: Add failing tests for project table renderer and roadmap lock**

Add to `tests/unit/test_roadmap_sprint.py`:

```python
def test_render_project_table_renders_project_rows():
    """render_project_table renders the planner project table shape."""
    data = {
        "current_sprint": "sprint-2026-09",
        "active_projects": [
            {"project_id": "p1", "phase": "phase-2", "priority": "P1",
             "feedback_status": "none", "proposal": "foo"},
            {"project_id": "p2", "phase": "phase-3", "priority": "P2",
             "feedback_status": "needs-revision", "proposal": "bar"},
        ],
    }
    out = rs.render_project_table(data)
    assert "## Current Sprint: sprint-2026-09" in out
    assert "| Project | Phase | Priority | Feedback | Proposal |" in out
    assert "| p1 | phase-2 | P1 | none | foo |" in out
    assert "| p2 | phase-3 | P2 | needs-revision | bar |" in out


def test_update_roadmap_dispatches_project_table(monkeypatch):
    """update_roadmap(..., table='project') renders via render_project_table."""
    captured = {}
    monkeypatch.setattr(rs, "render_project_table",
                        lambda d: (captured.setdefault("data", d), "PROJECT-INNER")[1])
    rs.update_roadmap("dummy", {"current_sprint": "sprint-2026-09", "active_projects": []},
                      table="project")
    assert "data" in captured


def test_update_roadmap_acquires_roadmap_lock(tmp_path, monkeypatch):
    """update_roadmap acquires a FileLock at <roadmap_path>.lock."""
    import _lib.core.lock as core_lock
    rm_path = tmp_path / "roadmap.md"
    rm_path.write_text("# R\n")
    seen_locks = []
    orig_lock = core_lock.FileLock
    def spy(lock_path, *a, **kw):
        seen_locks.append(lock_path)
        return orig_lock(lock_path, *a, **kw)
    monkeypatch.setattr("skills._lib.core.lock.FileLock", spy)
    rs.update_roadmap(str(rm_path), {"current_sprint": "sprint-x", "active_projects": []},
                      table="project")
    assert any(str(rm_path.with_suffix(".lock")) == p for p in seen_locks)
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
python3 -m pytest tests/unit/test_roadmap_sprint.py -q -k "project_table or roadmap_lock or dispatches"
```

Expected: FAIL (`render_project_table` and the `table=` kwarg do not exist).

- [ ] **Step 3: Implement project renderer and locked update in `roadmap_sprint`**

Modify `_lib/roadmap_sprint.py`:

1. Add `render_project_table(data)`:
   - Header: `## Current Sprint: <current_sprint>`.
   - If `active_projects`: render `| Project | Phase | Priority | Feedback | Proposal |` table from rows `{project_id, phase, priority, feedback_status, proposal}`.
   - Else: render `_No active projects in current sprint._`.
   - If `unmapped_proposals` present: render `### Unmapped (N)` with up to 10 entries + overflow line.

2. Add `table: str = "changes"` kwarg to `update_roadmap`. Dispatch:
   ```python
   if table == "project":
       inner = render_project_table(data)
   else:
       inner = render_sprint_table(data)
   ```

3. Wrap the file read/write block with `FileLock(str(Path(roadmap_path).with_suffix(".lock")), timeout=10.0)`. Existing `_split_around_sentinels` and atomic `.tmp + os.replace` remain.

- [ ] **Step 4: Run focused tests, including legacy change-shape tests**

```bash
python3 -m pytest tests/unit/test_roadmap_sprint.py tests/integration/test_iteration_lifecycle.py -q
```

Expected: all pass (existing change-shape tests still consume `update_roadmap(..., table="changes")` — the default).

- [ ] **Step 5: Migrate `planner_sync.apply_state` to delegate**

Modify `_lib/planner_sync.py`:

1. Delete `_render_sprint_block` and `_merge_sprint_block`.
2. In `apply_state`, replace the roadmap block with:
   ```python
   from _lib.roadmap_sprint import update_roadmap
   update_roadmap(str(roadmap_path), state, table="project")
   ```
3. Remove the local `FileLock`/`atomic_write_text` import and use. Keep `write_state(...)` unchanged (planner state file is separate from roadmap).

- [ ] **Step 6: Update planner_sync tests; add delegation test**

Update `tests/unit/test_planner_sync.py`:

- Remove tests that exercise the deleted private functions.
- Add:
  ```python
  def test_apply_state_delegates_to_roadmap_sprint(monkeypatch, tmp_path):
      """apply_state calls roadmap_sprint.update_roadmap with table='project'."""
      captured = {}
      def fake_update(roadmap_path, data, *, table="changes"):
          captured["path"] = roadmap_path
          captured["data"] = data
          captured["table"] = table
      monkeypatch.setattr("_lib.planner_sync.update_roadmap", fake_update)
      (tmp_path / ".rddf" / "roadmap.md").write_text("# R\n## Phase Skeleton\n| a | b |\n<!-- AUTO-INDEX -->\n")
      state = {"version": 1, "current_sprint": "sprint-2026-09",
               "active_projects": [], "unmapped_proposals": []}
      from _lib.planner_sync import apply_state
      apply_state(tmp_path, state)
      assert captured["table"] == "project"
      assert captured["data"]["current_sprint"] == "sprint-2026-09"
  ```

- [ ] **Step 7: Run planner_sync tests**

```bash
python3 -m pytest tests/unit/test_planner_sync.py -q
```

Expected: all pass.

- [ ] **Step 8: Update ADR-0038 and regenerate ADR index**

In `docs/adr/ADR-0038-rdd-planner-crosscutting.md`:

- Replace any "reused `_lib/roadmap_sprint.py`" wording with: "AUTO-SPRINT rendering and atomic update are owned by `_lib/roadmap_sprint.py`; planner sync delegates via the `table='project'` dispatch."
- Add section "Roadmap writer matrix": `_lib/roadmap_sprint.update_roadmap` is the **only** writer of the AUTO-SPRINT block. `_lib/loop/actions.py::action_update_roadmap` writes `.rddf/state/roadmap-state.json` (no sentinel, no roadmap write).

Regenerate ADR index: `docs/adr/README.md` has `<!-- ADR_INDEX_START --> ... <!-- ADR_INDEX_END -->` markers. `python3 -c "from _lib.adr_index_generator import render_table, scan_adrs; from pathlib import Path; print(render_table(scan_adrs(Path('docs/adr'))))"` then manually paste between the markers. Verify ADR-0036, ADR-0037, ADR-0038 are present.

- [ ] **Step 9: Commit P0-1**

```bash
git add _lib/roadmap_sprint.py _lib/planner_sync.py tests/unit/test_roadmap_sprint.py tests/unit/test_planner_sync.py tests/integration/test_iteration_lifecycle.py docs/adr/ADR-0038-rdd-planner-crosscutting.md docs/adr/README.md
git commit -m "fix(planner): single AUTO-SPRINT writer with project table dispatch"
```

## Task 2: P0-2 — feedback resolve and latest-entry parsing

**Files:**
- Modify: `_lib/feedback_appender.py`
- Modify: `_lib/cli/feedback_cmd.py`
- Modify: `_lib/planner_sync.py`
- Modify: `_lib/schemas/planner_state_schema.json`
- Modify: `_lib/schemas/improvement_frontmatter_schema.json`
- Test: `tests/unit/test_feedback_appender.py`
- Test: `tests/unit/test_feedback_cli.py`
- Test: `tests/unit/test_planner_sync.py`
- Test: `tests/integration/test_feedback_cmd.bats`
- Modify: `docs/adr/ADR-0037-feedback-contract.md`

- [ ] **Step 1: Add failing tests for resolution and latest-entry parsing**

In `tests/unit/test_feedback_appender.py`:

```python
def test_resolve_feedback_updates_only_selected_entry(tmp_path):
    """Two entries; only selected entry's resolution changes."""
    target = tmp_path / "imp.md"
    target.write_text(
        "---\nname: x\nlast_feedback_id: feedback-20260101-001\n"
        "---\n\n\n## Feedback\n\n"
        "### feedback-20260101-001\n- **kind**: needs-revision\n- **resolution**: open\n\n"
        "### feedback-20260202-001\n- **kind**: rejected\n- **resolution**: open\n"
    )
    from _lib.feedback_appender import resolve_feedback
    resolve_feedback(target_path=str(target), feedback_id="feedback-20260202-001")
    text = target.read_text()
    # selected entry resolved
    assert "- **resolution**: resolved" in text.split("### feedback-20260202-001")[1].split("###")[0]
    # unselected entry untouched
    first_block = text.split("### feedback-20260101-001")[1].split("### feedback-20260202-001")[0]
    assert "- **resolution**: open" in first_block


def test_resolve_feedback_rejects_unknown_id(tmp_path):
    target = tmp_path / "imp.md"
    target.write_text("---\nname: x\n---\n\n## Feedback\n\n### feedback-x\n- **resolution**: open\n")
    from _lib.feedback_appender import FeedbackError, resolve_feedback
    with pytest.raises(FeedbackError, match="not found"):
        resolve_feedback(target_path=str(target), feedback_id="feedback-y")


def test_resolve_feedback_records_resolved_at_and_by(tmp_path):
    target = tmp_path / "imp.md"
    target.write_text(
        "---\nname: x\nlast_feedback_id: feedback-x\n---\n\n## Feedback\n\n"
        "### feedback-x\n- **kind**: needs-revision\n- **resolution**: open\n"
    )
    from _lib.feedback_appender import resolve_feedback
    resolve_feedback(target_path=str(target), feedback_id="feedback-x", resolved_by="human")
    text = target.read_text()
    assert "- **resolution**: resolved" in text
    assert "- **resolved_by**: human" in text
    assert "- **resolved_at**:" in text
```

In `tests/unit/test_planner_sync.py`:

```python
def test_parse_feedback_status_uses_last_feedback_id(tmp_path):
    """Historical needs-revision followed by resolved current entry -> resolved."""
    f = _make_improvement(tmp_path, "x",
        feedback_block=(
            "### feedback-20260101-001\n- **kind**: needs-revision\n- **resolution**: open\n\n"
            "### feedback-20260202-001\n- **kind**: needs-revision\n- **resolution**: resolved\n"
        ),
        last_feedback_id="feedback-20260202-001",
    )
    from _lib.planner_sync import parse_feedback_status
    assert parse_feedback_status(f) == "resolved"


def test_parse_feedback_status_returns_noted_for_blocked(tmp_path):
    f = _make_improvement(tmp_path, "x",
        feedback_block="### feedback-x\n- **kind**: blocked\n- **resolution**: open\n",
        last_feedback_id="feedback-x",
    )
    from _lib.planner_sync import parse_feedback_status
    assert parse_feedback_status(f) == "noted"


def test_parse_feedback_status_stops_at_next_top_level_section(tmp_path):
    f = _make_improvement(tmp_path, "x",
        feedback_block=(
            "### feedback-x\n- **kind**: needs-revision\n- **resolution**: open\n\n"
            "## Unrelated\n\n- **kind**: rejected\n"
        ),
        last_feedback_id="feedback-x",
    )
    from _lib.planner_sync import parse_feedback_status
    assert parse_feedback_status(f) == "needs-revision"


def test_parse_feedback_status_fails_closed_on_missing_pointer_entry(tmp_path):
    f = _make_improvement(tmp_path, "x",
        feedback_block="### feedback-20260101-001\n- **kind**: needs-revision\n- **resolution**: open\n",
        last_feedback_id="feedback-does-not-exist",
    )
    from _lib.planner_sync import parse_feedback_status
    assert parse_feedback_status(f) == "none"
```

`_make_improvement` must be extended to accept `last_feedback_id` and emit it in frontmatter.

Add to `tests/integration/test_feedback_cmd.bats`:

```bash
@test "feedback resolve: success updates file" {
    # ... create imp.md with feedback entry, run resolve, assert resolution=resolved
}

@test "feedback resolve: unknown id returns non-zero" {
    # ... create imp.md, run resolve with bogus id, expect status != 0
}
```

- [ ] **Step 2: Run new tests to verify failure**

```bash
python3 -m pytest tests/unit/test_feedback_appender.py tests/unit/test_planner_sync.py -q -k "resolve_feedback or last_feedback_id or noted or next_top_level or missing_pointer"
bats tests/integration/test_feedback_cmd.bats
```

Expected: failures.

- [ ] **Step 3: Implement `resolve_feedback` in `feedback_appender`**

In `_lib/feedback_appender.py`:

```python
def resolve_feedback(
    *, target_path: str, feedback_id: str, resolved_by: str = "human"
) -> None:
    """Mark one existing feedback entry as resolved, atomically.

    Reads the file under the same per-file lock used by append_feedback,
    isolates the `### <feedback_id>` block, and replaces only that block's
    `- **resolution**: open` line with `resolved`, adding `resolved_at`
    and `resolved_by` lines. Writes atomically. Raises FeedbackError on
    unknown id or malformed entry; does not write on failure.
    """
    target = Path(target_path)
    if not target.exists():
        raise FeedbackError(f"Improvement file not found: {target}")
    lock_path = target.with_suffix(target.suffix + ".lock")
    with FileLock(str(lock_path), timeout=10.0):
        text = target.read_text(encoding="utf-8")
        if "## Feedback" not in text:
            raise FeedbackError("No ## Feedback section in target")
        marker = f"### {feedback_id}"
        idx = text.find(marker)
        if idx == -1:
            raise FeedbackError(f"Feedback entry not found: {feedback_id}")
        # Isolate block: from marker to next ### or ## boundary
        rest = text[idx + len(marker):]
        # Find end of block: next "### " or top-level "## "
        end = len(rest)
        for stop in ("\n### ", "\n## "):
            pos = rest.find(stop, 1)
            if pos != -1 and pos < end:
                end = pos
        block = rest[:end]
        if "- **resolution**:" not in block:
            raise FeedbackError(f"Entry {feedback_id} has no resolution field")
        # Replace resolution line, append resolved_at/resolved_by
        new_block_lines = []
        replaced = False
        for line in block.splitlines():
            if line.strip().startswith("- **resolution**:"):
                new_block_lines.append("- **resolution**: resolved")
                replaced = True
            else:
                new_block_lines.append(line)
        if not replaced:
            raise FeedbackError(f"Entry {feedback_id} resolution not updated")
        new_block_lines.append(f"- **resolved_at**: {_dt.datetime.now(_dt.timezone.utc).isoformat(timespec='seconds')}")
        new_block_lines.append(f"- **resolved_by**: {resolved_by}")
        new_block = "\n".join(new_block_lines)
        new_text = text[:idx + len(marker)] + new_block + rest[end:]
        atomic_write_text(target, new_text)
```

- [ ] **Step 4: Replace the CLI placeholder**

In `_lib/cli/feedback_cmd.py`:

```python
if ns.subcommand == "resolve":
    target = _find_improvement(project_root, ns.proposal)
    try:
        from _lib.feedback_appender import resolve_feedback, FeedbackError
        resolve_feedback(target_path=str(target), feedback_id=ns.feedback_id)
    except FeedbackError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1
    sys.stdout.write(f"✓ Resolved: {ns.feedback_id}\n  File: {target}\n")
    return 0
```

Preserve the existing `LoopExceededError` handler at the outer scope.

- [ ] **Step 5: Implement parser with `last_feedback_id` authority**

Replace `parse_feedback_status` in `_lib/planner_sync.py`:

```python
def parse_feedback_status(proposal_path: Path) -> str:
    if not proposal_path.exists():
        return "none"
    text = proposal_path.read_text(encoding="utf-8")
    if "## Feedback" not in text:
        return "none"
    # Isolate ## Feedback up to next top-level ##
    start = text.index("## Feedback")
    section = text[start:]
    rest = section[len("## Feedback"):]
    end = len(rest)
    for stop in ("\n## ",):
        pos = rest.find(stop, 1)
        if pos != -1 and pos < end:
            end = pos
    section = section[: len("## Feedback") + end]
    # Extract last_feedback_id from frontmatter (best effort)
    fm_id = None
    if text.startswith("---"):
        try:
            end_fm = text.index("\n---", 3)
            fm_inner = text[3:end_fm]
            import yaml
            fm = yaml.safe_load(fm_inner) or {}
            fm_id = fm.get("last_feedback_id")
        except (ValueError, yaml.YAMLError):
            fm_id = None
    # Find blocks
    blocks = []
    i = 0
    while True:
        j = section.find("\n### ", i + 1)
        if j == -1:
            break
        blocks.append((j, section[j + 1 : section.find("\n### ", j + 1) if section.find("\n### ", j + 1) != -1 else len(section)]))
        i = j
        if i > 10_000:
            break
    if not blocks:
        return "none"
    selected = None
    if fm_id:
        for offset, blk in blocks:
            if blk.startswith(f"### {fm_id}"):
                selected = blk
                break
        if selected is None:
            return "none"
    else:
        selected = blocks[-1][1]
    # Inspect selected block: resolution first, then kind
    if re.search(r"\*\*resolution\*\*: resolved", selected):
        return "resolved"
    m = re.search(r"\*\*kind\*\*:\s*(\S+)", selected)
    if not m:
        return "none"
    kind = m.group(1)
    if kind == "rejected":
        return "rejected"
    if kind in ("needs-revision", "ac-fail"):
        return "needs-revision"
    if kind in ("blocked", "noted"):
        return "noted"
    return "none"
```

Refactor the block-iteration loop into a clean helper if needed.

- [ ] **Step 6: Add `"noted"` to schema enums**

In `_lib/schemas/planner_state_schema.json`, change:
```json
"feedback_status": {"type": "string", "enum": ["none", "needs-revision", "rejected", "resolved"]}
```
to:
```json
"feedback_status": {"type": "string", "enum": ["none", "needs-revision", "rejected", "resolved", "noted"]}
```
in both occurrences (active_projects items; any other usage).

In `_lib/schemas/improvement_frontmatter_schema.json`, do the same for the frontmatter `feedback_status`.

Verify with:
```bash
python3 -c "import json, jsonschema; s = json.load(open('_lib/schemas/planner_state_schema.json')); jsonschema.validate({'version': 1, 'current_sprint': 'sprint-2026-09', 'last_sync_at': '2026-09-03T10:30:00+08:00', 'active_projects': [{'project_id': 'p', 'phase': 'phase-2', 'priority': 'P1', 'status': 'active', 'feedback_status': 'noted'}], 'unmapped_proposals': [], 'synced_proposals': []}, s); print('OK')"
```

- [ ] **Step 7: Add regression test for mapped+noted sync**

In `tests/unit/test_planner_sync.py`:

```python
def test_apply_state_accepts_noted_feedback(tmp_path):
    """sync --apply must accept noted feedback_status (schema includes 'noted')."""
    _make_improvement(tmp_path, "mapped", roadmap_ref={"project_id": "p", "phase": "phase-2"},
                      feedback_block="### feedback-x\n- **kind**: blocked\n- **resolution**: open\n",
                      last_feedback_id="feedback-x")
    state = render_state(tmp_path)
    apply_state(tmp_path, state)  # must not raise
```

- [ ] **Step 8: Run focused tests and full feedback regression**

```bash
python3 -m pytest tests/unit/test_feedback_appender.py tests/unit/test_feedback_cli.py tests/unit/test_planner_sync.py -q
bats tests/integration/test_feedback_cmd.bats
```

Expected: all pass.

- [ ] **Step 9: Update ADR-0037 and commit P0-2**

In `docs/adr/ADR-0037-feedback-contract.md`, add:

> §Decision: **In-place resolution exception** — `rddf feedback resolve <proposal> <feedback_id>` mutates only the selected entry's `resolution: open` to `resolved`, adding `resolved_at` and `resolved_by`. The append-only contract applies to **creation** of new entries, not to resolution status updates. The parser derives `feedback_status` by reading frontmatter `last_feedback_id` and selecting that exact `### feedback-<id>` block; missing pointer → `none`. Precedence is resolution before kind. Status enum: `none | needs-revision | rejected | resolved | noted`. `noted` covers `blocked` and `noted` kinds.

```bash
git add _lib/feedback_appender.py _lib/cli/feedback_cmd.py _lib/planner_sync.py _lib/schemas/planner_state_schema.json _lib/schemas/improvement_frontmatter_schema.json tests/unit/test_feedback_appender.py tests/unit/test_feedback_cli.py tests/unit/test_planner_sync.py tests/integration/test_feedback_cmd.bats docs/adr/ADR-0037-feedback-contract.md
git commit -m "feat(feedback): implement resolution and latest-entry status parsing"
```

## Task 3: P0-3 — strongly validated planner attach

**Files:**
- Create: `_lib/planner_attach.py`
- Modify: `_lib/cli/planner_cmd.py`
- Create: `tests/unit/test_planner_attach.py`
- Modify: `tests/integration/test_planner_cmd.bats`
- Modify: `docs/adr/ADR-0038-rdd-planner-crosscutting.md`

- [ ] **Step 1: Add failing attach tests**

In `tests/unit/test_planner_attach.py`:

```python
"""Tests for planner_attach (validated proposal attach)."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from _lib.planner_attach import AttachError, attach_proposal, list_valid_projects, list_valid_phases


def _setup_roadmap(parent: Path, themes: list[str], phases: list[str]):
    rmp = parent / ".rddf" / "roadmap.md"
    rmp.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"| {p} | {t} | active | | |" for p, t in zip(phases, themes))
    rmp.write_text(f"# Roadmap\n\n## Phase Skeleton\n| Phase | Theme | Status | Started | Done |\n|-------|-------|--------|---------|------|\n{rows}\n\n<!-- AUTO-INDEX -->\n")


def _setup_improvement(parent: Path, name: str, *, fm_extra: str = ""):
    imp = parent / ".rddf" / "improvements" / f"{name}.md"
    imp.parent.mkdir(parents=True, exist_ok=True)
    imp.write_text(f"---\nname: {name}\npriority: P2\n{fm_extra}---\n\n# proposal\n")


def test_list_valid_projects_reads_skeleton_themes(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar", "baz qux"], phases=["phase-2", "phase-3"])
    assert list_valid_projects(tmp_path) == {"foo bar", "baz qux"}


def test_list_valid_phases_reads_skeleton_and_fragment_ids(tmp_path):
    _setup_roadmap(tmp_path, themes=["t"], phases=["phase-2"])
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-extra.md").write_text("---\nid: phase-extra\nkind: phase\n---\n")
    assert list_valid_phases(tmp_path) == {"phase-2", "phase-extra"}


def test_attach_writes_roadmap_ref_and_preserves_other_frontmatter(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1", fm_extra="custom_key: keep_me\n")
    attach_proposal(project_root=tmp_path, proposal="imp1", project_id="foo bar", phase="phase-2")
    text = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    assert "project_id: foo bar" in text
    assert "phase: phase-2" in text
    assert "custom_key: keep_me" in text
    assert "priority: P2" in text


def test_attach_is_idempotent_for_same_mapping(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1")
    attach_proposal(project_root=tmp_path, proposal="imp1", project_id="foo bar", phase="phase-2")
    first = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    attach_proposal(project_root=tmp_path, proposal="imp1", project_id="foo bar", phase="phase-2")
    second = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    assert first == second


def test_attach_rejects_unknown_project(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1")
    with pytest.raises(AttachError, match="project_id not in roadmap"):
        attach_proposal(project_root=tmp_path, proposal="imp1", project_id="nope", phase="phase-2")


def test_attach_rejects_unknown_phase(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1")
    with pytest.raises(AttachError, match="phase not in roadmap"):
        attach_proposal(project_root=tmp_path, proposal="imp1", project_id="foo bar", phase="phase-nope")


def test_attach_rejects_malformed_frontmatter_without_writing(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    imp = tmp_path / ".rddf" / "improvements" / "broken.md"
    imp.parent.mkdir(parents=True)
    imp.write_text("---\nname: x\n: bad: yaml: :\n---\n")
    original = imp.read_text()
    with pytest.raises(AttachError):
        attach_proposal(project_root=tmp_path, proposal="broken", project_id="foo bar", phase="phase-2")
    assert imp.read_text() == original


def test_attach_rejects_path_traversal(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    with pytest.raises(AttachError, match="invalid proposal"):
        attach_proposal(project_root=tmp_path, proposal="../escape", project_id="foo bar", phase="phase-2")


def test_attach_does_not_modify_other_files(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1")
    _setup_improvement(tmp_path, "imp2")
    other = (tmp_path / ".rddf" / "improvements" / "imp2.md").read_text()
    attach_proposal(project_root=tmp_path, proposal="imp1", project_id="foo bar", phase="phase-2")
    assert (tmp_path / ".rddf" / "improvements" / "imp2.md").read_text() == other
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python3 -m pytest tests/unit/test_planner_attach.py -q
```

Expected: FAIL (module not found / `attach_proposal` undefined).

- [ ] **Step 3: Implement `_lib/planner_attach.py`**

```python
"""Validated, single-file proposal attach.

Per ADR-0038 (Stage 2.5): this is the only writer (besides `rddf feedback
add`) that touches .rddf/improvements/*.md. Operates on exactly one file,
preserves unrelated frontmatter, validates project_id and phase against
the canonical roadmap sources, and is idempotent for identical mappings.

project_id: must match a Theme value from .rddf/roadmap.md ## Phase Skeleton.
phase: must match a Phase value from ## Phase Skeleton or a phase fragment
       id (.rddf/roadmap/phases/*.md frontmatter `id`).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import yaml

from _lib.core.atomic_write import atomic_write_text
from _lib.core.lock import FileLock

__all__ = ["AttachError", "attach_proposal", "list_valid_projects", "list_valid_phases"]


class AttachError(Exception):
    """Attach validation failure (no write performed)."""


_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _roadmap_path(project_root: Path) -> Path:
    return project_root / ".rddf" / "roadmap.md"


def _improvement_path(project_root: Path, proposal: str) -> Path:
    if not _SAFE_NAME.match(proposal):
        raise AttachError(f"invalid proposal name: {proposal!r}")
    target = project_root / ".rddf" / "improvements" / f"{proposal}.md"
    if not target.exists():
        raise AttachError(f"improvement file not found: {target}")
    if target.resolve().parent != (project_root / ".rddf" / "improvements").resolve():
        raise AttachError(f"path traversal rejected for {proposal!r}")
    return target


def _parse_skeleton(roadmap_text: str) -> tuple[set[str], set[str]]:
    """Return (themes, phases) parsed from ## Phase Skeleton table."""
    themes: set[str] = set()
    phases: set[str] = set()
    in_section = False
    for line in roadmap_text.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == "## Phase Skeleton"
            continue
        if not in_section or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0].startswith("---") or cells[0].lower() == "phase":
            continue
        phases.add(cells[0])
        themes.add(cells[1])
    return themes, phases


def _phase_fragment_ids(project_root: Path) -> set[str]:
    ids: set[str] = set()
    phases_dir = project_root / ".rddf" / "roadmap" / "phases"
    if not phases_dir.is_dir():
        return ids
    for f in phases_dir.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        try:
            end = text.index("\n---", 3)
            fm = yaml.safe_load(text[3:end]) or {}
        except (ValueError, yaml.YAMLError):
            continue
        pid = fm.get("id")
        if isinstance(pid, str) and pid:
            ids.add(pid)
    return ids


def list_valid_projects(project_root: Path) -> set[str]:
    """Return set of valid project_ids (= Phase Skeleton Theme values)."""
    rm = _roadmap_path(project_root)
    if not rm.exists():
        return set()
    themes, _ = _parse_skeleton(rm.read_text(encoding="utf-8"))
    return {t for t in themes if t and t != "Theme"}


def list_valid_phases(project_root: Path) -> set[str]:
    """Return set of valid phases (skeleton Phase column + fragment ids)."""
    rm = _roadmap_path(project_root)
    phases: set[str] = set()
    if rm.exists():
        _, skel_phases = _parse_skeleton(rm.read_text(encoding="utf-8"))
        phases |= {p for p in skel_phases if p and p.lower() != "phase"}
    phases |= _phase_fragment_ids(project_root)
    return phases


def _parse_frontmatter_block(text: str) -> tuple[dict, str, str]:
    if not text.startswith("---"):
        raise AttachError("missing frontmatter delimiters")
    try:
        end = text.index("\n---", 3)
    except ValueError:
        raise AttachError("malformed frontmatter: no closing ---")
    fm_inner = text[3:end].lstrip("\n")
    try:
        fm = yaml.safe_load(fm_inner) or {}
        if not isinstance(fm, dict):
            raise AttachError("frontmatter is not a mapping")
    except yaml.YAMLError as exc:
        raise AttachError(f"YAML parse error: {exc}")
    fm_block = text[: end + 4]
    body = text[end + 4:].lstrip("\n")
    return fm, fm_block, body


def _serialize_frontmatter(fm: dict) -> str:
    yaml_text = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{yaml_text}\n---\n"


def attach_proposal(
    *, project_root: Path, proposal: str, project_id: str, phase: str, theme: str | None = None
) -> Path:
    """Validate and update one improvement's roadmap_ref. Idempotent for identical mapping."""
    project_root = Path(project_root).resolve()
    target = _improvement_path(project_root, proposal)
    valid_projects = list_valid_projects(project_root)
    valid_phases = list_valid_phases(project_root)
    if project_id not in valid_projects:
        raise AttachError(
            f"project_id not in roadmap Phase Skeleton Theme column: {project_id!r}; "
            f"valid: {sorted(valid_projects)}"
        )
    if phase not in valid_phases:
        raise AttachError(
            f"phase not in roadmap: {phase!r}; valid: {sorted(valid_phases)}"
        )

    new_ref = {"project_id": project_id, "phase": phase}
    if theme is not None:
        new_ref["theme"] = theme

    lock_path = target.with_suffix(target.suffix + ".lock")
    with FileLock(str(lock_path), timeout=10.0):
        text = target.read_text(encoding="utf-8")
        fm, _, body = _parse_frontmatter_block(text)
        existing = fm.get("roadmap_ref")
        if isinstance(existing, dict) and existing == new_ref:
            return target  # idempotent no-op
        if isinstance(existing, dict):
            raise AttachError(
                f"existing roadmap_ref differs: {existing!r}; explicit --overwrite required (not yet implemented)"
            )
        fm["roadmap_ref"] = new_ref
        new_text = _serialize_frontmatter(fm) + "\n" + body
        atomic_write_text(target, new_text)
    return target
```

- [ ] **Step 4: Register CLI subcommand**

In `_lib/cli/planner_cmd.py`:

```python
p_attach = sub.add_parser("attach", help="Attach proposal to roadmap project/phase")
p_attach.add_argument("proposal")
p_attach.add_argument("--project-id", required=True)
p_attach.add_argument("--phase", required=True)
p_attach.add_argument("--theme", default=None)
```

And in `cmd_planner`:

```python
if ns.subcommand == "attach":
    from _lib.planner_attach import AttachError, attach_proposal
    try:
        attach_proposal(
            project_root=project_root, proposal=ns.proposal,
            project_id=ns.project_id, phase=ns.phase, theme=ns.theme,
        )
    except AttachError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1
    sys.stdout.write(f"✓ Attached: {ns.proposal} -> {ns.project_id}/{ns.phase}\n")
    return 0
```

- [ ] **Step 5: Add bats integration cases**

In `tests/integration/test_planner_cmd.bats`:

```bash
@test "planner: attach --project-id (Theme) and --phase (Phase Skeleton) succeeds" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-2 | foo bar | active | | |
EOF
    cat > .rddf/improvements/imp1.md <<'EOF'
---
name: imp1
priority: P2
---
# imp1
EOF
    run python3 -m _lib.cli planner attach imp1 --project-id "foo bar" --phase phase-2 --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    grep -q "project_id: foo bar" .rddf/improvements/imp1.md
}

@test "planner: attach rejects unknown project_id" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-2 | foo bar | active | | |
EOF
    echo -e "---\nname: imp1\n---\n# x" > .rddf/improvements/imp1.md
    run python3 -m _lib.cli planner attach imp1 --project-id "nope" --phase phase-2 --project-root "$TEST_TMP"
    [ "$status" -eq 1 ]
}
```

- [ ] **Step 6: Run unit + integration tests**

```bash
python3 -m pytest tests/unit/test_planner_attach.py tests/unit/test_planner_cli.py -q
bats tests/integration/test_planner_cmd.bats
```

Expected: all pass.

- [ ] **Step 7: Update ADR-0038 and commit P0-3**

In `docs/adr/ADR-0038-rdd-planner-crosscutting.md`, append:

> §Decision (Stage 2.5): `rddf planner attach <proposal> --project-id X --phase Y [--theme Z]` is the only command besides `rddf feedback add` that may modify `.rddf/improvements/*.md`. It operates on **exactly one** file under per-file lock + atomic write, validates `project_id` against Phase Skeleton Theme column (and `phase` against Phase column / fragment ids), is idempotent for identical mappings, and refuses to overwrite an existing divergent mapping without an explicit flag. No bulk rewrite is permitted.

```bash
git add _lib/planner_attach.py _lib/cli/planner_cmd.py tests/unit/test_planner_attach.py tests/integration/test_planner_cmd.bats docs/adr/ADR-0038-rdd-planner-crosscutting.md
git commit -m "feat(planner): validated single-proposal attach"
```

## Task 4: Wave 1 verification and handoff

**Files:** None unless verification finds a change-caused defect.

- [ ] **Step 1: Run changed-file diagnostics**

```bash
python3 -m compileall -q _lib
python3 -m pytest tests/unit/test_roadmap_sprint.py tests/unit/test_planner_state.py tests/unit/test_planner_sync.py tests/unit/test_planner_cli.py tests/unit/test_planner_attach.py tests/unit/test_feedback_appender.py tests/unit/test_feedback_cli.py tests/integration/test_iteration_lifecycle.py -q
bats tests/integration/test_planner_cmd.bats tests/integration/test_feedback_cmd.bats
```

Expected: exit code 0 and no new failures.

- [ ] **Step 2: Run repository regression gates**

```bash
./test.sh --python
./test.sh --bats --regression
```

Before archive, the repository rule requires:

```bash
./test.sh --full --regression
```

Expected: exit code 0, or only failures already listed in `tests/KNOWN_FAILURES.txt`.

- [ ] **Step 3: Verify invariants**

```bash
git status --short .rddf/improvements/
python3 -m pytest tests/unit/test_p1_1_identity_merge.py tests/unit/test_adr_index_generator.py -q
```

Expected: no unintended bulk improvement changes; identity-merge and ADR index tests pass.

- [ ] **Step 4: Review the three P0 commits**

Check each commit's diff for: no type suppression, no empty catches, no unrelated refactor, no accidental state-file tracking, no silent-success errors, no second AUTO-SPRINT writer, no bulk improvement rewrite.

- [ ] **Step 5: Mark Wave 1 complete and hand off Wave 2**

Wave 2 must not begin until the single-writer contract and feedback status semantics are stable. Record remaining P1 work as separate changes rather than extending this Wave 1 implementation.

# Wave 2 planned task content (not executed by Wave 1)

1. `planner audit`: read-only unmapped list, grouping, and attach suggestions; JSON and human output contracts.
2. `planner diff`: stored vs computed state, including missing/corrupt state handling.
3. Incremental warning: add optional `previous_unmapped` compatibly, compute newly unmapped only, test migration and first-run semantics.
4. Sentinel/ADR hardening: canonical malformed-marker regression matrix and regenerated ADR index gate.

# Wave 3 planned task content (not executed by Wave 1)

1. `planner advance-sprint`: explicit close/reset semantics, no implicit history loss.
2. `planner history`: append-only persistence, retention, corruption handling, and JSON/human output.

# Self-review

- P0-1, P0-2, and P0-3 are independently reviewable and have explicit dependencies.
- The plan forbids the known bad fixes: regex-order-only parser changes, a second planner sentinel, silent attach overwrite, destructive schema upgrade, bulk improvement rewrite, and a fake `action_update_roadmap` delegation.
- Every Wave 1 task has failing tests, focused verification, commit scope, and full regression gates.
- Stage 3 rename/handover is not implemented here; only the writer contract is documented for future consumption.
- P1 `previous_unmapped` is planned but not implemented in Wave 1, avoiding an unapproved schema migration during the critical writer/feedback fixes.