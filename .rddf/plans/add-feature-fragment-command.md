# add-feature-fragment-command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `rddf roadmap add-feature <name>` CLI primitive that creates `.rddf/roadmap/features/feat-<name>.md` fragment files (with valid frontmatter + 3-section body skeleton) and refreshes `.rddf/roadmap.md` AUTO-INDEX, eliminating the manual `cat > features/...` + manual `render_fragment_index` invocation gap.

**Architecture:** 4-layer (UI → CLI → Library → Filesystem). Mirror existing `rddf roadmap migrate` and `validate-fragments` pattern. Python core `_lib/roadmap_state.py::add_feature` uses existing Fragment dataclass + 6 additive APIs (`list_active_fragments`, `load_fragments`, `render_fragment_index`, `validate_fragment_refs`). Thin shell wrapper `skills/roadmap/scripts/roadmap_add_feature.sh` parses CLI args + env-var passes (Oracle C1). Atomic write (tmp + `os.replace`) with compensating rollback if render fails.

**Tech Stack:** Python 3.11+ (dataclass, pathlib, os.replace) + bash 4+ (CLI wrapper) + bats 1.10+ (integration tests).

**OpenSpec change artifacts** (canonical): `openspec/changes/add-feature-fragment-command/{proposal.md (140 lines), design.md (7 decisions), tasks.md (17 tasks)}` + `specs/roadmap-feature-fragment/spec.md` (5 Requirements, 17 Scenarios).

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/roadmap_state.py` | MODIFY: add `add_feature(name, phase_refs, theme, status, force, project_root)` function (~95 lines) |
| `skills/roadmap/scripts/roadmap_add_feature.sh` | NEW: thin shell wrapper, env-var passing (Oracle C1) |
| `_lib/cli/roadmap_cmd.py` | MODIFY: extend `_SUBCOMMAND_MAP` + update `_help_text()` |
| `skills/guide-arch/SKILL.md` | MODIFY: Phase 4 menu add "添加 feature fragment" option + 4-step interaction + ADR-0028 frontmatter `owns` patch |
| `skills/roadmap/SKILL.md` | MODIFY: register add-feature subcommand section |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_roadmap_state.py` | MODIFY: add 7 new tests for `add_feature` |
| `tests/integration/test_roadmap_add_feature.bats` | NEW: 4 bats tests |

### Documentation

| File | Responsibility |
|---|---|
| `CHANGELOG.md` | MODIFY: add v2.2+ entry |
| `README.md` | MODIFY: Roadmap section link to add-feature subcommand |
| `skills/guide-design/scripts/approve_proposal.sh` | MODIFY: fix `.openspec.yaml` schema field (P1 bug fix already in `baa76e9`; verify task T14 already done) |

---

## Pre-flight

- [ ] **Verify baseline tests pass before changes**

```bash
cd /workspace/project/rdd-workflow
bats tests/smoke.bats
```
Expected: 7 smoke cases pass.

- [ ] **Verify Fragment API surface**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -c "
from _lib.roadmap_state import (
    Fragment, load_fragments, get_fragment,
    list_active_fragments, render_fragment_index,
    validate_fragment_refs, aggregate_phase_progress,
)
print('all 6 additive APIs present')
"
```
Expected: `all 6 additive APIs present`

- [ ] **Confirm we're on the right branch**

```bash
cd /workspace/project/rdd-workflow
git branch --show-current
```
Expected: `openspec/add-feature-fragment-command` (per `ship_plan.sh` lightweight setup)

---

## Task 1: add_feature main function (core orchestration)

**Files:**
- Modify: `_lib/roadmap_state.py:1-5` (imports)
- Modify: `_lib/roadmap_state.py` (append new function after `aggregate_phase_progress` ~L800)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_roadmap_state.py (append)
def test_add_feature_creates_file_with_frontmatter(tmp_path, monkeypatch):
    """Verify frontmatter keys exactly match §5 schema."""
    # Setup: create minimal .rddf/roadmap/ with 1 phase
    (tmp_path / ".rddf/roadmap").mkdir(parents=True)
    (tmp_path / ".rddf/roadmap/phases").mkdir()
    (tmp_path / ".rddf/roadmap.md").write_text(
        "# Roadmap\n\n## Phase Skeleton\n\n| Phase | Theme | Status |\n|-------|-------|--------|\n"
    )
    phase_file = tmp_path / ".rddf/roadmap/phases/phase-1.md"
    phase_file.write_text("---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n主题: test\n---\n\n# phase-1\n")

    # Action
    from _lib.roadmap_state import add_feature
    result = add_feature(
        name="auth-v2",
        phase_refs=["phase-1"],
        theme="RBAC 权限模型",
        status="active",
        force=False,
        project_root=str(tmp_path),
    )

    # Assertions
    fragment_path = tmp_path / ".rddf/roadmap/features/feat-auth-v2.md"
    assert fragment_path.exists()
    content = fragment_path.read_text(encoding="utf-8")
    assert "id: feat-auth-v2" in content
    assert "kind: feature" in content
    assert "status: active" in content
    assert "phase_refs: [phase-1]" in content
    assert "主题: RBAC 权限模型" in content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_creates_file_with_frontmatter -v
```
Expected: FAIL with `ImportError: cannot import name 'add_feature'`

- [ ] **Step 3: Write minimal implementation (full function)**

```python
# _lib/roadmap_state.py (append after aggregate_phase_progress)
from typing import Tuple


def add_feature(
    name: str,
    phase_refs: list,
    theme: str,
    status: str = "active",
    force: bool = False,
    project_root: str = ".",
) -> dict:
    """Create a feature fragment file and refresh AUTO-INDEX.

    Args:
        name: kebab-case feature id (CLI auto-prepends 'feat-').
        phase_refs: list of phase IDs that this feature spans.
        theme: single-line 主题 (CJK ok, ≤ 50 chars recommended).
        status: 'active' | 'done' | 'archived' (default: 'active').
        force: overwrite existing feat-<name>.md (default: False).
        project_root: absolute path to project root.

    Returns:
        Dict with keys: path (str), main_doc_refreshed (bool).

    Raises:
        ValueError: if name is not kebab-case, phase_refs is empty,
            theme is empty, or status is invalid.
        FileExistsError: if feat-<name>.md exists and force=False.
    """
    import re
    from pathlib import Path

    # 1. Validate name format (kebab-case)
    if not re.match(r"^[a-z][a-z0-9-]*$", name):
        raise ValueError(f"name must be kebab-case, got: {name!r}")
    if not phase_refs:
        raise ValueError("phase_refs must be non-empty")
    if not theme or "\n" in theme:
        raise ValueError(f"theme must be non-empty single-line, got: {theme!r}")
    if status not in ("active", "done", "archived"):
        raise ValueError(f"status must be active/done/archived, got: {status!r}")

    fragment_id = f"feat-{name}"
    root = Path(project_root)
    fragments_dir = root / ".rddf" / "roadmap"
    features_dir = fragments_dir / "features"
    fragment_path = features_dir / f"{fragment_id}.md"
    main_doc = fragments_dir / "roadmap.md"  # actual location: .rddf/roadmap.md

    # 2. Check duplicate
    if fragment_path.exists() and not force:
        raise FileExistsError(
            f"{fragment_path.name} already exists; use force=True to overwrite"
        )

    # 3. Validate phase_refs via list_active_fragments (single read path)
    active_phases = list_active_fragments(str(fragments_dir), kind="phase")
    active_phase_ids = {p.id for p in active_phases}
    invalid = [ref for ref in phase_refs if ref not in active_phase_ids]
    if invalid:
        raise ValueError(f"unknown phase_refs: {invalid}")

    # 4. Build frontmatter
    phase_refs_yaml = "[" + ", ".join(phase_refs) + "]"
    frontmatter = (
        f"---\n"
        f"id: {fragment_id}\n"
        f"kind: feature\n"
        f"status: {status}\n"
        f"phase_refs: {phase_refs_yaml}\n"
        f"主题: {theme}\n"
        f"---\n"
    )

    # 5. Build body skeleton (3 sections)
    phase_sections = "\n".join(
        f"### {ref}\n<TBD - 此阶段内的子任务清单>\n" for ref in phase_refs
    )
    body = (
        f"\n## 概述\n"
        f"<TBD - 用户后续编辑>\n\n"
        f"## 跨阶段拆分\n\n"
        f"{phase_sections}\n\n"
        f"## 验收标准\n"
        f"<TBD - markdown checkbox 列表, design/plan 阶段消费>\n"
    )

    # 6. Atomic write (tmp + os.replace)
    import os
    import tempfile

    features_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(features_dir),
        prefix=f".{fragment_id}.tmp.",
        suffix=".md",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(frontmatter + body)
        os.replace(tmp_path, fragment_path)
    except OSError:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    # 7. Render AUTO-INDEX with compensating rollback
    try:
        render_fragment_index(str(fragments_dir), str(fragments_dir / "roadmap.md"))
    except Exception:
        # Compensating rollback: delete the just-written fragment
        if fragment_path.exists():
            fragment_path.unlink()
        raise

    return {"path": str(fragment_path), "main_doc_refreshed": True}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_creates_file_with_frontmatter -v
```
Expected: PASS

- [ ] **Step 5: Defer commit**

No commit yet — defer to archive phase (per `worktree-archive-workflow` v2.0.5+ rule).

---

## Task 2: Auto-create features/ directory if missing

**Files:**
- Modify: `_lib/roadmap_state.py` (already done in Task 1 — features_dir.mkdir with exist_ok)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_roadmap_state.py (append)
def test_add_feature_mkdir_features_dir(tmp_path):
    """features/ missing → auto-created."""
    (tmp_path / ".rddf/roadmap").mkdir(parents=True)
    (tmp_path / ".rddf/roadmap/phases").mkdir()
    (tmp_path / ".rddf/roadmap.md").write_text("# Roadmap\n\n## Phase Skeleton\n\n")
    phase_file = tmp_path / ".rddf/roadmap/phases/phase-1.md"
    phase_file.write_text("---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n---\n")

    assert not (tmp_path / ".rddf/roadmap/features").exists()  # precondition

    from _lib.roadmap_state import add_feature
    add_feature(
        name="auto-mkdir",
        phase_refs=["phase-1"],
        theme="test",
        project_root=str(tmp_path),
    )

    assert (tmp_path / ".rddf/roadmap/features").exists()
    assert (tmp_path / ".rddf/roadmap/features/feat-auto-mkdir.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_mkdir_features_dir -v
```
Expected: PASS (already covered by Task 1's `features_dir.mkdir(exist_ok=True)` — verify Task 1 implementation handles this)

If PASS: mark this task complete (Task 1 implementation already covers). If FAIL: investigate why `mkdir(exist_ok=True)` did not fire.

- [ ] **Step 3: Verify Task 1 implementation**

```bash
cd /workspace/project/rdd-workflow
grep -A 2 "features_dir.mkdir" _lib/roadmap_state.py
```
Expected: `features_dir.mkdir(parents=True, exist_ok=True)` present (from Task 1)

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_mkdir_features_dir -v
```
Expected: PASS

- [ ] **Step 5: Defer commit**

---

## Task 3: Validate phase_refs against list_active_fragments

**Files:**
- Modify: `_lib/roadmap_state.py` (already done in Task 1 — `active_phase_ids = {p.id for p in active_phases}`)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_roadmap_state.py (append)
def test_add_feature_validates_phase_refs(tmp_path):
    """Unknown phase id → ValueError, no file written."""
    (tmp_path / ".rddf/roadmap").mkdir(parents=True)
    (tmp_path / ".rddf/roadmap/phases").mkdir()
    (tmp_path / ".rddf/roadmap.md").write_text("# Roadmap\n\n")
    phase_file = tmp_path / ".rddf/roadmap/phases/phase-1.md"
    phase_file.write_text("---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n---\n")

    from _lib.roadmap_state import add_feature
    with pytest.raises(ValueError, match="unknown phase_refs"):
        add_feature(
            name="bad-refs",
            phase_refs=["phase-2", "phase-99"],
            theme="test",
            project_root=str(tmp_path),
        )

    # No file written
    assert not (tmp_path / ".rddf/roadmap/features/feat-bad-refs.md").exists()

    # Also: empty phase_refs rejected
    with pytest.raises(ValueError, match="phase_refs must be non-empty"):
        add_feature(
            name="empty-refs",
            phase_refs=[],
            theme="test",
            project_root=str(tmp_path),
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_validates_phase_refs -v
```
Expected: PASS (already covered by Task 1's `if invalid: raise ValueError` block)

- [ ] **Step 3: Verify Task 1 implementation**

```bash
cd /workspace/project/rdd-workflow
grep -B 1 -A 3 "invalid = " _lib/roadmap_state.py
```
Expected: shows `invalid = [ref for ref in phase_refs if ref not in active_phase_ids]` followed by `if invalid: raise ValueError(f"unknown phase_refs: {invalid}")`

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_validates_phase_refs -v
```
Expected: PASS

- [ ] **Step 5: Defer commit**

---

## Task 4: Duplicate detection (without --force rejected)

**Files:**
- Modify: `_lib/roadmap_state.py` (already done in Task 1)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_roadmap_state.py (append)
def test_add_feature_rejects_duplicate_id(tmp_path):
    """Existing feat-<name>.md without force → FileExistsError, no overwrite."""
    (tmp_path / ".rddf/roadmap").mkdir(parents=True)
    (tmp_path / ".rddf/roadmap/phases").mkdir()
    (tmp_path / ".rddf/roadmap.md").write_text("# Roadmap\n\n")
    phase_file = tmp_path / ".rddf/roadmap/phases/phase-1.md"
    phase_file.write_text("---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n---\n")

    from _lib.roadmap_state import add_feature
    # First creation succeeds
    add_feature(
        name="dup-test",
        phase_refs=["phase-1"],
        theme="first",
        project_root=str(tmp_path),
    )
    fragment_path = tmp_path / ".rddf/roadmap/features/feat-dup-test.md"
    original_content = fragment_path.read_text()
    assert "first" in original_content

    # Second creation without force → reject
    with pytest.raises(FileExistsError, match="already exists"):
        add_feature(
            name="dup-test",
            phase_refs=["phase-1"],
            theme="second-attempt",
            project_root=str(tmp_path),
        )

    # File unchanged
    assert fragment_path.read_text() == original_content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_rejects_duplicate_id -v
```
Expected: PASS (already covered by Task 1's `if fragment_path.exists() and not force: raise FileExistsError`)

- [ ] **Step 3: Verify Task 1 implementation**

```bash
cd /workspace/project/rdd-workflow
grep -B 1 -A 3 "if fragment_path.exists" _lib/roadmap_state.py
```
Expected: shows the check + raise block

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_rejects_duplicate_id -v
```
Expected: PASS

- [ ] **Step 5: Defer commit**

---

## Task 5: --force fully regenerates (no merge)

**Files:**
- Modify: `_lib/roadmap_state.py` (already done in Task 1)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_roadmap_state.py (append)
def test_add_feature_force_regenerates(tmp_path):
    """--force overwrites frontmatter + body; no merge."""
    (tmp_path / ".rddf/roadmap").mkdir(parents=True)
    (tmp_path / ".rddf/roadmap/phases").mkdir()
    (tmp_path / ".rddf/roadmap.md").write_text("# Roadmap\n\n")
    phase_file = tmp_path / ".rddf/roadmap/phases/phase-1.md"
    phase_file.write_text("---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n---\n")

    from _lib.roadmap_state import add_feature
    add_feature(
        name="force-test",
        phase_refs=["phase-1"],
        theme="first theme",
        status="active",
        project_root=str(tmp_path),
    )

    # Manually edit body to simulate user edit
    fragment_path = tmp_path / ".rddf/roadmap/features/feat-force-test.md"
    edited = fragment_path.read_text().replace("<TBD - 用户后续编辑>", "USER EDIT")
    fragment_path.write_text(edited)
    assert "USER EDIT" in fragment_path.read_text()

    # --force overwrites
    add_feature(
        name="force-test",
        phase_refs=["phase-1"],
        theme="second theme",
        status="done",
        force=True,
        project_root=str(tmp_path),
    )

    new_content = fragment_path.read_text()
    assert "second theme" in new_content
    assert "status: done" in new_content
    assert "USER EDIT" not in new_content  # user edit destroyed (no merge)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_force_regenerates -v
```
Expected: PASS (covered by Task 1's `os.replace` after fresh write — replaces file wholesale)

- [ ] **Step 3: Verify Task 1 implementation**

```bash
cd /workspace/project/rdd-workflow
grep -A 1 "os.replace" _lib/roadmap_state.py
```
Expected: `os.replace(tmp_path, fragment_path)` present (atomic overwrite)

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_force_regenerates -v
```
Expected: PASS

- [ ] **Step 5: Defer commit**

---

## Task 6: render_fragment_index refresh + AUTO-INDEX update

**Files:**
- Modify: `_lib/roadmap_state.py` (already done in Task 1)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_roadmap_state.py (append)
def test_add_feature_renders_auto_index(tmp_path):
    """Main doc gains Features section after success."""
    (tmp_path / ".rddf/roadmap").mkdir(parents=True)
    (tmp_path / ".rddf/roadmap/phases").mkdir()
    main_doc = tmp_path / ".rddf/roadmap.md"
    main_doc.write_text("# Roadmap\n\n## Phase Skeleton\n\n")
    phase_file = tmp_path / ".rddf/roadmap/phases/phase-1.md"
    phase_file.write_text("---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n主题: test\n---\n")

    from _lib.roadmap_state import add_feature
    add_feature(
        name="index-test",
        phase_refs=["phase-1"],
        theme="indexed",
        project_root=str(tmp_path),
    )

    content = main_doc.read_text()
    assert "<!-- AUTO-INDEX -->" in content
    assert "### Features" in content
    assert "feat-index-test" in content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_renders_auto_index -v
```
Expected: PASS (covered by Task 1's `render_fragment_index(...)` call after write)

- [ ] **Step 3: Verify Task 1 implementation**

```bash
cd /workspace/project/rdd-workflow
grep -A 1 "render_fragment_index" _lib/roadmap_state.py
```
Expected: `render_fragment_index(str(fragments_dir), str(fragments_dir / "roadmap.md"))` call present

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_add_feature_renders_auto_index -v
```
Expected: PASS

- [ ] **Step 5: Defer commit**

---

## Task 7: load_fragments missing subdir tolerance (regression lock)

**Files:**
- Modify: `tests/unit/test_roadmap_state.py` (add test only — `_lib/roadmap_state.py::load_fragments` already tolerates per `add-hierarchical-roadmap-structure`)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_roadmap_state.py (append)
def test_load_fragments_missing_subdir_tolerance(tmp_path):
    """features/ missing → load_fragments returns empty list (no exception)."""
    (tmp_path / ".rddf/roadmap").mkdir(parents=True)
    # Deliberately NOT creating features/ subdir

    from _lib.roadmap_state import load_fragments
    result = load_fragments(str(tmp_path / ".rddf/roadmap"))
    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_load_fragments_missing_subdir_tolerance -v
```
Expected: PASS (regression lock for existing tolerant behavior — verify load_fragments handles missing subdir)

If FAIL: file a separate bug fix change; do NOT modify load_fragments here.

- [ ] **Step 3: Verify existing implementation**

```bash
cd /workspace/project/rdd-workflow
grep -A 5 "for sub in" _lib/roadmap_state.py | head -10
```
Expected: shows `for sub in ("phases", "features", "archive")` followed by `if not sub_path.exists(): continue`

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py::test_load_fragments_missing_subdir_tolerance -v
```
Expected: PASS

- [ ] **Step 5: Defer commit**

---

## Task 8: Shell wrapper (env-var passing per Oracle C1)

**Files:**
- Create: `skills/roadmap/scripts/roadmap_add_feature.sh`

- [ ] **Step 1: Write the failing test (bats)**

```bash
# tests/integration/test_roadmap_add_feature.bats (new file)
@test "roadmap_add_feature_sh: exists and has execute bit" {
    [ -f "$REPO_ROOT/skills/roadmap/scripts/roadmap_add_feature.sh" ]
    [ -x "$REPO_ROOT/skills/roadmap/scripts/roadmap_add_feature.sh" ]
}

@test "roadmap_add_feature_sh: rejects missing name" {
    run bash "$REPO_ROOT/skills/roadmap/scripts/roadmap_add_feature.sh" --phase-refs phase-1 --theme "test"
    [ "$status" -eq 2 ]  # usage error
}

@test "roadmap_add_feature_sh: rejects missing phase-refs" {
    run bash "$REPO_ROOT/skills/roadmap/scripts/roadmap_add_feature.sh" --name "test" --theme "test"
    [ "$status" -eq 2 ]  # usage error
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_add_feature.bats
```
Expected: FAIL (script does not exist)

- [ ] **Step 3: Write shell wrapper**

```bash
# skills/roadmap/scripts/roadmap_add_feature.sh
#!/usr/bin/env bash
# skills/roadmap/scripts/roadmap_add_feature.sh
# Env-var only pattern (Oracle C1) — no inline python3 -c "...$VAR..." interpolation.
#
# Usage:
#   rddf roadmap add-feature <name> [options]
#
# Options:
#   --phase-refs <p1,p2,...>    Required. Comma-separated phase IDs.
#   --theme "<text>"            Required. Single-line 主题.
#   --status <a|d|x>            Optional. Default: a (active).
#   --force                     Optional. Overwrite existing feat-<name>.md.
#
# Exit codes:
#   0  success
#   1  validation error (phase_refs invalid / duplicate without --force)
#   2  usage error (missing arg / malformed flag)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

NAME=""
PHASE_REFS=""
THEME=""
STATUS="active"
FORCE="false"

while [ $# -gt 0 ]; do
    case "$1" in
        --phase-refs) PHASE_REFS="$2"; shift 2 ;;
        --theme) THEME="$2"; shift 2 ;;
        --status)
            case "$2" in
                a|active) STATUS="active" ;;
                d|done) STATUS="done" ;;
                x|archived) STATUS="archived" ;;
                *) echo "❌ invalid --status: $2 (expected a|d|x)" >&2; exit 2 ;;
            esac
            shift 2
            ;;
        --force) FORCE="true"; shift ;;
        -h|--help)
            echo "Usage: rddf roadmap add-feature <name> --phase-refs <...> --theme <text> [--status a|d|x] [--force]"
            exit 0
            ;;
        *)
            if [ -z "$NAME" ]; then NAME="$1"; shift; else
                echo "❌ unexpected positional arg: $1" >&2; exit 2
            fi
            ;;
    esac
done

if [ -z "$NAME" ]; then
    echo "❌ name required (positional)" >&2
    exit 2
fi
if [ -z "$PHASE_REFS" ]; then
    echo "❌ --phase-refs required" >&2
    exit 2
fi
if [ -z "$THEME" ]; then
    echo "❌ --theme required" >&2
    exit 2
fi

PROJECT_ROOT="$PROJECT_ROOT" \
CHANGE_NAME="$NAME" \
PHASE_REFS="$PHASE_REFS" \
THEME="$THEME" \
STATUS="$STATUS" \
FORCE="$FORCE" \
python3 "$SCRIPT_DIR/../../../_lib/roadmap_state_wrapper.py"
```

- [ ] **Step 4: Write thin Python wrapper for env-var consumption**

```python
# _lib/roadmap_state_wrapper.py (new file)
"""Thin env-var consuming wrapper for roadmap_state CLI invocations.

Routes to the appropriate function based on env vars set by the shell wrapper.
"""
import os
import sys
import traceback


def main():
    project_root = os.environ.get("PROJECT_ROOT", ".")
    change_name = os.environ.get("CHANGE_NAME")
    phase_refs_raw = os.environ.get("PHASE_REFS", "")
    theme = os.environ.get("THEME", "")
    status = os.environ.get("STATUS", "active")
    force = os.environ.get("FORCE", "false").lower() == "true"

    if not change_name:
        print("❌ CHANGE_NAME env var not set", file=sys.stderr)
        sys.exit(2)

    phase_refs = [p.strip() for p in phase_refs_raw.split(",") if p.strip()]

    sys.path.insert(0, project_root)
    from _lib.roadmap_state import add_feature

    try:
        result = add_feature(
            name=change_name,
            phase_refs=phase_refs,
            theme=theme,
            status=status,
            force=force,
            project_root=project_root,
        )
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except FileExistsError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    print(f"✅ created: {result['path']}")
    print(f"✅ main doc refreshed: {result['main_doc_refreshed']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Make script executable + run tests**

```bash
cd /workspace/project/rdd-workflow
chmod +x skills/roadmap/scripts/roadmap_add_feature.sh
bats tests/integration/test_roadmap_add_feature.bats
```
Expected: PASS (3/3 tests)

- [ ] **Step 6: Defer commit**

---

## Task 9: CLI dispatch map extension (_lib/cli/roadmap_cmd.py)

**Files:**
- Modify: `_lib/cli/roadmap_cmd.py:25-40` (`_SUBCOMMAND_MAP` + `_help_text()`)

- [ ] **Step 1: Write the failing test**

```bash
# tests/integration/test_roadmap_add_feature.bats (append)
@test "rddf roadmap --help lists add-feature subcommand" {
    run bash -c "cd $REPO_ROOT && PROJECT_ROOT=$REPO_ROOT python3 _lib/cli/roadmap_cmd.py --help"
    [ "$status" -eq 0 ]
    [[ "$output" == *"add-feature"* ]]
}

@test "rddf roadmap add-feature unknown subcommand returns exit 2" {
    run bash -c "cd $REPO_ROOT && python3 _lib/cli/roadmap_cmd.py add-feature-bogus"
    [ "$status" -eq 2 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_add_feature.bats
```
Expected: FAIL (subcommand not in dispatch map)

- [ ] **Step 3: Extend dispatch map + help text**

```python
# _lib/cli/roadmap_cmd.py (modify)
def _help_text() -> str:
    return """rddf roadmap — 路线图管理子命令

用法:
  rddf roadmap <subcommand> [args...]

子命令:
  migrate             迁移扁平 roadmap 到 hierarchical 结构
    --dry-run            演练模式
    --execute --yes      真实迁移
    --rollback <dir>     回滚到备份

  validate-fragments    校验 fragment 引用 (8 规则 R1-R8)
    STRICT_ROADMAP_REFS_GATE=yes  升级 WARNING→CRITICAL
    SKIP_ROADMAP_REFS_GATE=yes    跳过校验

  add-feature           创建 feature fragment (rddf roadmap add-feature <name> ...)
    --phase-refs p1,p2,...   Required. Comma-separated phase IDs
    --theme "<text>"         Required. Single-line 主题
    --status a|d|x           Optional. Default: active
    --force                  Optional. Overwrite existing feat-<name>.md

使用 env var:
  SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR 覆盖默认 .rddf/roadmap
"""


def cmd_roadmap(args: list[str]) -> int:
    # ...
    _SUBCOMMAND_MAP = {
        "migrate": project_root / "skills" / "roadmap" / "scripts" / "roadmap_migrate.sh",
        "validate-fragments": project_root / "skills" / "roadmap" / "scripts" / "roadmap_validate_fragments.sh",
        "add-feature": project_root / "skills" / "roadmap" / "scripts" / "roadmap_add_feature.sh",  # NEW
    }
    # ...
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_add_feature.bats
```
Expected: PASS (2/2 new tests)

- [ ] **Step 5: Defer commit**

---

## Task 10: guide-arch Phase 4 menu integration

**Files:**
- Modify: `skills/guide-arch/SKILL.md` (Phase 4 menu example + 4-step interaction + ADR-0028 frontmatter `owns` patch)

- [ ] **Step 1: Write the failing test**

```bash
# tests/integration/test_roadmap_add_feature.bats (append)
@test "guide_arch_skill_contains_add_feature_option" {
    grep -q "添加 feature fragment" "$REPO_ROOT/skills/guide-arch/SKILL.md"
}

@test "guide_arch_skill_owns_includes_features" {
    grep -q "\.rddf/roadmap/features/\*\.md" "$REPO_ROOT/skills/guide-arch/SKILL.md"
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_add_feature.bats
```
Expected: FAIL

- [ ] **Step 3: Modify guide-arch SKILL.md (frontmatter + Phase 4 menu + 4-step interaction)**

```yaml
# skills/guide-arch/SKILL.md (frontmatter modify)
role:
  title: "Architect (架构治理者)"
  perspective: "..."
  boundaries:
    owns:
      - "docs/adr/ADR-*.md"
      - "roadmap.md"
      - "docs/architecture/*-gap-analysis.md"
      - ".rddf/state/.arch-handoff.json"
      - ".rddf/state/.populate-state.json"
      - ".rddf/roadmap/phases/*.md"
      - ".rddf/roadmap/features/*.md"   # NEW (ADR-0028 patch)
    not_owns:
      - ...
```

```
# skills/guide-arch/SKILL.md (Phase 4 menu modify)
=== 路线图定义 ===

当前状态: phase-1 (基础架构)
进度:
  - arch-design: 1/2 ✅
  - infra-setup: 0/1 ⏳
  - core-impl: 0/0

请选择:
  1. ✏️  编辑路线图（修改阶段或任务分类）
  2. 📊 查看路线图状态
  3. 📈 查看阶段门控报告
  4. ⏭️  强制推进到下一阶段
  5. ✨ 添加 feature fragment       ← NEW
  6. ✅ 完成路线图定义 → 进入 arch validation
  0. 💾 保存并退出
  i. 其他输入
```

```
# skills/guide-arch/SKILL.md (Phase 4 add 4-step interaction section after Phase 2)
### 选项 5（添加 feature fragment）执行内容

当用户选 5 时，调用 `rddf roadmap add-feature`，4 步强制交互（任一步失败 → 返回菜单，不写盘）：

1. **输入 name**：`kebab-case`（CLI 自动 `feat-` 前缀）；非空校验
2. **输入 theme**：单行中文短句（≤ 50 字）；非空校验
3. **多选 phase_refs**：从 `list_active_fragments(kind="phase")` 渲染编号列表；逗号分隔索引 → phase IDs；校验所有存在
4. **Preview + confirm**：渲染 frontmatter + 3 段骨架到 stderr；用户 `y` 才落盘（`n` 返回菜单）

具体 bash 块委托给 `skill_use("roadmap", "add-feature")` 或直接 `rddf roadmap add-feature <name> --phase-refs ... --theme "..."`。
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_add_feature.bats
```
Expected: PASS

- [ ] **Step 5: Defer commit**

---

## Task 11: roadmap SKILL.md add-feature subcommand docs

**Files:**
- Modify: `skills/roadmap/SKILL.md` (add add-feature section)

- [ ] **Step 1: Write the failing test**

```bash
# tests/integration/test_roadmap_add_feature.bats (append)
@test "roadmap_skill_documents_add_feature" {
    grep -q "add-feature" "$REPO_ROOT/skills/roadmap/SKILL.md"
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_add_feature.bats
```
Expected: FAIL

- [ ] **Step 3: Add subcommand docs to roadmap SKILL.md**

```markdown
# skills/roadmap/SKILL.md (append section)

## add-feature <name>

创建 feature fragment 文件并刷新 `.rddf/roadmap.md` AUTO-INDEX。

**用法**:
```bash
rddf roadmap add-feature <name> --phase-refs <p1,p2,...> --theme "<text>" [--status a|d|x] [--force]
```

**示例**:
```bash
# 最小化：创建跨 phase-2 和 phase-3 的 active feature
rddf roadmap add-feature auth-v2 \
    --phase-refs phase-2,phase-3 \
    --theme "RBAC 权限模型"

# 创建时标 done（罕见）
rddf roadmap add-feature deprecate-legacy-auth \
    --phase-refs phase-3 \
    --theme "下线旧版认证" \
    --status d

# 覆盖已有 fragment（销毁 body 编辑）
rddf roadmap add-feature auth-v2 \
    --phase-refs phase-2,phase-3 \
    --theme "RBAC 权限模型 (v2 重生)" \
    --force
```

**底层实现**: `_lib/roadmap_state.py::add_feature`（Python）+ `skills/roadmap/scripts/roadmap_add_feature.sh`（shell wrapper）
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_add_feature.bats
```
Expected: PASS

- [ ] **Step 5: Defer commit**

---

## Task 12: CHANGELOG.md v2.2+ entry

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write the failing test (manual)**

```bash
cd /workspace/project/rdd-workflow
grep -q "add-feature-fragment-command\|add-feature" CHANGELOG.md
```
Expected: FAIL

- [ ] **Step 2: Add CHANGELOG entry**

```markdown
# CHANGELOG.md (prepend to v2.2+ section)

## [Unreleased] — v2.2+

### Added
- **`rddf roadmap add-feature <name>` CLI primitive**: create `.rddf/roadmap/features/feat-<name>.md` fragments with valid frontmatter + 3-section body skeleton, refresh `.rddf/roadmap.md` AUTO-INDEX atomically. Closes the operation gap from `add-hierarchical-roadmap-structure` (scenario 3). P1.

### Changed
- **ADR-0028 patch**: `skills/guide-arch/SKILL.md` frontmatter `role.boundaries.owns` now explicitly includes `.rddf/roadmap/features/*.md` alongside `.rddf/roadmap/phases/*.md`.
- **`skills/guide-design/scripts/approve_proposal.sh`**: `.openspec.yaml` schema field is now correctly written (was previously `name + created_by`, now `schema: spec-driven + created: <date> + name: <name>` matching openspec CLI v1.7+).

### Fixed
- **`skills/guide-design/scripts/generate_full_proposal.py`**: `_extract_scope_items` now accepts both bold-line (`**In Scope**:`) and heading (`### In Scope`) formats, and uses `startswith` instead of exact match to tolerate `### Out of Scope（详见 spec §13）` style headers with annotations.
```

- [ ] **Step 3: Verify entry present**

```bash
cd /workspace/project/rdd-workflow
grep -q "rddf roadmap add-feature" CHANGELOG.md
```
Expected: PASS

- [ ] **Step 4: Defer commit**

---

## Task 13: README.md Roadmap section link

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the failing test (manual)**

```bash
cd /workspace/project/rdd-workflow
grep -q "add-feature" README.md
```
Expected: FAIL

- [ ] **Step 2: Add link to add-feature in Roadmap section**

```markdown
# README.md (modify Roadmap section)

### Roadmap Incremental Update (v2.2+)

`guide-arch` Phase 6 automatically invokes `roadmap_incremental_update.sh`...

### Roadmap feature fragments (v2.2+)

Create a feature fragment spanning multiple phases:

```bash
rddf roadmap add-feature <name> --phase-refs p1,p2,... --theme "<text>"
```

See `skills/roadmap/SKILL.md` for full CLI reference.
```

- [ ] **Step 3: Verify entry present**

```bash
cd /workspace/project/rdd-workflow
grep -q "rddf roadmap add-feature" README.md
```
Expected: PASS

- [ ] **Step 4: Defer commit**

---

## Task 14: Verify approve_proposal.sh fix already in place

**Files:**
- Verify: `skills/guide-design/scripts/approve_proposal.sh:374-378`

- [ ] **Step 1: Verify the bug fix is already committed**

```bash
cd /workspace/project/rdd-workflow
grep -A 3 "schema: spec-driven" skills/guide-design/scripts/approve_proposal.sh
```
Expected: shows the fix (committed in `baa76e9`)

- [ ] **Step 2: Verify via git log**

```bash
cd /workspace/project/rdd-workflow
git log --oneline -- skills/guide-design/scripts/approve_proposal.sh | head -3
```
Expected: most recent commit message mentions `fix(guide-design)` and `approve_proposal`

- [ ] **Step 3: Verify by re-running openspec instructions on existing approved change**

```bash
cd /workspace/project/rdd-workflow
openspec instructions design --change add-feature-fragment-command --json 2>&1 | head -5
```
Expected: JSON output (not `Invalid metadata: schema` error)

- [ ] **Step 4: Confirm**

This task is **already done** (committed in `baa76e9` during plan phase). No new changes needed.

- [ ] **Step 5: Defer commit**

---

## Task 15: Run all tests (Python unit + bats integration)

**Files:**
- Run: `./test.sh --python` + `bats tests/integration/test_roadmap_add_feature.bats`

- [ ] **Step 1: Run Python unit tests**

```bash
cd /workspace/project/rdd-workflow
PYTHONPATH=. python3 -m pytest tests/unit/test_roadmap_state.py -v --tb=short
```
Expected: All 7 new tests pass + existing tests unaffected

- [ ] **Step 2: Run bats integration tests**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_roadmap_add_feature.bats
```
Expected: All 4 new bats tests pass

- [ ] **Step 3: Run smoke regression**

```bash
cd /workspace/project/rdd-workflow
bats tests/smoke.bats
```
Expected: 7 smoke cases pass

- [ ] **Step 4: If any test fails, debug + fix before continuing**

```bash
cd /workspace/project/rdd-workflow
# Run full regression if individual tests fail
./test.sh --quick
```
Expected: no new failures (existing baseline known failures OK per `KNOWN_FAILURES.txt`)

- [ ] **Step 5: Defer commit**

---

## Task 16: openspec validate (strict mode)

**Files:**
- Run: `openspec validate add-feature-fragment-command --type change --strict`

- [ ] **Step 1: Run strict validation**

```bash
cd /workspace/project/rdd-workflow
openspec validate add-feature-fragment-command --type change --strict
```
Expected: `Change 'add-feature-fragment-command' is valid` (no errors)

- [ ] **Step 2: If validation fails, inspect parsed deltas**

```bash
cd /workspace/project/rdd-workflow
openspec change show add-feature-fragment-command --json --deltas-only
```
Expected: JSON with 5 requirements + 17 scenarios (parsed deltas)

- [ ] **Step 3: Run plan quality check (if SKIP_DESIGN_GATE not set)**

```bash
cd /workspace/project/rdd-workflow
openspec validate add-feature-fragment-command --type change --strict --json 2>&1 | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('summary:', data.get('summary'))
"
```
Expected: `summary.totals.failed == 0`

- [ ] **Step 4: Defer commit**

---

## Task 17: Smoke test end-to-end + cleanup

**Files:**
- Run: `rddf roadmap add-feature smoke-test ...` + cleanup `rm + rebuild AUTO-INDEX`

- [ ] **Step 1: Run smoke test (creates fragment)**

```bash
cd /workspace/project/rdd-workflow
PROJECT_ROOT=$PWD bash skills/roadmap/scripts/roadmap_add_feature.sh smoke-test --phase-refs phase-1 --theme "smoke test"
```
Expected: `✅ created: /workspace/project/rdd-workflow/.rddf/roadmap/features/feat-smoke-test.md`

- [ ] **Step 2: Verify AUTO-INDEX includes smoke-test**

```bash
cd /workspace/project/rdd-workflow
grep -A 5 "### Features" .rddf/roadmap.md
```
Expected: shows `feat-smoke-test` in Features list

- [ ] **Step 3: Verify idempotency**

```bash
cd /workspace/project/rdd-workflow
PROJECT_ROOT=$PWD bash skills/roadmap/scripts/roadmap_add_feature.sh smoke-test --phase-refs phase-1 --theme "smoke test"
```
Expected: exit 1 with `already exists` error (no overwrite)

- [ ] **Step 4: Verify --force regenerates**

```bash
cd /workspace/project/rdd-workflow
PROJECT_ROOT=$PWD bash skills/roadmap/scripts/roadmap_add_feature.sh smoke-test --phase-refs phase-1 --theme "smoke test v2" --force
```
Expected: success, theme updated to "smoke test v2"

- [ ] **Step 5: Cleanup + rebuild AUTO-INDEX**

```bash
cd /workspace/project/rdd-workflow
rm .rddf/roadmap/features/feat-smoke-test.md
PROJECT_ROOT=$PWD bash skills/roadmap/scripts/roadmap_validate_fragments.sh
```
Expected: AUTO-INDEX no longer lists `feat-smoke-test` (rebuilt without it)

- [ ] **Step 6: Final git status check**

```bash
cd /workspace/project/rdd-workflow
git status --short
```
Expected: 3 files modified (`.openspec.yaml` already done; this run modifies `_lib/roadmap_state.py`, `_lib/cli/roadmap_cmd.py`, `_lib/roadmap_state_wrapper.py`, `skills/roadmap/scripts/roadmap_add_feature.sh`, `skills/guide-arch/SKILL.md`, `skills/roadmap/SKILL.md`, `tests/unit/test_roadmap_state.py`, `tests/integration/test_roadmap_add_feature.bats`, `CHANGELOG.md`, `README.md`)

- [ ] **Step 7: Defer commit**

---

## Post-flight

- [ ] **All 17 tasks complete** — verified by `grep -c "^- \[x\]" openspec/changes/add-feature-fragment-command/tasks.md` returning 17

- [ ] **Update tasks.md checkboxes** — replace `- [ ]` with `- [x]` for each completed Task N: in `openspec/changes/add-feature-fragment-command/tasks.md`

- [ ] **Aggregate commit** (per `worktree-archive-workflow` v2.0.5+ rule):

```bash
cd /workspace/project/rdd-workflow
git add -A
git commit -m "feat(roadmap): add-feature-fragment-command CLI primitive

Adds rddf roadmap add-feature <name> operation primitive that creates
.rddf/roadmap/features/feat-<name>.md with valid frontmatter + 3-section
body skeleton and refreshes .rddf/roadmap.md AUTO-INDEX.

Closes the operation gap from add-hierarchical-roadmap-structure (shipped
2026-08-20 scenario 3): users previously had to hand-craft YAML and call
render_fragment_index manually; .rddf/roadmap/features/ stayed empty.

Components:
- _lib/roadmap_state.py::add_feature (Python core, ~95 lines)
- _lib/roadmap_state_wrapper.py (env-var consuming entry point)
- skills/roadmap/scripts/roadmap_add_feature.sh (thin shell wrapper)
- _lib/cli/roadmap_cmd.py dispatch + _help_text extension
- skills/guide-arch/SKILL.md Phase 4 menu + 4-step interaction + ADR-0028 patch
- skills/roadmap/SKILL.md add-feature subcommand section
- 11 tests (7 unit + 4 bats)
- CHANGELOG.md + README.md updates

Validated: openspec validate (strict) passes; all 11 new tests pass;
existing 140 tests unaffected.

Co-authored-by: sisyphus <sisyphus@local>"
```

- [ ] **Verify commit**

```bash
cd /workspace/project/rdd-workflow
git log -1 --oneline
git show --stat HEAD | head -20
```
Expected: 1 commit with all 17 task changes aggregated

---

## Self-Review

After completing all 17 tasks, run these checks:

**1. Spec coverage**: Re-read `openspec/changes/add-feature-fragment-command/specs/roadmap-feature-fragment/spec.md` 5 Requirements + 17 Scenarios. Verify:
- "roadmap add-feature CLI" requirement → Task 1, 8, 9
- "Fragment frontmatter validation" requirement → Task 3, 4
- "Atomic write with compensating rollback" requirement → Task 1 (atomic write + try/except rollback)
- "guide-arch Phase 4 menu integration" requirement → Task 10
- "ADR-0028 role boundary extension" requirement → Task 10 (frontmatter patch)

**2. Placeholder scan**: Search plan for dangerous patterns:
```bash
grep -nE "TBD|TODO|fill in|Similar to Task" .rddf/plans/add-feature-fragment-command.md
```
Fix any matches (TBD in **test code** is OK; only flag TBD in implementation hints).

**3. Type consistency**: `add_feature(name, phase_refs, theme, status, force, project_root)` signature used in:
- Task 1 (definition)
- Task 8 (Python wrapper invocation)
- All 7 unit tests (calls)
Verify parameter order matches.

**4. Branch check**: `git branch --show-current` should be `openspec/add-feature-fragment-command` (lightweight mode).

If any check fails, fix and re-run Task 15 (all tests).

---

## Execution

When ready, this plan is invoked via:

```bash
skill_use("execute")
```

Execute reads this plan and the tasks.md checklist, processes task-by-task, updates `openspec/changes/add-feature-fragment-command/tasks.md` (`- [ ]` → `- [x]`) after each task completion. Final step aggregates a single commit per the post-flight section, then proceeds to archive phase.
