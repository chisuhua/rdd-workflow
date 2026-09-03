# rdd-planner Stage 2.5 Wave 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close Wave 1 review findings, harden the ADR index, and add `planner audit`, `planner diff`, and incremental warning on top of the single-writer / latest-entry / validated-attach contract.

**Architecture:** Five independently reviewable changes. Task 3.5 patches Wave 1 defects identified by Oracle (attach `--overwrite` + theme idempotency, `resolve_feedback` section-scoped search, parser observability, fragment `主题` fallback, import style). Task 3.4b adds a structural ADR index gate plus a single-writer grep assertion. Tasks 3.2 and 3.1 add `planner diff` and `planner audit` subcommands with TDD coverage. Task 3.3 introduces an additive `previous_unmapped` baseline for incremental warning. All changes preserve the single AUTO-SPRINT writer (`_lib.roadmap_sprint.update_roadmap`) and the 226-improvement no-touch invariant.

**Tech Stack:** Python 3.11+, PyYAML, jsonschema, argparse, logging, pytest, bats-core, existing `_lib.core.atomic_write` and `FileLock`.

**Builds on:** Wave 1 commits (`43c7683` P0-1, `585ec34` P0-2, `b04ebad` P0-3).
**Spec:** `docs/superpowers/specs/2026-09-03-rdd-planner-stage2-design.md` + Stage 2.5 plan §Wave 2.

---

## Confirmed decisions and non-negotiable invariants

1. **Delivery:** Five independent changes, one commit each. Execution order: 3.5 → 3.4b → 3.2 → 3.1 → 3.3.
2. **Single AUTO-SPRINT writer:** `_lib/roadmap_sprint.update_roadmap` remains the only writer. 3.4b adds a structural grep assertion enforcing this.
3. **attach idempotency:** `theme: null` ≡ theme omitted; `--overwrite` is the only path that mutates an existing divergent `roadmap_ref`.
4. **resolve_feedback scope:** marker search is bounded by the `## Feedback` section, mirroring `parse_feedback_status`.
5. **Parser observability:** `parse_feedback_status` fail-closed paths emit `logger.warning`; no silent misreports.
6. **ADR index gate:** unique numbering + README ↔ generator agreement + non-empty status/date.
7. **No bulk improvement rewrite**; no second AUTO-SPRINT writer; no plan migration of existing files.
8. **Schema compatibility:** `previous_unmapped` is additive; state version stays 1.

## File map (per change)

- **3.5** Wave 1 defect fixes:
  - Modify: `_lib/planner_attach.py` (add `--overwrite`, normalize `theme` in idempotency).
  - Modify: `_lib/cli/planner_cmd.py` (expose `--overwrite`).
  - Modify: `_lib/feedback_appender.py` (`resolve_feedback` section-scoped search).
  - Modify: `_lib/planner_sync.py` (parser logging, fragment `主题` fallback in `list_valid_projects`).
  - Modify: `_lib/roadmap_sprint.py` (import style L1).
  - Test: `tests/unit/test_planner_attach.py`, `tests/unit/test_feedback_appender.py`, `tests/unit/test_planner_sync.py`, `tests/integration/test_planner_cmd.bats`.
- **3.4b** ADR index gate + single-writer structural assertion:
  - Create: `tests/unit/test_adr_index_gate.py`.
- **3.2** `planner diff`:
  - Modify: `_lib/planner_sync.py` (`diff_state`).
  - Modify: `_lib/cli/planner_cmd.py` (`diff` subcommand).
  - Test: `tests/unit/test_planner_sync.py`, `tests/integration/test_planner_cmd.bats`.
- **3.1** `planner audit`:
  - Create: `_lib/planner_audit.py`.
  - Modify: `_lib/cli/planner_cmd.py` (`audit [--json]`).
  - Test: `tests/unit/test_planner_audit.py`, `tests/integration/test_planner_cmd.bats`.
- **3.3** Incremental warning:
  - Modify: `_lib/schemas/planner_state_schema.json` (add `previous_unmapped: [string]`, schema version stays 1).
  - Modify: `_lib/planner_sync.py` (`apply_state` computes incremental warning).
  - Test: `tests/unit/test_planner_sync.py`.

## Dependency graph

```text
3.5 (Wave 1 fixes) ────────────────┐
3.4b (ADR gate, no deps) ──────────┼─► 3.1 (audit, needs 3.5 for --overwrite)
                                  │
                                  ├─► 3.3 (previous_unmapped, after 3.1/3.2)
3.2 (diff, no deps) ──────────────┘
```

# Change 3.5 — Wave 1 defect fixes

## Task 3.5.1: attach `--overwrite` + theme idempotency normalization

**Files:**
- Modify: `_lib/planner_attach.py`
- Modify: `_lib/cli/planner_cmd.py`
- Test: `tests/unit/test_planner_attach.py`
- Modify: `tests/integration/test_planner_cmd.bats`

- [ ] **Step 1: Add failing tests**

Append to `tests/unit/test_planner_attach.py`:

```python
def test_attach_overwrite_replaces_divergent_mapping(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar", "bar baz"], phases=["phase-2", "phase-3"])
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-3.md").write_text(
        "---\nid: phase-3\nkind: phase\n---\n"
    )
    imp = tmp_path / ".rddf" / "improvements" / "imp1.md"
    imp.parent.mkdir(parents=True)
    imp.write_text(
        "---\nname: imp1\npriority: P2\nroadmap_ref:\n  project_id: foo bar\n  phase: phase-2\n---\n\n# proposal\n"
    )
    attach_proposal(
        project_root=tmp_path, proposal="imp1",
        project_id="bar baz", phase="phase-3", overwrite=True,
    )
    text = imp.read_text()
    assert "project_id: bar baz" in text
    assert "phase: phase-3" in text
    assert "project_id: foo bar" not in text


def test_attach_overwrite_false_rejects_divergent_mapping(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2", "phase-3"])
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-3.md").write_text(
        "---\nid: phase-3\nkind: phase\n---\n"
    )
    imp = tmp_path / ".rddf" / "improvements" / "imp1.md"
    imp.parent.mkdir(parents=True)
    imp.write_text(
        "---\nname: imp1\npriority: P2\nroadmap_ref:\n  project_id: foo bar\n  phase: phase-2\n---\n\n# proposal\n"
    )
    original = imp.read_text()
    with pytest.raises(AttachError, match="existing roadmap_ref differs"):
        attach_proposal(
            project_root=tmp_path, proposal="imp1",
            project_id="foo bar", phase="phase-3",
        )
    assert imp.read_text() == original


def test_attach_theme_idempotent_when_existing_omits_theme(tmp_path):
    """theme=None on second call matches existing {project_id, phase}."""
    _setup_roadmap(tmp_path, themes=["foo bar"], phases=["phase-2"])
    _setup_improvement(tmp_path, "imp1")
    attach_proposal(project_root=tmp_path, proposal="imp1",
                    project_id="foo bar", phase="phase-2", theme="t")
    first = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    attach_proposal(project_root=tmp_path, proposal="imp1",
                    project_id="foo bar", phase="phase-2", theme=None)
    second = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    # theme was kept; second call with theme=None is a no-op
    assert "theme: t" in first
    assert first == second


def test_attach_accepts_fragment_main_theme_as_project_id(tmp_path):
    """fragment 主题 field is a valid backup source for project_id (per plan §P0-3)."""
    _setup_roadmap(tmp_path, themes=["skeleton theme"], phases=["phase-2"])
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-2.md").write_text(
        "---\nid: phase-2\nkind: phase\n主题: fragment theme\n---\n"
    )
    _setup_improvement(tmp_path, "imp1")
    attach_proposal(project_root=tmp_path, proposal="imp1",
                    project_id="fragment theme", phase="phase-2")
    text = (tmp_path / ".rddf" / "improvements" / "imp1.md").read_text()
    assert "project_id: fragment theme" in text
```

- [ ] **Step 2: Run tests, verify failure**

```bash
python3 -m pytest tests/unit/test_planner_attach.py -q -k "overwrite or theme_idempotent or fragment_main_theme"
```

Expected: 4 failed.

- [ ] **Step 3: Update `_lib/planner_attach.py`**

In `list_valid_projects`, replace the body to merge Theme column with fragment `主题`:

```python
def list_valid_projects(project_root: Path) -> set[str]:
    """Return set of valid project_ids (= skeleton Theme + fragment 主题)."""
    rm = _roadmap_path(project_root)
    projects: set[str] = set()
    if rm.exists():
        themes, _ = _parse_skeleton(rm.read_text(encoding="utf-8"))
        projects |= {t for t in themes if t and t != "Theme"}
    projects |= _fragment_themes(project_root)
    return projects
```

Add helper after `_phase_fragment_ids`:

```python
def _fragment_themes(project_root: Path) -> set[str]:
    themes: set[str] = set()
    phases_dir = project_root / ".rddf" / "roadmap" / "phases"
    if not phases_dir.is_dir():
        return themes
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
        for raw in (fm.get("主题") or []):
            if isinstance(raw, str) and raw:
                themes.add(raw)
    return themes
```

Update `attach_proposal` signature and idempotency logic:

```python
def attach_proposal(
    *, project_root: Path, proposal: str, project_id: str, phase: str,
    theme: str | None = None, overwrite: bool = False,
) -> Path:
    """Validate and update one improvement's `roadmap_ref`.

    Idempotent for identical {project_id, phase} (theme mismatch is
    treated as a no-op when existing has theme and new call omits
    theme; explicit theme replacement requires `--overwrite`).
    Refuses to mutate an existing divergent mapping unless
    `overwrite=True`.
    """
    project_root = Path(project_root).resolve()
    target = _improvement_path(project_root, proposal)
    valid_projects = list_valid_projects(project_root)
    valid_phases = list_valid_phases(project_root)
    if project_id not in valid_projects:
        raise AttachError(
            f"project_id not in roadmap: {project_id!r}; valid: {sorted(valid_projects)}"
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
        fm, body = _parse_frontmatter_block(text)
        existing = fm.get("roadmap_ref")
        if isinstance(existing, dict):
            existing_normalized = {k: v for k, v in existing.items() if k != "theme"}
            new_normalized = {k: v for k, v in new_ref.items() if k != "theme"}
            if existing_normalized == new_normalized:
                return target  # idempotent (theme ignored)
            if not overwrite:
                raise AttachError(
                    f"existing roadmap_ref differs: {existing!r}; pass --overwrite to replace"
                )
        fm["roadmap_ref"] = new_ref
        new_text = _serialize_frontmatter(fm) + "\n" + body
        atomic_write_text(target, new_text)
    return target
```

- [ ] **Step 4: Update `_lib/cli/planner_cmd.py`**

Add `--overwrite` flag to the `attach` subparser and pass through:

```python
    p_attach.add_argument("--overwrite", action="store_true",
                          help="Replace an existing divergent roadmap_ref")
```

```python
                attach_proposal(
                    project_root=project_root,
                    proposal=ns.proposal,
                    project_id=ns.project_id,
                    phase=ns.phase,
                    theme=ns.theme,
                    overwrite=ns.overwrite,
                )
```

- [ ] **Step 5: Add bats case**

In `tests/integration/test_planner_cmd.bats`:

```bash
@test "planner: attach --overwrite replaces divergent mapping" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-2 | foo bar | active | | |
| phase-3 | bar baz | active | | |
EOF
    mkdir -p .rddf/roadmap/phases
    printf -- '---\nid: phase-3\nkind: phase\n---\n' > .rddf/roadmap/phases/phase-3.md
    printf -- '---\nname: imp1\npriority: P2\nroadmap_ref:\n  project_id: foo bar\n  phase: phase-2\n---\n# imp1\n' > .rddf/improvements/imp1.md
    run python3 -m _lib.cli planner attach imp1 --project-id "bar baz" --phase phase-3 --overwrite --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    grep -q "project_id: bar baz" .rddf/improvements/imp1.md
    grep -q "phase: phase-3" .rddf/improvements/imp1.md
    ! grep -q "project_id: foo bar" .rddf/improvements/imp1.md
}
```

- [ ] **Step 6: Run tests**

```bash
python3 -m pytest tests/unit/test_planner_attach.py tests/unit/test_planner_cli.py -q
bats tests/integration/test_planner_cmd.bats
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add _lib/planner_attach.py _lib/cli/planner_cmd.py tests/unit/test_planner_attach.py tests/integration/test_planner_cmd.bats
git commit -m "fix(planner-attach): add --overwrite and theme idempotency"
```

## Task 3.5.2: `resolve_feedback` section-scoped search

**Files:**
- Modify: `_lib/feedback_appender.py`
- Test: `tests/unit/test_feedback_appender.py`

- [ ] **Step 1: Add failing tests**

```python
def test_resolve_feedback_does_not_match_history_section(tmp_path):
    """A `### feedback-x` heading outside ## Feedback must NOT be resolved."""
    from _lib.feedback_appender import resolve_feedback
    target = tmp_path / "imp.md"
    target.write_text(
        "---\nname: x\n---\n"
        "# title\n\n"
        "## History\n\n### feedback-real\nnot the one to resolve\n\n"
        "## Feedback\n\n### feedback-real\n- **resolution**: open\n"
    )
    resolve_feedback(target_path=str(target), feedback_id="feedback-real")
    text = target.read_text()
    # History heading untouched
    assert "### feedback-real\nnot the one" in text
    # Feedback section entry resolved
    feedback_split = text.split("## Feedback")[1]
    assert "- **resolution**: resolved" in feedback_split


def test_resolve_feedback_rejects_when_id_only_in_other_section(tmp_path):
    from _lib.feedback_appender import FeedbackError, resolve_feedback
    target = tmp_path / "imp.md"
    target.write_text(
        "---\nname: x\n---\n\n## History\n\n### feedback-orphan\n\n## Feedback\n\n"
        "### feedback-other\n- **resolution**: open\n"
    )
    with pytest.raises(FeedbackError, match="not found"):
        resolve_feedback(target_path=str(target), feedback_id="feedback-orphan")
```

- [ ] **Step 2: Run tests, verify failure**

```bash
python3 -m pytest tests/unit/test_feedback_appender.py -q -k "history_section or only_in_other_section"
```

Expected: failures.

- [ ] **Step 3: Update `resolve_feedback`**

Replace the marker search in `_lib/feedback_appender.py`:

```python
def resolve_feedback(
    *, target_path: str, feedback_id: str, resolved_by: str = "human"
) -> None:
    target = Path(target_path)
    if not target.exists():
        raise FeedbackError(f"Improvement file not found: {target}")
    lock_path = target.with_suffix(target.suffix + ".lock")
    with FileLock(str(lock_path), timeout=10.0):
        text = target.read_text(encoding="utf-8")
        if "## Feedback" not in text:
            raise FeedbackError("No ## Feedback section in target")
        start = text.index("## Feedback")
        section = text[start:]
        rest = section[len("## Feedback"):]
        end = len(rest)
        for stop in ("\n## ",):
            pos = rest.find(stop, 1)
            if pos != -1 and pos < end:
                end = pos
        section = section[: len("## Feedback") + end]
        marker = f"### {feedback_id}"
        idx_in_section = section.find(marker)
        if idx_in_section == -1:
            raise FeedbackError(f"Feedback entry not found in ## Feedback: {feedback_id}")
        rest = section[idx_in_section + len(marker):]
        end = len(rest)
        for stop in ("\n### ", "\n## "):
            pos = rest.find(stop, 1)
            if pos != -1 and pos < end:
                end = pos
        block = rest[:end]
        if "- **resolution**:" not in block:
            raise FeedbackError(f"Entry {feedback_id} has no resolution field")
        new_lines = []
        replaced = False
        for line in block.splitlines():
            if line.lstrip().startswith("- **resolution**:"):
                new_lines.append("- **resolution**: resolved")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            raise FeedbackError(f"Entry {feedback_id} resolution not updated")
        now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        new_lines.append(f"- **resolved_at**: {now_iso}")
        new_lines.append(f"- **resolved_by**: {resolved_by}")
        new_block = "\n".join(new_lines)
        new_section = section[: idx_in_section + len(marker)] + new_block + rest[end:]
        new_text = text[:start] + new_section
        atomic_write_text(target, new_text)
```

- [ ] **Step 4: Run focused tests**

```bash
python3 -m pytest tests/unit/test_feedback_appender.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add _lib/feedback_appender.py tests/unit/test_feedback_appender.py
git commit -m "fix(feedback): scope resolve_feedback marker search to ## Feedback section"
```

## Task 3.5.3: parser observability + import style fix

**Files:**
- Modify: `_lib/planner_sync.py` (parser logging)
- Modify: `_lib/roadmap_sprint.py` (import style)
- Test: `tests/unit/test_planner_sync.py`

- [ ] **Step 1: Add failing test**

```python
def test_parse_feedback_status_logs_when_pointer_missing(tmp_path, caplog):
    """When last_feedback_id points to a missing block, parser logs a warning."""
    import logging
    f = _make_improvement(tmp_path, "x",
        feedback_block="### feedback-20260101-001\n- **kind**: needs-revision\n- **resolution**: open\n",
        last_feedback_id="feedback-does-not-exist",
    )
    with caplog.at_level(logging.WARNING, logger="_lib.planner_sync"):
        from _lib.planner_sync import parse_feedback_status
        result = parse_feedback_status(f)
    assert result == "none"
    assert any("feedback-does-not-exist" in r.message for r in caplog.records)
```

- [ ] **Step 2: Run test, verify failure**

```bash
python3 -m pytest tests/unit/test_planner_sync.py::test_parse_feedback_status_logs_when_pointer_missing -q
```

Expected: FAIL.

- [ ] **Step 3: Add logging to `parse_feedback_status`**

In `_lib/planner_sync.py`, near the top:

```python
import logging
logger = logging.getLogger(__name__)
```

In `parse_feedback_status`, after the `if fm_id:` block, when `selected is None`:

```python
        if fm_id:
            selected = next((b for b in blocks if b.startswith(f"### {fm_id}")), None)
            if selected is None:
                logger.warning(
                    "last_feedback_id %r points to missing entry; returning 'none'",
                    fm_id,
                )
                return "none"
```

Also add a log line when no `## Feedback` block is found (file without the section) — keep current `none` return but make the empty-sections path explicit:

```python
    if not blocks:
        logger.warning("no feedback entries found despite ## Feedback section")
        return "none"
```

- [ ] **Step 4: Fix import style in `_lib/roadmap_sprint.py`**

Replace `from skills._lib.core.lock import FileLock` with `from _lib.core.lock import FileLock` (per AGENTS.md #25).

- [ ] **Step 5: Run focused tests**

```bash
python3 -m pytest tests/unit/test_planner_sync.py tests/unit/test_roadmap_sprint.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add _lib/planner_sync.py _lib/roadmap_sprint.py tests/unit/test_planner_sync.py
git commit -m "fix(planner-sync): log parser fail-closed paths; correct import style"
```

---

# Change 3.4b — ADR index gate + single-writer structural assertion

## Task 3.4b.1: Create `tests/unit/test_adr_index_gate.py`

**Files:**
- Create: `tests/unit/test_adr_index_gate.py`

- [ ] **Step 1: Write the test file**

```python
"""Structural gates for docs/adr/.

Lock the ADR index contract:
- Unique ADR numbering (no collisions in docs/adr/).
- README ADR_INDEX_START..END segment matches the generator output.
- Every ADR row has non-empty status and date (excluding templates).
- Single-writer enforcement for AUTO-SPRINT block: the literal
  `AUTO-SPRINT-START` must not appear outside `_lib/roadmap_sprint.py`
  (except for tests).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ADR_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "adr"
README_PATH = ADR_DIR / "README.md"


def _collect_adr_files() -> list[Path]:
    return [p for p in ADR_DIR.glob("ADR-*.md") if "template" not in p.name.lower()]


def test_adr_numbering_is_unique():
    nums = [re.match(r"ADR-(\d{4})-", p.name).group(1) for p in _collect_adr_files() if re.match(r"ADR-(\d{4})-", p.name)]
    assert len(nums) == len(set(nums)), f"duplicate ADR numbers: {sorted(n for n in nums if nums.count(n) > 1)}"


def test_readme_index_matches_generator_output():
    from _lib.adr_index_generator import render_table, scan_adrs
    from _lib.adr_index_generator import render_table as _rt  # noqa
    adrs = scan_adrs(ADR_DIR)
    seen = {}
    for a in adrs:
        seen.setdefault(a["number"], a)
    deduped = sorted(seen.values(), key=lambda a: a["number"])
    expected = _rt(deduped).rstrip()
    readme = README_PATH.read_text(encoding="utf-8")
    m = re.search(r"<!-- ADR_INDEX_START -->\n(.*?)<!-- ADR_INDEX_END -->", readme, re.DOTALL)
    assert m, "ADR_INDEX_START/END markers missing in README"
    actual = m.group(1).rstrip()
    assert actual == expected, f"README index out of sync with generator\n---\nactual:\n{actual}\n---\nexpected:\n{expected}"


def test_readme_index_rows_have_status_and_date():
    readme = README_PATH.read_text(encoding="utf-8")
    m = re.search(r"<!-- ADR_INDEX_START -->\n(.*?)<!-- ADR_INDEX_END -->", readme, re.DOTALL)
    body = m.group(1)
    for line in body.splitlines()[2:]:  # skip header rows
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        status, date = cells[2], cells[3]
        assert status and status != "—", f"empty status in row: {line}"
        assert date and date != "—", f"empty date in row: {line}"


def test_auto_sprint_start_only_in_roadmap_sprint():
    """`AUTO-SPRINT-START` literal must only appear in roadmap_sprint.py (or its tests)."""
    repo_root = ADR_DIR.parent.parent
    offenders: list[str] = []
    for path in repo_root.rglob("*.py"):
        if any(part.startswith(".") for part in path.parts):
            continue
        if "_lib/roadmap_sprint" in str(path):
            continue
        if "tests/" in str(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "AUTO-SPRINT-START" in text:
            offenders.append(str(path))
    assert not offenders, f"AUTO-SPRINT-START leaked into: {offenders}"
```

- [ ] **Step 2: Run the new tests**

```bash
python3 -m pytest tests/unit/test_adr_index_gate.py -q
```

Expected: passing tests pin the current state; if any fail, document existing gaps and stop. If `test_readme_index_rows_have_status_and_date` fails because of the ADR-0036/37/38 empty rows, fix README first.

- [ ] **Step 3: Fix README ADR rows**

Edit `docs/adr/README.md` ADR_INDEX_START..END so each row has a non-empty status and date. Fill `"—"` with concrete values pulled from each ADR file (`> **状态**:` / `> **日期**:` block).

- [ ] **Step 4: Run again, expect all green**

```bash
python3 -m pytest tests/unit/test_adr_index_gate.py -q
```

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_adr_index_gate.py docs/adr/README.md
git commit -m "test(adr): lock index uniqueness + README sync + single-writer assertion"
```

---

# Change 3.2 — `planner diff` subcommand

## Task 3.2.1: Add `diff_state` + tests

**Files:**
- Modify: `_lib/planner_sync.py`
- Test: `tests/unit/test_planner_sync.py`

- [ ] **Step 1: Add failing tests**

```python
def test_diff_state_no_baseline_returns_empty_diff():
    from _lib.planner_sync import diff_state
    diff = diff_state(project_root=__import__("pathlib").Path("/nonexistent"))
    assert diff["has_baseline"] is False
    assert diff["unmapped_diff"] == {"added": [], "removed": []}
    assert diff["projects_diff"] == {}


def test_diff_state_identical_when_stored_equals_computed(tmp_path, monkeypatch):
    from _lib.planner_state import write_state
    state = render_state(tmp_path)
    write_state(tmp_path, state)
    from _lib.planner_sync import diff_state
    diff = diff_state(project_root=tmp_path)
    assert diff["has_baseline"] is True
    assert diff["unmapped_diff"] == {"added": [], "removed": []}
    assert diff["projects_diff"] == {}


def test_diff_state_detects_newly_unmapped(tmp_path, monkeypatch):
    from _lib.planner_state import write_state
    _make_improvement(tmp_path, "u1", roadmap_ref={"project_id": "p1", "phase": "phase-1"})
    state_before = render_state(tmp_path)
    write_state(tmp_path, state_before)
    _make_improvement(tmp_path, "u2")  # add an unmapped one
    from _lib.planner_sync import diff_state
    diff = diff_state(project_root=tmp_path)
    assert "u2" in diff["unmapped_diff"]["added"]
    assert diff["unmapped_diff"]["removed"] == []
```

- [ ] **Step 2: Run tests, verify failure**

```bash
python3 -m pytest tests/unit/test_planner_sync.py -q -k "diff_state"
```

Expected: 3 failed.

- [ ] **Step 3: Implement `diff_state`**

Append to `_lib/planner_sync.py`:

```python
def diff_state(project_root: Path) -> Dict[str, Any]:
    """Compare stored planner state to freshly computed state.

    Returns a dict:
      - has_baseline: bool (False if state file missing)
      - unmapped_diff: {"added": [...], "removed": [...]}
      - projects_diff: {project_id: {"phase": (stored, computed), "feedback_status": (stored, computed)}}
    Timestamps (last_sync_at, last_sync_status, sprint id) are NOT
    compared — they always differ and would create noise.
    """
    try:
        from _lib.planner_state import read_state
        stored = read_state(project_root)
    except Exception:
        return {
            "has_baseline": False,
            "unmapped_diff": {"added": [], "removed": []},
            "projects_diff": {},
        }
    computed = render_state(project_root)
    stored_unmapped = set(stored.get("unmapped_proposals") or [])
    computed_unmapped = set(computed.get("unmapped_proposals") or [])
    stored_active = {p["project_id"]: p for p in (stored.get("active_projects") or [])}
    computed_active = {p["project_id"]: p for p in (computed.get("active_projects") or [])}
    projects_diff: Dict[str, Dict[str, tuple]] = {}
    for pid in sorted(set(stored_active) | set(computed_active)):
        s = stored_active.get(pid, {})
        c = computed_active.get(pid, {})
        d = {}
        for key in ("phase", "feedback_status"):
            if s.get(key) != c.get(key):
                d[key] = (s.get(key), c.get(key))
        if d:
            projects_diff[pid] = d
    return {
        "has_baseline": True,
        "unmapped_diff": {
            "added": sorted(computed_unmapped - stored_unmapped),
            "removed": sorted(stored_unmapped - computed_unmapped),
        },
        "projects_diff": projects_diff,
    }
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/unit/test_planner_sync.py -q -k "diff_state"
```

Expected: 3 passed.

- [ ] **Step 5: Commit (library only)**

```bash
git add _lib/planner_sync.py tests/unit/test_planner_sync.py
git commit -m "feat(planner-sync): add diff_state stored vs computed comparison"
```

## Task 3.2.2: Register `diff` CLI subcommand + bats

**Files:**
- Modify: `_lib/cli/planner_cmd.py`
- Test: `tests/integration/test_planner_cmd.bats`

- [ ] **Step 1: Add `diff` subparser**

```python
    sub.add_parser("diff", help="Compare stored vs computed state", parents=[common])
```

- [ ] **Step 2: Add `diff` handler in `cmd_planner`**

```python
        if ns.subcommand == "diff":
            from _lib.planner_sync import diff_state
            diff = diff_state(project_root)
            if not diff["has_baseline"]:
                sys.stdout.write("No baseline state on disk; nothing to diff.\n")
                return 0
            added = diff["unmapped_diff"]["added"]
            removed = diff["unmapped_diff"]["removed"]
            proj = diff["projects_diff"]
            if not added and not removed and not proj:
                sys.stdout.write("Stored and computed state agree.\n")
                return 0
            if added:
                sys.stdout.write(f"Unmapped added: {', '.join(added)}\n")
            if removed:
                sys.stdout.write(f"Unmapped removed: {', '.join(removed)}\n")
            for pid, fields in proj.items():
                diffs = ", ".join(f"{k}: {v[0]} -> {v[1]}" for k, v in fields.items())
                sys.stdout.write(f"{pid}: {diffs}\n")
            return 1
```

- [ ] **Step 3: Add bats**

In `tests/integration/test_planner_cmd.bats`:

```bash
@test "planner: diff with no baseline exits 0 with notice" {
    run python3 -m _lib.cli planner diff --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "No baseline" ]]
}

@test "planner: diff exits 0 when stored matches computed" {
    mkdir -p .rddf/improvements
    printf -- '---\nname: foo\npriority: P2\nroadmap_ref:\n  project_id: p1\n  phase: phase-1\n---\n# foo\n' > .rddf/improvements/foo.md
    python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP"
    run python3 -m _lib.cli planner diff --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Stored and computed state agree" ]]
}
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/unit/test_planner_cli.py -q
bats tests/integration/test_planner_cmd.bats
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add _lib/cli/planner_cmd.py tests/integration/test_planner_cmd.bats
git commit -m "feat(planner-cmd): add diff subcommand (stored vs computed)"
```

---

# Change 3.1 — `planner audit` subcommand

## Task 3.1.1: Create `_lib/planner_audit.py` + tests

**Files:**
- Create: `_lib/planner_audit.py`
- Test: `tests/unit/test_planner_audit.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for planner_audit."""
from __future__ import annotations

import json

import pytest

from _lib.planner_audit import (
    AuditRow,
    build_audit_rows,
    render_markdown,
    suggest_project_id,
)


def _setup_roadmap(parent, themes):
    rmp = parent / ".rddf" / "roadmap.md"
    rmp.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"| phase-1 | {t} | active | | |" for t in themes)
    rmp.write_text(f"# Roadmap\n\n## Phase Skeleton\n| Phase | Theme | Status | Started | Done |\n|-------|-------|--------|---------|------|\n{rows}\n\n<!-- AUTO-INDEX -->\n")


def _setup_improvement(parent, name, *, priority="P2", feedback_block="", last_feedback_id=None):
    imp = parent / ".rddf" / "improvements" / f"{name}.md"
    imp.parent.mkdir(parents=True, exist_ok=True)
    fm = f"---\nname: {name}\npriority: {priority}\n"
    if last_feedback_id:
        fm += f"last_feedback_id: {last_feedback_id}\n"
    fm += "---\n# proposal\n"
    if feedback_block:
        fm += f"\n## Feedback\n\n{feedback_block}"
    imp.write_text(fm)


def test_suggest_project_id_exact_substring_match():
    assert suggest_project_id("add-foo-bar", ["foo bar", "baz"]) == "foo bar"


def test_suggest_project_id_no_match_returns_none():
    assert suggest_project_id("xyzzy-1234", ["foo bar"]) is None


def test_build_audit_rows_includes_unmapped_with_suggestion(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"])
    _setup_improvement(tmp_path, "add-foo-bar-baz")
    rows = build_audit_rows(tmp_path)
    assert len(rows) == 1
    r = rows[0]
    assert r.propro == "add-foo-bar-baz"
    assert r.priority == "P2"
    assert r.suggested_project_id == "foo bar"


def test_build_audit_rows_groups_by_priority(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"])
    _setup_improvement(tmp_path, "a", priority="P0")
    _setup_improvement(tmp_path, "b", priority="P2")
    rows = build_audit_rows(tmp_path)
    priorities = [r.priority for r in rows]
    assert priorities[0] == "P0"  # P0 sorted first


def test_build_audit_rows_marks_feedback_status(tmp_path):
    _setup_roadmap(tmp_path, themes=["foo bar"])
    _setup_improvement(tmp_path, "needs-rev", priority="P1",
                       feedback_block="### fb-x\n- **kind**: needs-revision\n- **resolution**: open\n",
                       last_feedback_id="fb-x")
    rows = build_audit_rows(tmp_path)
    assert rows[0].feedback_status == "needs-revision"


def test_render_markdown_outputs_human_table():
    from dataclasses import asdict
    rows = [
        AuditRow(propro="x", priority="P2", feedback_status="none", suggested_project_id="foo bar"),
        AuditRow(propro="y", priority="P0", feedback_status="needs-revision", suggested_project_id=None),
    ]
    md = render_markdown(rows)
    assert "| Proposal | Priority | Feedback | Suggested project_id |" in md
    assert "| x | P2 | none | foo bar |" in md
    assert "| y | P0 | needs-revision | _(manual)_ |" in md
```

- [ ] **Step 2: Run tests, verify failure**

```bash
python3 -m pytest tests/unit/test_planner_audit.py -q
```

Expected: module not found / `AuditRow` undefined.

- [ ] **Step 3: Create `_lib/planner_audit.py`**

```python
"""Read-only audit of unmapped proposals.

Produces a prioritized list of `.rddf/improvements/*.md` files
without a `roadmap_ref`, grouped by priority, with a heuristic
project_id suggestion (substring match against Phase Skeleton Theme
column / fragment 主题). Pure derived view; no mutation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from _lib.planner_sync import discover_projects
from _lib.planner_attach import list_valid_projects

__all__ = ["AuditRow", "build_audit_rows", "render_markdown", "suggest_project_id"]


@dataclass
class AuditRow:
    propro: str
    priority: str
    feedback_status: str
    suggested_project_id: str | None


def suggest_project_id(proposal_name: str, valid_projects: Iterable[str]) -> str | None:
    """Return the first Theme whose tokens appear as a substring of the proposal name.

    Substring match only (case-sensitive); no fuzzy / semantic matching.
    Returns None when no Theme matches.
    """
    for theme in valid_projects:
        if theme and theme in proposal_name:
            return theme
    return None


def build_audit_rows(project_root: Path) -> list[AuditRow]:
    valid_projects = list_valid_projects(project_root)
    projects = discover_projects(project_root)
    rows: list[AuditRow] = []
    for p in projects:
        if p["mapped"]:
            continue
        rows.append(AuditRow(
            propro=p["proposal"],
            priority=p.get("priority") or "P2",
            feedback_status=p.get("feedback_status") or "none",
            suggested_project_id=suggest_project_id(p["proposal"], valid_projects),
        ))
    priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    rows.sort(key=lambda r: (priority_rank.get(r.priority, 9), r.propro))
    return rows


def render_markdown(rows: list[AuditRow]) -> str:
    if not rows:
        return "_No unmapped proposals._\n"
    lines = [
        "| Proposal | Priority | Feedback | Suggested project_id |",
        "|----------|----------|----------|----------------------|",
    ]
    for r in rows:
        sug = r.suggested_project_id if r.suggested_project_id else "_(manual)_"
        lines.append(f"| {r.propro} | {r.priority} | {r.feedback_status} | {sug} |")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/unit/test_planner_audit.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add _lib/planner_audit.py tests/unit/test_planner_audit.py
git commit -m "feat(planner-audit): unmapped proposal audit with substring suggestion"
```

## Task 3.1.2: Register `audit [--json]` subcommand

**Files:**
- Modify: `_lib/cli/planner_cmd.py`
- Test: `tests/integration/test_planner_cmd.bats`

- [ ] **Step 1: Add `audit` subparser**

```python
    p_audit = sub.add_parser("audit", help="List unmapped proposals (read-only)", parents=[common])
    p_audit.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")
```

- [ ] **Step 2: Add `audit` handler**

```python
        if ns.subcommand == "audit":
            from _lib.planner_audit import build_audit_rows, render_markdown
            rows = build_audit_rows(project_root)
            if ns.json:
                from dataclasses import asdict
                sys.stdout.write(json.dumps([asdict(r) for r in rows], indent ensure=False, ensure_ascii=False))
            else:
                sys.stdout.write(render_markdown(rows))
            return 0
```

(Add `import json` to the top of the file.)

- [ ] **Step 3: Add bats**

```bash
@test "planner: audit lists unmapped proposals in Markdown" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | foo bar | active | | |
EOF
    printf -- '---\nname: add-foo-bar-baz\npriority: P2\n---\n# x\n' > .rddf/improvements/add-foo-bar-baz.md
    run python3 -m _lib.cli planner audit --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "add-foo-bar-baz" ]]
    [[ "$output" =~ "foo bar" ]]
}

@test "planner: audit --json outputs structured list" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap
## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | foo bar | active | | |
EOF
    printf -- '---\nname: z\npriority: P2\n---\n# x\n' > .rddf/improvements/z.md
    run python3 -m _lib.cli planner audit --json --project-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"propro": "z"' ]]
}
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/unit/test_planner_cli.py -q
bats tests/integration/test_planner_cmd.bats
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add _lib/cli/planner_cmd.py tests/integration/test_planner_cmd.bats
git commit -m "feat(planner-cmd): add audit subcommand (Markdown + --json)"
```

---

# Change 3.3 — Incremental warning via `previous_unmapped`

## Task 3.3.1: Add `previous_unmapped` to schema + capture in `apply_state`

**Files:**
- Modify: `_lib/schemas/planner_state_schema.json`
- Modify: `_lib/planner_sync.py`
- Test: `tests/unit/test_planner_sync.py`

- [ ] **Step 1: Add failing tests**

```python
def test_apply_state_warns_when_newly_unmapped(tmp_path, capsys):
    """First sync captures baseline; second sync detects newly added unmapped."""
    _make_improvement(tmp_path, "u1")
    apply_state(tmp_path, render_state(tmp_path))
    _make_improvement(tmp_path, "u2")
    captured = capsys.readouterr()
    # apply_state does not currently print; we add a helper that does
    from _lib.planner_sync import apply_state_with_warnings
    apply_state_with_warnings(tmp_path, render_state(tmp_path))
    out2 = capsys.readouterr()
    assert "u2" in out2.out


def test_apply_state_no_warning_when_only_existing_unmapped(tmp_path):
    _make_improvement(tmp_path, "u1")
    apply_state(tmp_path, render_state(tmp_path))
    from _lib.planner_sync import apply_state_with_warnings
    # no new unmapped
    out = apply_state_with_warnings(tmp_path, render_state(tmp_path))
    assert "newly unmapped" not in out.lower()
```

- [ ] **Step 2: Run tests, verify failure**

```bash
python3 -m pytest tests/unit/test_planner_sync.py -q -k "warns_when_newly_unmapped or no_warning_when_only_existing"
```

Expected: 2 failed.

- [ ] **Step 3: Update schema**

In `_lib/schemas/planner_state_schema.json`, add to properties:

```json
    "previous_unmapped": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Unmapped proposal names captured at the previous sync (additive v1)."
    },
```

(`previous_unmapped` is optional; absence means baseline == current, suppressing first-run warning.)

- [ ] **Step 4: Implement `apply_state_with_warnings`**

In `_lib/planner_sync.py`:

```python
def apply_state_with_warnings(project_root: Path, state: Dict[str, Any]) -> str:
    """Like apply_state, but emits a stdout warning listing newly added unmapped proposals.

    Returns the warning text (empty string when no new unmapped).
    Compares the `unmapped_proposals` list against the previous sync's
    stored `previous_unmapped`. On first sync (state file missing or
    no previous_unmapped), baseline equals current — no warning.
    """
    current_unmapped = list(state.get("unmapped_proposals") or [])
    try:
        from _lib.planner_state import read_state
        existing = read_state(project_root)
        previous = list(existing.get("previous_unmapped") or current_unmapped)
    except Exception:
        previous = current_unmapped

    state_with_baseline = dict(state)
    state_with_baseline["previous_unmapped"] = current_unmapped

    apply_state(project_root, state_with_baseline)

    newly = [name for name in current_unmapped if name not in previous]
    if newly:
        msg = f"⚠ newly unmapped proposals (vs prior sync): {', '.join(newly)}\n"
        sys.stdout.write(msg)
        return msg
    return ""
```

Add `import sys` at top of planner_sync.py if not present.

- [ ] **Step 5: Wire into CLI `sync --apply`**

In `_lib/cli/planner_cmd.py`, replace:

```python
            apply_state(project_root, state)
```

with:

```python
            from _lib.planner_sync import apply_state_with_warnings as _apply_state_with_warn
            _apply_state_with_warn(project_root, state)
```

- [ ] **Step 6: Update existing `test_apply_state_*` tests if needed**

`apply_state` is still exported; existing callers (delegation tests) work as-is. Verify the `test_apply_state_writes_planner_state_and_roadmap` test still passes — it calls `apply_state` directly.

- [ ] **Step 7: Run tests**

```bash
python3 -m pytest tests/unit/test_planner_sync.py tests/unit/test_planner_cli.py tests/unit/test_planner_state.py -q
bats tests/integration/test_planner_cmd.bats
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add _lib/schemas/planner_state_schema.json _lib/planner_sync.py _lib/cli/planner_cmd.py tests/unit/test_planner_sync.py
git commit -m "feat(planner): incremental unmapped warning via previous_unmapped baseline"
```

---

# Wave 2 verification

## Task 4: Run all gates

**Files:** None unless verification finds a change-caused defect.

- [ ] **Step 1: Run focused suites**

```bash
python3 -m pytest tests/unit/test_roadmap_sprint.py tests/unit/test_planner_state.py tests/unit/test_planner_sync.py tests/unit/test_planner_cli.py tests/unit/test_planner_attach.py tests/unit/test_planner_audit.py tests/unit/test_feedback_appender.py tests/unit/test_feedback_cli.py tests/unit/test_adr_index_gate.py tests/unit/test_adr_index_generator.py tests/integration/test_iteration_lifecycle.py -q
bats tests/integration/test_planner_cmd.bats tests/integration/test_feedback_cmd.bats
```

Expected: all pass.

- [ ] **Step 2: Run repository full regression**

```bash
./test.sh --python
bats tests/smoke.bats
```

Expected: exit 0; no new failures vs `tests/KNOWN_FAILURES.txt`.

- [ ] **Step 3: Verify invariants**

```bash
git status --short .rddf/improvements/
git log --oneline -10
```

Expected: 226 improvements untouched; 5 commits since Wave 1.

- [ ] **Step 4: Final review of Wave 2 commits**

Check each commit's diff for: no type suppression, no empty catches, no unrelated refactor, no bulk improvement rewrite, no second AUTO-SPRINT writer.

---

# Self-review

- 3.5 is the P0 prerequisite for 3.1; failing to land it first would re-open the one-shot trap Oracle warned about.
- 3.4b is decoupled from the others — it can land at any point without blocking or being blocked.
- 3.2 has no upstream dependency and feeds trust-signal into Wave 3 history diffs.
- 3.3 lands last to let Wave 1's two new subcommands (3.1, 3.2) stabilize before introducing the precedent for additive state evolution.
- Schema stays at version 1 (additive `previous_unmapped`).
- No change touches `.rddf/improvements/*.md` outside the explicit one-proposal attach path.
- The single-writer enforcement from 3.4b is the only structural guard; it must reference the same literal the code uses.