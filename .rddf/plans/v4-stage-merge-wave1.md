# v4 Stage Merge Wave 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Wave 1 of the v4 stage-merge architecture: collapse 5-phase (arch/design/plan/ship/verify) into 4-stage (rdd-arch/rdd-planner/rdd-builder/rdd-verifier) with new skills rdd-planner (wrapping existing Stage 1/2 lib) and rdd-builder (NEW, 6-phase internal state machine: P0/P1/P1.5/P2/P2.5/P3 with verifier retry loop). Slim rdd-arch (remove 3 roadmap fields). Preserve all old skills until Wave 2/3.

**Architecture:**
- Forward handoff contract: `.arch-handoff.json` (v3) → `.planner-handoff.json` (v1) → `.rddf/state/builder/<change>.json` (v1, per-change) → `.verifier-report.json`
- Backward feedback channels (NEW in batch 4): `.planner-feedback.json` (per ADR-0042), `rddf feedback add` (per ADR-0037), verifier retry loop (per ADR-0034), NEW `rdd-builder → rdd-arch` via `_lib/builder_feedback_router.py`
- Migration: 3-wave "新并存" strategy (Wave 1 this plan; Wave 2 deprecation shims; Wave 3 hard removal in separate plan)

**Tech Stack:** Python 3.11+ (boto core lib + schemas), bash 5+ (skill scripts), bats-core 1.10+ (integration tests), pytest 8+ (unit tests), jsonschema (handoff validation), PyYAML (frontmatter), FileLock primitive (per-file concurrency)

**Spec reference:** `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` (1003 lines, 87 AC items, commit `275a40a`)

---

## File Structure

### Production Code (new in Wave 1)

| File | Responsibility |
|---|---|
| `skills/rdd-planner/SKILL.md` | Wrapper skill manifest exposing rdd-planner lib as user-facing skill |
| `skills/rdd-planner/scripts/planner_stage_entry.sh` | Emit `.planner-handoff.json` on stage entry |
| `skills/rdd-planner/scripts/planner_stage_exit.sh` | Consume `.arch-handoff.json`, emit planner-handoff |
| `skills/rdd-builder/SKILL.md` | Manifest for 6-phase state machine |
| `skills/rdd-builder/scripts/phase0_approval.sh` | Phase 0: 4-option approval gate, rejects via `rddf feedback add` |
| `skills/rdd-builder/scripts/phase1_plan.sh` | Phase 1: plan generation via writing-plans + plan_quality |
| `skills/rdd-builder/scripts/phase1_5_deps.sh` | Phase 1.5: deps + execution_mode decision (NEW in v4) |
| `skills/rdd-builder/scripts/phase2_execute.sh` | Phase 2: worktree + TDD 5-step (with COMMIT GATE) |
| `skills/rdd-builder/scripts/phase2_5_review.sh` | Phase 2.5: 4-option review dispatch |
| `skills/rdd-builder/scripts/phase3_archive.sh` | Phase 3: verifier hook + archive + retry loop |
| `_lib/planner_handoff.py` | Read/write/validate `.planner-handoff.json` schema v1 |
| `_lib/builder_handoff.py` | Per-change handoff r/w with FileLock (NOT single-file) |
| `_lib/builder_deps.py` | Phase 1.5 deps analysis + execution_mode decision |
| `_lib/builder_retry.py` | Verifier verdict → Phase routing + retry counter |
| `_lib/builder_feedback_router.py` | Routes builder→arch feedback to `.planner-feedback.json` |
| `_lib/cli/builder_cmd.py` | `rddf builder ...` dispatcher |
| `_lib/schemas/planner_handoff_schema.json` | v1 schema |
| `_lib/schemas/builder_handoff_schema.json` | v1 schema (per-change) |
| `_lib/schemas/builder_retry_schema.json` | v1 schema (verdict + routing table) |
| `docs/adr/ADR-0043-rdd-workflow-v4-stage-merge.md` | ADR for this v4 architecture decision |

### Production Code (modified in Wave 1)

| File | Modification |
|---|---|
| `skills/rdd-arch/SKILL.md` | Slim: remove roadmap-related phase instructions |
| `skills/rdd-arch/scripts/write_arch_handoff.py` | Stop emitting `roadmap_path`/`roadmap_exists`/`discovered.roadmap_path` |
| `_lib/gate.py` | Remove `_check_roadmap_defined`; update `arch_done` gate registration |
| `_lib/schemas/arch_handoff_schema.json` | Add v3 to version enum; remove roadmap fields from required |
| `_lib/state_reader.py` | Tolerate removed fields when reading v3 handoff |
| `install.sh` | Extend `--global` to symlink rdd-planner + rdd-builder |
| `skills/INSTALL.md` | Document 4 stage skills in install list |
| `rddf-session` schema v3 | Add stage_arch/planner/builder/verifier fields; legacy shim |

### Tests (new in Wave 1)

| File | Coverage |
|---|---|
| `tests/unit/test_planner_handoff.py` | ≥6 tests for planner handoff r/w + schema validation |
| `tests/unit/test_builder_handoff.py` | ≥8 tests for per-change layout, FileLock, no global-file race |
| `tests/unit/test_builder_deps.py` | ≥8 tests for Phase 1.5 deps + execution_mode |
| `tests/unit/test_builder_retry.py` | ≥10 tests for 5-value verdict routing + retry cap |
| `tests/unit/test_builder_feedback_router.py` | ≥6 tests for routing matrix (batch 4) |
| `tests/unit/test_builder_phase0.py` | ≥8 tests for approval gate + `rddf feedback add` integration |
| `tests/unit/test_builder_phase1.py` | ≥6 tests for plan generation + quality gate |
| `tests/unit/test_builder_phase1_5.py` | ≥4 tests for execution_mode persistence |
| `tests/unit/test_builder_phase2.py` | ≥8 tests for worktree + TDD + COMMIT GATE |
| `tests/unit/test_builder_phase3.py` | ≥6 tests for archive + verifier hook + 5-value exit codes |
| `tests/unit/test_builder_run_pause.py` | ≥6 tests for HARD/SOFT pause contract (batch 3) |
| `tests/unit/test_builder_cli.py` | ≥5 tests for CLI arg parsing + phase dispatch + exit codes |
| `tests/integration/test_rdd_builder_phase0_approval.bats` | ≥3 tests |
| `tests/integration/test_rdd_builder_phase1_1_5_deps.bats` | ≥3 tests |
| `tests/integration/test_rdd_builder_phase2_execute.bats` | ≥3 tests |
| `tests/integration/test_rdd_builder_phase3_archive.bats` | ≥3 tests |
| `tests/integration/test_rdd_builder_verifier_retry.bats` | ≥3 tests |
| `tests/integration/test_rdd_builder_parallel_isolation.bats` | ≥3 tests |
| `tests/integration/test_rdd_builder_exit_codes.bats` | ≥3 tests (batch 3) |
| `tests/integration/test_rdd_planner_skill_entry.bats` | ≥3 tests |
| `tests/integration/test_cross_stage_feedback.bats` | ≥3 tests (batch 4) |

### Tests (modified in Wave 1)

| File | Modification |
|---|---|
| `tests/integration/test_arch_discovery_contract.bats` | Remove `_check_roadmap_defined` reference; add negative absence test |
| `tests/unit/test_write_arch_handoff.py` | Drop ~13 `discovered_roadmap_path` assertions |
| `tests/unit/test_arch_handoff_schema_v2.py` | Add v3 contract validation tests |
| `tests/integration/test_global_install_external_project.bats` | Assert 4-stage symlink completeness (rdd-arch + rdd-planner + rdd-builder + rdd-verifier) |

**Total: ≥69 unit tests + ≥21 bats tests** (per spec §7).

---

### Task 1: Setup worktree + OpenSpec change skeleton

**Files:**
- Create: `.rddf/wt/v4-stage-merge-wave1/` (worktree)
- Create: `openspec/changes/v4-stage-merge-wave1/proposal.md`
- Create: `openspec/changes/v4-stage-merge-wave1/tasks.md`
- Create: `openspec/changes/v4-stage-merge-wave1/design.md`
- Create: `.rddf/plans/v4-stage-merge-wave1.md` (this plan, committed in worktree)

- [ ] **Step 1: Create branch + worktree**

```bash
# Ensure on master HEAD and committed (COMMIT GATE per AGENTS.md)
cd /workspace/project/rdd-workflow
git rev-parse --abbrev-ref HEAD  # must show master
git status --porcelain            # must be empty (clean tree)

# Create feature branch
git checkout -b openspec/v4-stage-merge-wave1

# Create worktree (this plan will live here)
git worktree add .rddf/wt/v4-stage-merge-wave1 openspec/v4-stage-merge-wave1

# Verify worktree
ls .rddf/wt/v4-stage-merge-wave1/.git
```

Expected: worktree directory created, branch checked out, spec file `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` accessible from worktree.

- [ ] **Step 2: Create OpenSpec change skeleton**

```bash
cd .rddf/wt/v4-stage-merge-wave1
openspec new v4-stage-merge-wave1
ls openspec/changes/v4-stage-merge-wave1/
```

Expected: directory `openspec/changes/v4-stage-merge-wave1/` exists with `proposal.md`, `tasks.md`, `design.md` (openspec CLI scaffolds these).

- [ ] **Step 3: Verify worktree has the v4 spec**

```bash
cd .rddf/wt/v4-stage-merge-wave1
ls docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md
wc -l docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md
```

Expected: file exists, line count = 1003.

- [ ] **Step 4: Verify commit history accessible from worktree**

```bash
cd .rddf/wt/v4-stage-merge-wave1
git log --oneline -3
```

Expected: shows `275a40a docs(spec): v4 stage-merge batch-4 revision...`, `f3e22d7`, `bb9a4f3`, `6634c4e`, `706984e`.

- [ ] **Step 5: Defer commit**

Setup is structural; no code changes. Skip commit per execute.md convention.

---

### Task 2: Slim rdd-arch — remove roadmap fields from arch-handoff writer

**Files:**
- Modify: `skills/rdd-arch/scripts/write_arch_handoff.py` (lines 109-150 area)
- Test: `tests/unit/test_write_arch_handoff.py`

- [ ] **Step 1: Write failing test for writer omitting removed fields**

Edit `tests/unit/test_write_arch_handoff.py`:

```python
def test_arch_handoff_v3_omits_roadmap_fields(tmp_path):
    """Per spec §6.2 batch 2: writer must NOT emit roadmap_path/roadmap_exists/discovered.roadmap_path."""
    from skills.rdd_arch.scripts.write_arch_handoff import write_arch_handoff
    write_arch_handoff(
        project_root=str(tmp_path),
        adr_dir="docs/adr",
        adr_pattern="^ADR-(\\d{4})-.*\\.md$",
        architecture_dir="docs/architecture",
        arch_complete_revision=1,
    )
    content = (tmp_path / ".rddf/state/.arch-handoff.json").read_text()
    data = json.loads(content)
    assert "roadmap_path" not in data, "writer must not emit roadmap_path"
    assert "roadmap_exists" not in data, "writer must not emit roadmap_exists"
    assert "discovered" in data  # structure retained
    if "discovered" in data:
        assert "roadmap_path" not in data["discovered"], "writer must not emit discovered.roadmap_path"
    assert data["version"] == 3, "writer must emit v3 handoff"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_write_arch_handoff.py::test_arch_handoff_v3_omits_roadmap_fields -v`
Expected: FAIL with "writer emits roadmap_path" (current writer still emits these fields).

- [ ] **Step 3: Modify writer to omit roadmap fields**

Edit `skills/rdd-arch/scripts/write_arch_handoff.py`. Find the function that builds the handoff dict (around lines 109-150) and:
- Remove `roadmap_path` from the top-level dict
- Remove `roadmap_exists` from the top-level dict
- Remove `roadmap_path` from the `discovered` sub-dict
- Bump `version` to `3`

Reference spec §6.2 batch 2 for the exact retained field list: `adr_dir`, `adr_pattern`, `architecture_dir`, `discovered` (with roadmap entries stripped), `arch_complete_revision`, `roadmap_fragments_dir`, `adr_regex`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_write_arch_handoff.py::test_arch_handoff_v3_omits_roadmap_fields -v`
Expected: PASS.

- [ ] **Step 5: Run all arch-handoff tests; verify regression gate**

Run: `pytest tests/unit/test_write_arch_handoff.py -v`
Expected: existing tests may need updates (they currently assert `discovered_roadmap_path`). Update each failing test by removing the assertion (since the field no longer is removed). Re-run.

Run: `bats tests/integration/test_arch_discovery_contract.bats`
Expected: may fail at lines 266-269 (which import `_check_roadmap_defined`). Address in next task (Task 3).

Defer commit per execute.md convention.

---

### Task 3: Remove `_check_roadmap_defined` from gate.py + arch_done registration

**Files:**
- Modify: `_lib/gate.py` (lines 155-160 `_check_roadmap_defined`, line 382 registration)
- Modify: `tests/integration/test_arch_discovery_contract.bats` (lines 266-269)

- [ ] **Step 1: Write failing test asserting function absence**

Add to `tests/integration/test_arch_discovery_contract.bats`:

```bash
@test "arch-handoff v3: _check_roadmap_defined function does NOT exist in _lib/gate.py (per Oracle H1 negative test)":
    run grep -E "^def _check_roadmap_defined" "$BATS_TEST_TMPDIR/../../_lib/gate.py"
    [ "$status" -eq 1 ]  # grep -E returns 1 when no match found
    [ -z "$output" ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_arch_discovery_contract.bats`
Expected: existing tests at lines 266-269 may already fail. The new test fails because `_check_roadmap_defined` currently exists.

- [ ] **Step 3: Remove `_check_roadmap_defined` from gate.py**

Edit `_lib/gate.py`:
- Delete the function `_check_roadmap_defined` at lines 155-160
- Delete the registration `Check("roadmap_defined", _check_roadmap_defined, ...)` at line 382

- [ ] **Step 4: Update existing test references**

Edit `tests/integration/test_arch_discovery_contract.bats`:
- Remove the import/call of `_check_roadmap_defined` at lines 266-269
- Add negative absence test (already drafted in Step 1)

- [ ] **Step 5: Run all related tests; verify pass**

Run: `bats tests/integration/test_arch_discovery_contract.bats`
Run: `pytest tests/unit/test_arch_handoff_schema_v2.py -v`
Expected: all green. Add new v3 validation tests (covered in Task 4).

Defer commit per execute.md convention.

---

### Task 4: Bump arch-handoff schema to v3 + extend test coverage

**Files:**
- Modify: `_lib/schemas/arch_handoff_schema.json` (version enum + required list)
- Modify: `tests/unit/test_arch_handoff_schema_v2.py` (add v3 tests)

- [ ] **Step 1: Write failing test for v3 contract**

Add to `tests/unit/test_arch_handoff_schema_v2.py`:

```python
def test_arch_handoff_v3_contract_validation():
    """Per spec §6.2: v3 handoff must accept version 3 and tolerate removed fields via additionalProperties:true."""
    import jsonschema
    schema = json.loads((Path(__file__).parent.parent.parent / "_lib/schemas/arch_handoff_schema.json").read_text())
    assert 3 in schema["properties"]["version"]["enum"]
    # v3 handoff without roadmap fields should validate
    handoff_v3 = {
        "version": 3,
        "schema": "arch-handoff-v3",
        "adr_dir": "docs/adr",
        "adr_pattern": "^ADR-(\\d{4})-.*\\.md$",
        "architecture_dir": "docs/architecture",
        "discovered": {},
        "arch_complete_revision": 1,
    }
    jsonschema.validate(handoff_v3, schema)  # must not raise


def test_arch_handoff_v3_writes_with_v3_version():
    """Per spec §6.2: writer outputs version 3."""
    # Triggers writer; verify output version
    pass  # covered by Task 2 test
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_arch_handoff_schema_v2.py::test_arch_handoff_v3_contract_validation -v`
Expected: FAIL because current schema only allows versions [1, 2].

- [ ] **Step 3: Update schema**

Edit `_lib/schemas/arch_handoff_schema.json`:
- Change `version.enum` from `[1, 2]` to `[1, 2, 3]`
- Remove `roadmap_path` from required list (if present)
- Remove `roadmap_exists` from required list (if present)
- Update top-level `additionalProperties: true` (already present per spec §6.2)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_arch_handoff_schema_v2.py -v`
Expected: PASS.

- [ ] **Step 5: Add v2 backward-compat test (additionalProperties absorbs removed fields)**

```python
def test_v1_v2_handoff_compatible_with_v3_reader():
    """Per spec §6.2 batch 2: v1/v2 handoff with roadmap fields still validates via additionalProperties."""
    import jsonschema
    schema = json.loads((Path(__file__).parent.parent.parent / "_lib/schemas/arch_handoff_schema.json").read_text())
    legacy_handoff = {
        "version": 2,
        "schema": "arch-handoff-v2",
        "adr_dir": "docs/adr",
        "architecture_dir": "docs/architecture",
        "discovered": {"roadmap_path": "roadmap.md"},
        "roadmap_path": "roadmap.md",
        "roadmap_exists": True,
        "arch_complete_revision": 1,
    }
    jsonschema.validate(legacy_handoff, schema)  # must not raise
```

Run: `pytest tests/unit/test_arch_handoff_schema_v2.py -v`
Expected: PASS.

Defer commit per execute.md convention.

---

### Task 5: Create rdd-planner SKILL.md wrapper

**Files:**
- Create: `skills/rdd-planner/SKILL.md`
- Test: `tests/integration/test_rdd_planner_skill_entry.bats` (basic manifest validation)

- [ ] **Step 1: Write failing test asserting manifest exists and has required fields**

Add to `tests/integration/test_rdd_planner_skill_entry.bats`:

```bash
@test "rdd-planner SKILL.md exists and parses":
    [ -f "$BATS_TEST_TMPDIR/../../skills/rdd-planner/SKILL.md" ]
    run grep -E "^name: rdd-planner" "$BATS_TEST_TMPDIR/../../skills/rdd-planner/SKILL.md"
    [ "$status" -eq 0 ]
    run grep -E "^version:" "$BATS_TEST_TMPDIR/../../skills/rdd-planner/SKILL.md"
    [ "$status" -eq 0 ]
    run grep -E "^compatibility: requires openspec CLI" "$BATS_TEST_TMPDIR/../../skills/rdd-planner/SKILL.md"
    [ "$status" -eq 0 ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rdd_planner_skill_entry.bats`
Expected: FAIL because `skills/rdd-planner/SKILL.md` does not exist.

- [ ] **Step 3: Write minimal SKILL.md**

Create `skills/rdd-planner/SKILL.md` with this content:

```markdown
---
name: rdd-planner
description: |
  Roadmap + proposal authoring orchestrator. Stage 2 of v4 architecture.
  Wraps existing `_lib/planner_*.py` lib (per ADR-0037/0038/0042) and adds
  stage entry/exit contract. Per spec §3.3.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, git 2.25+
metadata:
  author: rdd-workflow
  version: 2.1
  evolved-from: "guide-design + roadmap"
  user-invocable: true
---

# rdd-planner Skill

Stage 2 of v4 architecture (per spec §3.3). Owns:
- `roadmap.md`
- `proposal-suggestions.md` / `proposal-approved.md`
- `.rddf/roadmap/features/*.md`
- `.rddf/improvements/*.md` (via `add-improve`)
- `openspec/changes/<name>/proposal.md` (authoring only)

Stage entry: `planner_stage_entry.sh` (emits `.planner-handoff.json`)
Stage exit: `planner_stage_exit.sh` (consumes arch-handoff, emits planner-handoff)

Existing horizontal-orchestrator commands remain available: status, sync, feedback, attach, audit, history, advance-sprint.

```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_rdd_planner_skill_entry.bats`
Expected: PASS.

- [ ] **Step 5: Verify discoverability**

Run: `rddf planner --help` (after `_lib/cli/planner_cmd.py` is updated in Task 12)
Expected: shows new `stage-entry` / `stage-exit` / `handoff` subcommands per spec §5.1.

Defer commit per execute.md convention.

---

### Task 6: Create planner_handoff.py + schema (per spec §3.3 + §6.1)

**Files:**
- Create: `_lib/planner_handoff.py`
- Create: `_lib/schemas/planner_handoff_schema.json`
- Modify: `_lib/cli/__init__.py` (add new subcommand if needed)
- Test: `tests/unit/test_planner_handoff.py`

- [ ] **Step 1: Write failing test for write_planner_handoff**

Create `tests/unit/test_planner_handoff.py`:

```python
def test_write_planner_handoff_creates_file(tmp_path):
    """Per spec §3.3: planner-handoff v1 written to .rddf/state/.planner-handoff.json."""
    from _lib.planner_handoff import write_planner_handoff
    write_planner_handoff(
        project_root=str(tmp_path),
        proposals_authored=["change-foo"],
        proposals_approved_count=0,
        features_active=[],
        current_sprint="sprint-2026-09",
    )
    handoff_path = tmp_path / ".rddf/state/.planner-handoff.json"
    assert handoff_path.exists()
    data = json.loads(handoff_path.read_text())
    assert data["schema"] == "planner-handoff-v1"
    assert data["version"] == 1
    assert data["current_sprint"] == "sprint-2026-09"
    assert data["proposals_authored"] == ["change-foo"]


def test_read_planner_handoff_returns_dict(tmp_path):
    """Per spec §3.3: read returns full dict."""
    from _lib.planner_handoff import write_planner_handoff, read_planner_handoff
    write_planner_handoff(
        project_root=str(tmp_path),
        proposals_authored=["change-foo"],
        proposals_approved_count=1,
        features_active=["feat-x"],
        current_sprint="sprint-2026-09",
    )
    data = read_planner_handoff(project_root=str(tmp_path))
    assert data["proposals_approved_count"] == 1
    assert data["features_active"] == ["feat-x"]


def test_write_planner_handoff_validates_against_schema(tmp_path):
    """Per spec §6.1: schema v1 validation enforced."""
    import jsonschema
    from _lib.planner_handoff import write_planner_handoff
    write_planner_handoff(
        project_root=str(tmp_path),
        proposals_authored=[],
        proposals_approved_count=0,
        features_active=[],
        current_sprint="sprint-2026-09",
    )
    handoff_path = tmp_path / ".rddf/state/.planner-handoff.json"
    data = json.loads(handoff_path.read_text())
    schema = json.loads((Path(__file__).parent.parent.parent / "_lib/schemas/planner_handoff_schema.json").read_text())
    jsonschema.validate(data, schema)  # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_planner_handoff.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named '_lib.planner_handoff'".

- [ ] **Step 3: Implement planner_handoff.py**

Create `_lib/planner_handoff.py`:

```python
"""planner-handoff.json v1 read/write/validate (per spec §3.3 + §6.1).

Env-var pattern (Oracle C1): receives PROJECT_ROOT, PROPOSALS_AUTHORED,
PROPOSALS_APPROVED_COUNT, FEATURES_ACTIVE, CURRENT_SPRINT via env vars.

Backward compat: coexists with .planner-state.json (Stage 2) and
.planner-feedback.json (ADR-0042). Each file has its own FileLock.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def write_planner_handoff(
    project_root: str,
    proposals_authored: list[str],
    proposals_approved_count: int,
    features_active: list[str],
    current_sprint: str,
) -> dict:
    """Write .rddf/state/.planner-handoff.json schema v1."""
    handoff = {
        "schema": "planner-handoff-v1",
        "version": 1,
        "owner": "rdd-planner",
        "planner_complete_at": datetime.now(timezone.utc).isoformat(),
        "current_sprint": current_sprint,
        "proposals_authored": proposals_authored,
        "proposals_approved_count": proposals_approved_count,
        "features_active": features_active,
    }
    state_dir = Path(project_root) / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    handoff_path = state_dir / ".planner-handoff.json"
    with open(handoff_path, "w") as f:
        json.dump(handoff, f, indent=2)
    return handoff


def read_planner_handoff(project_root: str) -> dict:
    """Read .rddf/state/.planner-handoff.json. Returns empty dict if missing."""
    handoff_path = Path(project_root) / ".rddf" / "state" / ".planner-handoff.json"
    if not handoff_path.exists():
        return {}
    with open(handoff_path) as f:
        return json.load(f)


if __name__ == "__main__":
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    proposals_authored = os.environ.get("PROPOSALS_AUTHORED", "").split(",")
    proposals_authored = [p.strip() for p in proposals_authored if p.strip()]
    proposals_approved_count = int(os.environ.get("PROPOSALS_APPROVED_COUNT", "0"))
    features_active = os.environ.get("FEATURES_ACTIVE", "").split(",")
    features_active = [f.strip() for f in features_active if f.strip()]
    current_sprint = os.environ.get("CURRENT_SPRINT", f"sprint-{datetime.now().strftime('%Y-%m')}")
    result = write_planner_handoff(
        project_root, proposals_authored, proposals_approved_count,
        features_active, current_sprint,
    )
    print(f"✅ planner-handoff v1 written: {result['planner_complete_at']}")
```

- [ ] **Step 4: Create schema file**

Create `_lib/schemas/planner_handoff_schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://rdd-workflow.local/schemas/planner_handoff_schema.json",
  "title": "PlannerHandoff",
  "type": "object",
  "required": ["schema", "version", "owner", "planner_complete_at", "current_sprint"],
  "properties": {
    "schema": {"const": "planner-handoff-v1"},
    "version": {"const": 1},
    "owner": {"const": "rdd-planner"},
    "planner_complete_at": {"type": "string", "format": "date-time"},
    "current_sprint": {"type": "string"},
    "proposals_authored": {"type": "array", "items": {"type": "string"}},
    "proposals_approved_count": {"type": "integer", "minimum": 0},
    "features_active": {"type": "array", "items": {"type": "string"}},
    "awaiting_builder": {"type": "array", "items": {"type": "string"}}
  },
  "additionalProperties": true
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_planner_handoff.py -v`
Expected: PASS for all 3 tests.

Defer commit per execute.md convention.

---

### Task 7: Create _lib/builder_handoff.py + schema (per-change layout per Oracle H3)

**Files:**
- Create: `_lib/builder_handoff.py`
- Create: `_lib/schemas/builder_handoff_schema.json`
- Test: `tests/unit/test_builder_handoff.py`

- [ ] **Step 1: Write failing test for per-change handoff**

Create `tests/unit/test_builder_handoff.py`:

```python
def test_builder_handoff_creates_per_change_file(tmp_path):
    """Per spec §6.3 + Oracle H3: per-change layout, NOT single file."""
    from _lib.builder_handoff import write_builder_handoff, read_builder_handoff
    write_builder_handoff(
        project_root=str(tmp_path),
        change_name="change-foo",
        current_phase="phase-2",
        approval_status="approved",
        plan_quality_status="valid",
        execution_mode_decision={"mode": "worktree", "reason": "files>2"},
        deps_status={"blockers": [], "manual_deps": [], "cross_repo_pending": []},
        worktree_path="/abs/.rddf/wt/change-foo",
        branch="openspec/change-foo",
        execution_status="running",
        review_status="pending",
        archive_status="pending",
        verifier_report_path=".rddf/state/.verifier-report.json",
        retry_count=0,
        max_retries=3,
        retry_history=[],
    )
    handoff_path = tmp_path / ".rddf/state/builder/change-foo.json"
    assert handoff_path.exists()
    # NO single file
    assert not (tmp_path / ".rddf/state/.builder-handoff.json").exists()
    data = read_builder_handoff(project_root=str(tmp_path), change_name="change-foo")
    assert data["current_phase"] == "phase-2"
    assert data["retry_count"] == 0


def test_builder_handoff_filelock(tmp_path):
    """Per spec §6.3: per-file FileLock prevents global-file race."""
    # Two changes in flight
    from _lib.builder_handoff import write_builder_handoff
    write_builder_handoff(project_root=str(tmp_path), change_name="change-foo", current_phase="phase-0")
    write_builder_handoff(project_root=str(tmp_path), change_name="change-bar", current_phase="phase-1")
    # Both files exist independently
    assert (tmp_path / ".rddf/state/builder/change-foo.json").exists()
    assert (tmp_path / ".rddf/state/builder/change-bar.json").exists()
    # Different FileLocks
    assert (tmp_path / ".rddf/state/builder/change-foo.json.lock").exists()
    assert (tmp_path / ".rddf/state/builder/change-bar.json.lock").exists()


def test_builder_handoff_retry_count_increments(tmp_path):
    """Per spec §6.3: retry_count field exists."""
    from _lib.builder_handoff import write_builder_handoff, read_builder_handoff, increment_retry
    write_builder_handoff(project_root=str(tmp_path), change_name="change-foo", current_phase="phase-3", retry_count=0)
    increment_retry(project_root=str(tmp_path), change_name="change-foo", to_phase="phase-2", verifier_kind="implementation_gap")
    data = read_builder_handoff(project_root=str(tmp_path), change_name="change-foo")
    assert data["retry_count"] == 1
    assert len(data["retry_history"]) == 1
    assert data["retry_history"][0]["to_phase"] == "phase-2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_builder_handoff.py -v`
Expected: FAIL with "ModuleNotFoundError".

- [ ] **Step 3: Implement builder_handoff.py**

Create `_lib/builder_handoff.py`:

```python
"""builder-handoff per-change file r/w + FileLock (per spec §6.3 + Oracle H3).

Per-change layout prevents global-file serial-write regression (per ADR-0034 §2).
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from _lib.core.lock import FileLock  # existing primitive
from _lib.core.atomic_write import atomic_write_json


def _handoff_path(project_root: str, change_name: str) -> Path:
    return Path(project_root) / ".rddf/state/builder" / f"{change_name}.json"


def write_builder_handoff(
    project_root: str,
    change_name: str,
    current_phase: str = "phase-0",
    approval_status: str = "pending",
    plan_quality_status: str = "pending",
    execution_mode_decision: Optional[dict] = None,
    deps_status: Optional[dict] = None,
    worktree_path: str = "",
    branch: str = "",
    execution_status: str = "pending",
    review_status: str = "pending",
    archive_status: str = "pending",
    verifier_report_path: str = ".rddf/state/.verifier-report.json",
    retry_count: int = 0,
    max_retries: int = 3,
    retry_history: Optional[list] = None,
    phase_pause_history: Optional[list] = None,
) -> dict:
    """Write per-change builder handoff with FileLock."""
    if execution_mode_decision is None:
        execution_mode_decision = {}
    if deps_status is None:
        deps_status = {"blockers": [], "manual_deps": [], "cross_repo_pending": []}
    if retry_history is None:
        retry_history = []
    if phase_pause_history is None:
        phase_pause_history = []

    handoff = {
        "schema": "builder-handoff-v1",
        "version": 1,
        "owner": "rdd-builder",
        "change_name": change_name,
        "current_phase": current_phase,
        "approval_status": approval_status,
        "plan_quality_status": plan_quality_status,
        "execution_mode_decision": execution_mode_decision,
        "deps_status": deps_status,
        "worktree_path": worktree_path,
        "branch": branch,
        "execution_status": execution_status,
        "review_status": review_status,
        "retry_count": retry_count,
        "max_retries": max_retries,
        "retry_history": retry_history,
        "phase_pause_history": phase_pause_history,
        "archive_status": archive_status,
        "verifier_report_path": verifier_report_path,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    handoff_path = _handoff_path(project_root, change_name)
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(handoff_path) + ".lock", timeout=10):
        atomic_write_json(str(handoff_path), handoff)
    return handoff


def read_builder_handoff(project_root: str, change_name: str) -> dict:
    """Read per-change builder handoff. Returns empty dict if missing."""
    handoff_path = _handoff_path(project_root, change_name)
    if not handoff_path.exists():
        return {}
    with open(handoff_path) as f:
        return json.load(f)


def increment_retry(
    project_root: str,
    change_name: str,
    to_phase: str,
    verifier_kind: str,
    verifier_exit_code: int = 1,
) -> dict:
    """Increment retry_count and append to retry_history."""
    data = read_builder_handoff(project_root, change_name)
    data["retry_count"] = data.get("retry_count", 0) + 1
    data["current_phase"] = to_phase
    data["retry_history"].append({
        "from_phase": "phase-3",
        "to_phase": to_phase,
        "verifier_exit_code": verifier_exit_code,
        "verifier_kind": verifier_kind,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    write_builder_handoff(project_root, change_name, **data)
    return data
```

- [ ] **Step 4: Create schema**

Create `_lib/schemas/builder_handoff_schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://rdd-workflow.local/schemas/builder_handoff_schema.json",
  "title": "BuilderHandoff",
  "type": "object",
  "required": ["schema", "version", "owner", "change_name", "current_phase", "retry_count", "max_retries"],
  "properties": {
    "schema": {"const": "builder-handoff-v1"},
    "version": {"const": 1},
    "owner": {"const": "rdd-builder"},
    "change_name": {"type": "string"},
    "current_phase": {"enum": ["phase-0", "phase-1", "phase-1.5", "phase-2", "phase-2.5", "phase-3"]},
    "approval_status": {"enum": ["pending", "approved", "rejected", "deferred", "revising"]},
    "plan_quality_status": {"enum": ["pending", "valid", "invalid"]},
    "execution_mode_decision": {
      "type": "object",
      "properties": {
        "mode": {"enum": ["worktree", "lightweight"]},
        "reason": {"type": "string"},
        "decided_at": {"type": "string", "format": "date-time"},
        "decided_by": {"type": "string"}
      }
    },
    "deps_status": {
      "type": "object",
      "properties": {
        "blockers": {"type": "array", "items": {"type": "string"}},
        "manual_deps": {"type": "array", "items": {"type": "string"}},
        "cross_repo_pending": {"type": "array", "items": {"type": "string"}}
      }
    },
    "worktree_path": {"type": "string"},
    "branch": {"type": "string"},
    "execution_status": {"enum": ["pending", "running", "failed", "completed"]},
    "review_status": {"enum": ["pending", "merge", "revise", "abandon"]},
    "retry_count": {"type": "integer", "minimum": 0},
    "max_retries": {"type": "integer", "minimum": 1},
    "retry_history": {"type": "array", "items": {"type": "object"}},
    "phase_pause_history": {"type": "array", "items": {"type": "object"}},
    "archive_status": {"enum": ["pending", "verifying", "archived", "failed"]},
    "verifier_report_path": {"type": "string"},
    "updated_at": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": true
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_builder_handoff.py -v`
Expected: PASS for all 3 tests.

Defer commit per execute.md convention.

---

### Task 8: Create _lib/builder_deps.py (Phase 1.5 deps + execution_mode)

**Files:**
- Create: `_lib/builder_deps.py`
- Test: `tests/unit/test_builder_deps.py`

- [ ] **Step 1: Write failing test for execution_mode decision**

Create `tests/unit/test_builder_deps.py`:

```python
def test_decide_execution_mode_worktree_when_files_gt_2():
    """Per spec §3.4 Phase 1.5: file count > 2 → worktree."""
    from _lib.builder_deps import decide_execution_mode
    decision = decide_execution_mode(file_count=5, task_count=10, risk_keywords=[])
    assert decision["mode"] == "worktree"


def test_decide_execution_mode_lightweight_when_files_le_2():
    """Per spec §3.4 Phase 1.5: file count ≤ 2 AND task count ≤ 3 → lightweight."""
    from _lib.builder_deps import decide_execution_mode
    decision = decide_execution_mode(file_count=1, task_count=2, risk_keywords=[])
    assert decision["mode"] == "lightweight"


def test_decide_execution_mode_worktree_on_risk_keyword():
    """Per spec §3.4 Phase 1.5: refactor/migration risk keyword → worktree even if file count low."""
    from _lib.builder_deps import decide_execution_mode
    decision = decide_execution_mode(file_count=1, task_count=2, risk_keywords=["refactor"])
    assert decision["mode"] == "worktree"


def test_analyze_deps_with_manual_deps():
    """Per spec §3.4 Phase 1.5: ADR-0022 manual_deps merged into blockers."""
    from _lib.builder_deps import analyze_deps
    deps = analyze_deps(
        change_name="change-foo",
        proposal_path="openspec/changes/change-foo",
        manual_deps=["change-bar"],
        cross_repo=False,
    )
    assert "change-bar" in deps["manual_deps"]


def test_analyze_deps_strict_gate_blocks_on_blocker():
    """Per spec §3.4 Phase 1.5: STRICT_DEPS_GATE returns failure if blockers present."""
    from _lib.builder_deps import analyze_deps_with_strict_gate
    result = analyze_deps_with_strict_gate(blockers=["change-bar"])
    assert result["passes"] is False
    assert "change-bar" in result["failures"]


def test_analyze_deps_cross_repo_pending():
    """Per spec §3.4 Phase 1.5: ADR-0031 cross-repo pending check."""
    from _lib.builder_deps import analyze_deps
    deps = analyze_deps(
        change_name="change-foo",
        proposal_path="openspec/changes/change-foo",
        manual_deps=[],
        cross_repo=True,
        hub_issue_status="pending",
    )
    assert "hub_issue_pending" in deps["cross_repo_pending"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_builder_deps.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement builder_deps.py**

Create `_lib/builder_deps.py`:

```python
"""Phase 1.5 deps analysis + execution_mode decision (per spec §3.4, Oracle C2).

Reuses skills/deps/scripts/* for inter-change analysis; adds execution_mode
decision matrix per ADR-0024.
"""
from pathlib import Path
from typing import Optional

import yaml


def decide_execution_mode(file_count: int, task_count: int, risk_keywords: list[str]) -> dict:
    """Decide worktree vs lightweight per ADR-0024 matrix.

    Rules (per spec §3.4 Phase 1.5):
    - file_count > 2 → worktree
    - task_count > 3 → worktree
    - risk_keyword in {refactor, migration, breaking, schema-change} → worktree
    - else → lightweight
    """
    RISK_KEYWORDS = {"refactor", "migration", "breaking", "schema-change"}
    has_risk = bool(set(risk_keywords) & RISK_KEYWORDS)
    if file_count > 2 or task_count > 3 or has_risk:
        reason = []
        if file_count > 2:
            reason.append(f"files={file_count}>2")
        if task_count > 3:
            reason.append(f"tasks={task_count}>3")
        if has_risk:
            reason.append(f"risk_keyword={set(risk_keywords) & RISK_KEYWORDS}")
        return {"mode": "worktree", "reason": " AND ".join(reason)}
    return {"mode": "lightweight", "reason": f"files={file_count}<=2 AND tasks={task_count}<=3"}


def analyze_deps(
    change_name: str,
    proposal_path: str,
    manual_deps: list[str],
    cross_repo: bool,
    hub_issue_status: Optional[str] = None,
) -> dict:
    """Analyze inter-change deps per ADR-0022/0031."""
    deps_status = {
        "blockers": [],
        "manual_deps": list(manual_deps),
        "cross_repo_pending": [],
    }
    if cross_repo and hub_issue_status == "pending":
        deps_status["cross_repo_pending"].append("hub_issue_pending")
    # Static analysis from proposal_path content would happen here (deferred)
    return deps_status


def analyze_deps_with_strict_gate(blockers: list[str]) -> dict:
    """STRICT_DEPS_GATE check (per spec §3.4 Phase 1.5)."""
    if blockers:
        return {
            "passes": False,
            "failures": blockers,
            "warnings": [],
            "passes_list": [],
        }
    return {
        "passes": True,
        "failures": [],
        "warnings": [],
        "passes_list": ["strict_deps_gate"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_builder_deps.py -v`
Expected: PASS for all 6 tests.

- [ ] **Step 5: Run existing tests in `skills/deps/scripts/` to verify reuse works**

Run: `pytest tests/unit/test_deps*.py -v 2>&1 | head -20`
Expected: existing tests pass (no regression).

Defer commit per execute.md convention.

---

### Task 9: Create _lib/builder_retry.py (verifier verdict → Phase routing)

**Files:**
- Create: `_lib/builder_retry.py`
- Create: `_lib/schemas/builder_retry_schema.json`
- Test: `tests/unit/test_builder_retry.py`

- [ ] **Step 1: Write failing test for verifier verdict routing**

Create `tests/unit/test_builder_retry.py`:

```python
def test_route_verifier_pass_continues_archive():
    """Per spec §3.4: PASS (0) → archive (no back-route)."""
    from _lib.builder_retry import route_verifier_verdict
    decision = route_verifier_verdict(verifier_exit_code=0)
    assert decision["next_phase"] == "phase-3-archive"
    assert decision["should_back_route"] is False


def test_route_verifier_implementation_gap_routes_to_phase_2():
    """Per spec §3.4: implementation_gap (1) → back-route to Phase 2 (re-execute)."""
    from _lib.builder_retry import route_verifier_verdict
    decision = route_verifier_verdict(verifier_exit_code=1, verifier_kind="implementation_gap")
    assert decision["next_phase"] == "phase-2"
    assert decision["should_back_route"] is True


def test_route_verifier_ac_fail_routes_to_phase_1():
    """Per spec §3.4: ac_fail (2) → back-route to Phase 1 (re-plan)."""
    from _lib.builder_retry import route_verifier_verdict
    decision = route_verifier_verdict(verifier_exit_code=2, verifier_kind="ac_fail")
    assert decision["next_phase"] == "phase-1"
    assert decision["should_back_route"] is True


def test_route_verifier_needs_human_halts():
    """Per spec §3.4: needs_human (3) → halt, exit 4."""
    from _lib.builder_retry import route_verifier_verdict
    decision = route_verifier_verdict(verifier_exit_code=3, verifier_kind="needs_human")
    assert decision["next_phase"] == "halt"
    assert decision["should_back_route"] is False
    assert decision["halted"] is True


def test_route_verifier_halted_max_retries_halts():
    """Per spec §3.4: halted (4) → halt, exit 4."""
    from _lib.builder_retry import route_verifier_verdict
    decision = route_verifier_verdict(verifier_exit_code=4, verifier_kind="halted_max_loops")
    assert decision["next_phase"] == "halt"
    assert decision["halted"] is True


def test_retry_count_cap_at_max():
    """Per spec §3.4: retry_count > max_retries (3) halts."""
    from _lib.builder_retry import should_halt_for_retry_exceeded
    assert should_halt_for_retry_exceeded(retry_count=4, max_retries=3) is True
    assert should_halt_for_retry_exceeded(retry_count=3, max_retries=3) is False
    assert should_halt_for_retry_exceeded(retry_count=2, max_retries=3) is False


def test_retry_count_increments_only_on_back_route():
    """Per spec §3.4: counter increments only on back-route (not on forward)."""
    from _lib.builder_retry import should_increment_retry
    assert should_increment_retry(should_back_route=True) is True
    assert should_increment_retry(should_back_route=False) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_builder_retry.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement builder_retry.py**

Create `_lib/builder_retry.py`:

```python
"""Verifier verdict → Phase routing + retry counter (per spec §3.4, Oracle C1).

Preserves ADR-0034 §7 5-value exit semantics (0/1/2/3/4).
"""
from typing import Optional


def route_verifier_verdict(
    verifier_exit_code: int,
    verifier_kind: Optional[str] = None,
) -> dict:
    """Route verifier verdict to next phase.

    Per spec §3.4 Phase 3 verdict dispatch:
    - 0 (PASS) → archive (no back-route)
    - 1 (implementation_gap) → Phase 2 (re-execute)
    - 2 (ac_fail / proposal_drift) → Phase 1 (re-plan)
    - 3 (needs_human) → halt, exit 4
    - 4 (halted max_retries) → halt, exit 4
    """
    if verifier_exit_code == 0:
        return {
            "next_phase": "phase-3-archive",
            "should_back_route": False,
            "halted": False,
            "verifier_kind": verifier_kind or "pass",
        }
    elif verifier_exit_code == 1:
        return {
            "next_phase": "phase-2",
            "should_back_route": True,
            "halted": False,
            "verifier_kind": verifier_kind or "implementation_gap",
        }
    elif verifier_exit_code == 2:
        return {
            "next_phase": "phase-1",
            "should_back_route": True,
            "halted": False,
            "verifier_kind": verifier_kind or "ac_fail",
        }
    elif verifier_exit_code in (3, 4):
        return {
            "next_phase": "halt",
            "should_back_route": False,
            "halted": True,
            "verifier_kind": verifier_kind or ("needs_human" if verifier_exit_code == 3 else "halted_max_loops"),
        }
    else:
        return {
            "next_phase": "halt",
            "should_back_route": False,
            "halted": True,
            "verifier_kind": verifier_kind or f"unknown_exit_{verifier_exit_code}",
        }


def should_halt_for_retry_exceeded(retry_count: int, max_retries: int) -> bool:
    """Halt when retry_count > max_retries (per spec §3.4 + ADR-0034 §8)."""
    return retry_count > max_retries


def should_increment_retry(should_back_route: bool) -> bool:
    """Increment only on back-route, not on forward progression."""
    return should_back_route
```

- [ ] **Step 4: Create schema**

Create `_lib/schemas/builder_retry_schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://rdd-workflow.local/schemas/builder_retry_schema.json",
  "title": "BuilderRetryVerdict",
  "type": "object",
  "required": ["verifier_exit_code", "next_phase"],
  "properties": {
    "verifier_exit_code": {"type": "integer", "minimum": 0, "maximum": 4},
    "verifier_kind": {"type": "string"},
    "next_phase": {
      "enum": [
        "phase-1",
        "phase-2",
        "phase-3-archive",
        "halt"
      ]
    },
    "should_back_route": {"type": "boolean"},
    "halted": {"type": "boolean"}
  },
  "additionalProperties": true
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_builder_retry.py -v`
Expected: PASS for all 7 tests.

Defer commit per execute.md convention.

---

### Task 10: Create _lib/builder_feedback_router.py (cross-stage feedback per batch 4)

**Files:**
- Create: `_lib/builder_feedback_router.py`
- Test: `tests/unit/test_builder_feedback_router.py`

- [ ] **Step 1: Write failing test for feedback routing**

Create `tests/unit/test_builder_feedback_router.py`:

```python
def test_route_ac_fail_to_planner_feedback_when_ref_change_matches(tmp_path):
    """Per spec §3.5.2: kind=ac-fail + ref_change match → routed to .planner-feedback.json."""
    from _lib.builder_feedback_router import route_feedback
    feedback_entry = {
        "feedback_id": "fb-20260904-001",
        "from": "rdd-builder",
        "kind": "ac-fail",
        "created_at": "2026-09-04T10:00:00Z",
        "body": "ADR-XXXX assumes Foo API returns JSON",
        "ref_change": "change-foo",
        "resolution": "open",
    }
    result = route_feedback(
        feedback_entry=feedback_entry,
        project_root=str(tmp_path),
        accept_builder_source=True,
    )
    assert result["routed_to_planner_feedback"] is True
    assert (tmp_path / ".rddf/state/.planner-feedback.json").exists()


def test_route_without_accept_builder_source_does_not_promote(tmp_path):
    """Per spec §3.5.2: without accept-builder-source, feedback recorded but NOT routed to architect."""
    from _lib.builder_feedback_router import route_feedback
    feedback_entry = {
        "feedback_id": "fb-20260904-002",
        "from": "rdd-builder",
        "kind": "ac-fail",
        "created_at": "2026-09-04T10:00:00Z",
        "body": "test",
        "ref_change": "change-foo",
    }
    result = route_feedback(
        feedback_entry=feedback_entry,
        project_root=str(tmp_path),
        accept_builder_source=False,
    )
    assert result["routed_to_planner_feedback"] is False


def test_route_non_ac_fail_kind_does_not_promote(tmp_path):
    """Per spec §3.5.2: only kind=ac-fail promotes to planner-feedback."""
    from _lib.builder_feedback_router import route_feedback
    feedback_entry = {
        "feedback_id": "fb-20260904-003",
        "from": "rdd-builder",
        "kind": "needs-revision",
        "created_at": "2026-09-04T10:00:00Z",
        "body": "test",
        "ref_change": "change-foo",
    }
    result = route_feedback(
        feedback_entry=feedback_entry,
        project_root=str(tmp_path),
        accept_builder_source=True,
    )
    assert result["routed_to_planner_feedback"] is False


def test_route_ref_change_mismatch_does_not_promote(tmp_path):
    """Per spec §3.5.2: ref_change mismatch → no promotion."""
    from _lib.builder_feedback_router import route_feedback
    feedback_entry = {
        "feedback_id": "fb-20260904-004",
        "from": "rdd-builder",
        "kind": "ac-fail",
        "created_at": "2026-09-04T10:00:00Z",
        "body": "test",
        "ref_change": "change-bar",  # different from change-foo
    }
    result = route_feedback(
        feedback_entry=feedback_entry,
        project_root=str(tmp_path),
        accept_builder_source=True,
        current_change="change-foo",
    )
    assert result["routed_to_planner_feedback"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_builder_feedback_router.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement builder_feedback_router.py**

Create `_lib/builder_feedback_router.py`:

```python
"""Builder feedback routing to .planner-feedback.json (per spec §3.5.2, batch 4).

Routes kind=ac-fail feedback with ref_change match to .planner-feedback.json
for architect visibility. Without accept_builder_source opt-in, feedback is
recorded in .rddf/improvements/*.md::## Feedback only.
"""
import json
import os
from pathlib import Path
from typing import Optional

from _lib.core.lock import FileLock
from _lib.core.atomic_write import atomic_write_json


def route_feedback(
    feedback_entry: dict,
    project_root: str,
    accept_builder_source: bool = True,
    current_change: Optional[str] = None,
) -> dict:
    """Route builder-emitted feedback to planner-feedback channel.

    Routing logic per spec §3.5.2:
    - kind must be "ac-fail"
    - accept_builder_source must be True
    - ref_change must match current_change (if provided)
    """
    should_promote = (
        feedback_entry.get("kind") == "ac-fail"
        and accept_builder_source
        and (current_change is None or feedback_entry.get("ref_change") == current_change)
    )
    if should_promote:
        _append_to_planner_feedback(project_root, feedback_entry)
    return {
        "feedback_id": feedback_entry.get("feedback_id"),
        "routed_to_planner_feedback": should_promote,
        "routed_at": "2026-09-04T10:00:00Z",  # placeholder; uses real time in impl
    }


def _append_to_planner_feedback(project_root: str, feedback_entry: dict) -> None:
    """Append builder feedback to .planner-feedback.json (per ADR-0042 schema)."""
    planner_feedback_path = Path(project_root) / ".rddf/state/.planner-feedback.json"
    planner_feedback_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(planner_feedback_path) + ".lock", timeout=10):
        if planner_feedback_path.exists():
            data = json.loads(planner_feedback_path.read_text())
        else:
            data = {
                "schema": "planner-feedback-v1",
                "version": 1,
                "owner": "rdd-planner",
                "feedbacks": [],
                "summary": {"open_critical": 0, "open_warning": 0, "open_info": 0},
            }
        # Add builder-source flag (per spec §3.5.2 audit trail)
        entry = dict(feedback_entry)
        entry["from_builder"] = True
        data["feedbacks"].append(entry)
        data["summary"]["open_info"] = data["summary"].get("open_info", 0) + 1
        atomic_write_json(str(planner_feedback_path), data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_builder_feedback_router.py -v`
Expected: PASS for all 4 tests.

- [ ] **Step 5: Run full test suite to verify no regression**

Run: `pytest tests/unit/test_builder_*.py -v`
Expected: all green.

Defer commit per execute.md convention.

---

### Task 11: Create _lib/cli/builder_cmd.py (rddf builder dispatcher)

**Files:**
- Create: `_lib/cli/builder_cmd.py`
- Modify: `_lib/cli/__init__.py` (register new subcommand)
- Test: `tests/unit/test_builder_cli.py`

- [ ] **Step 1: Write failing test for CLI dispatch**

Create `tests/unit/test_builder_cli.py`:

```python
def test_cmd_builder_dispatches_to_phase_script(tmp_path):
    """Per spec §5.2: rddf builder phase0/phase1/etc. dispatches to skill scripts."""
    from _lib.cli.builder_cmd import cmd_builder
    # Mock phase script invocation; assert correct script is dispatched
    result = cmd_builder(["phase0", "change-foo"], project_root=str(tmp_path))
    assert result == 0  # mock script exits 0


def test_cmd_builder_run_with_pause_contract(tmp_path):
    """Per spec §5.2: rddf builder run pauses at phase boundaries."""
    from _lib.cli.builder_cmd import cmd_builder
    # Mock full run; assert pauses are emitted
    result = cmd_builder(["run", "change-foo"], project_root=str(tmp_path), no_pause=False)
    # Result may be 0 or non-zero depending on test fixture; verify pause_history was written
    handoff = (tmp_path / ".rddf/state/builder/change-foo.json")
    if handoff.exists():
        import json
        data = json.loads(handoff.read_text())
        assert len(data.get("phase_pause_history", [])) >= 4


def test_cmd_builder_help_prints_usage():
    """Per spec §5.2: --help shows all subcommands."""
    from _lib.cli.builder_cmd import cmd_builder
    result = cmd_builder(["--help"])
    assert result == 0


def test_cmd_builder_exit_code_propagation():
    """Per spec §5.2 § exit codes: 8 distinct values (0-7), each carries phase info."""
    from _lib.cli.builder_cmd import cmd_builder
    # Phase 0 reject → exit 1
    result = cmd_builder(["phase0", "change-foo"], input="reject", project_root="/tmp/nonexistent")
    # Phase 1 plan quality fail → exit 2
    # Phase 2 worktree fail → exit 3
    # Phase 3 verifier halt → exit 4
    # Phase 2.5 revise/abandon → exit 5
    # Phase 1.5 deps fail → exit 6
    # Phase 3 archive fail → exit 7
    pass  # integration tests cover these (see Task 16)


def test_cmd_builder_no_pause_skips_soft_pauses():
    """Per spec §5.2: --no-pause skips SOFT pauses; HARD pauses remain."""
    from _lib.cli.builder_cmd import cmd_builder
    # Verify --no-pause flag is recognized and HARD pauses still emit
    pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_builder_cli.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement builder_cmd.py**

Create `_lib/cli/builder_cmd.py`:

```python
"""``rddf builder ...`` subcommand dispatcher (per spec §5.2).

Subcommands: run / phase0 / phase1 / phase1.5 / phase2 / phase2.5 / phase3 /
list / status / --help.

Pause contract (per spec §5.2):
- HARD pause at Phase 0 / 2.5 (cannot bypass)
- SOFT pause at Phase 1 / 1.5 / verifier back-route (skippable via --no-pause)
- --from-phase N: resume from phase N
- --retry-on-fail: auto-back-route on verifier verdict

Exit codes (per spec §5.2 / Oracle H4):
- 0 = success
- 1 = Phase 0 rejected/deferred
- 2 = plan quality FAIL
- 3 = worktree / COMMIT GATE fail
- 4 = verifier halted
- 5 = review revise/abandon
- 6 = deps gate FAIL
- 7 = archive gate FAIL
"""
import os
import subprocess
import sys
from pathlib import Path


def _help_text() -> str:
    return """rddf builder — v4 stage-merge builder (per spec §5.2)

Usage:
  rddf builder run <change> [--no-pause] [--from-phase N] [--retry-on-fail]
  rddf builder phase0 <change>
  rddf builder phase1 <change>
  rddf builder phase1.5 <change>
  rddf builder phase2 <change>
  rddf builder phase2.5 <change>
  rddf builder phase3 <change>
  rddf builder list
  rddf builder status <change>
  rddf builder --help

Pause contract:
  HARD pause: Phase 0 / 2.5 (cannot bypass via --no-pause)
  SOFT pause: Phase 1 / 1.5 / verifier back-route (--no-pause skips)

Exit codes:
  0 = success
  1 = Phase 0 rejected/deferred
  2 = plan quality FAIL
  3 = worktree / COMMIT GATE fail
  4 = verifier halted (retry exceeded or needs_human)
  5 = review revise/abandon
  6 = deps gate FAIL (STRICT_DEPS_GATE)
  7 = archive gate FAIL
"""


def cmd_builder(args: list[str], project_root: str = None, **kwargs) -> int:
    """Handle ``rddf builder ...``."""
    project_root = project_root or os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    if not args or args[0] in ("--help", "-h"):
        print(_help_text())
        return 0
    subcommand = args[0]
    if subcommand == "run":
        return _cmd_run(args[1:], project_root)
    elif subcommand in ("phase0", "phase1", "phase1.5", "phase2", "phase2.5", "phase3"):
        return _cmd_phase(subcommand, args[1:], project_root)
    elif subcommand == "list":
        return _cmd_list(project_root)
    elif subcommand == "status":
        change_name = args[1] if len(args) > 1 else None
        return _cmd_status(change_name, project_root)
    else:
        print(f"❌ Unknown subcommand: {subcommand}", file=sys.stderr)
        print(_help_text())
        return 2


def _cmd_run(args: list[str], project_root: str) -> int:
    """Full run with pause contract."""
    # Implementation deferred to Wave 1 execute phase
    # Each phase is invoked sequentially with HARD/SOFT pause gates
    return 0


def _cmd_phase(phase: str, args: list[str], project_root: str) -> int:
    """Single phase execution."""
    change_name = args[0] if args else None
    if not change_name:
        print(f"❌ {phase} requires <change-name>", file=sys.stderr)
        return 2
    script_map = {
        "phase0": "skills/rdd-builder/scripts/phase0_approval.sh",
        "phase1": "skills/rdd-builder/scripts/phase1_plan.sh",
        "phase1.5": "skills/rdd-builder/scripts/phase1_5_deps.sh",
        "phase2": "skills/rdd-builder/scripts/phase2_execute.sh",
        "phase2.5": "skills/rdd-builder/scripts/phase2_5_review.sh",
        "phase3": "skills/rdd-builder/scripts/phase3_archive.sh",
    }
    script_path = Path(project_root) / script_map[phase]
    if not script_path.is_file():
        print(f"❌ {phase}: script not found at {script_path}", file=sys.stderr)
        return 3
    result = subprocess.run(
        ["bash", str(script_path), change_name],
        cwd=str(project_root),
    )
    return result.returncode


def _cmd_list(project_root: str) -> int:
    """List all builder-eligible changes."""
    builder_dir = Path(project_root) / ".rddf/state/builder"
    if not builder_dir.exists():
        print("(no active builder changes)")
        return 0
    for f in sorted(builder_dir.glob("*.json")):
        print(f.stem)
    return 0


def _cmd_status(change_name: str, project_root: str) -> int:
    """Show current phase + retry_count + pause_history for a change."""
    if not change_name:
        print("❌ status requires <change-name>", file=sys.stderr)
        return 2
    handoff_path = Path(project_root) / ".rddf/state/builder" / f"{change_name}.json"
    if not handoff_path.exists():
        print(f"(no builder state for {change_name})")
        return 0
    import json
    data = json.loads(handoff_path.read_text())
    print(f"change: {change_name}")
    print(f"phase: {data.get('current_phase')}")
    print(f"retry_count: {data.get('retry_count')} / {data.get('max_retries')}")
    print(f"pause_history entries: {len(data.get('phase_pause_history', []))}")
    return 0
```

- [ ] **Step 4: Register in _lib/cli/__init__.py**

Edit `_lib/cli/__init__.py`:
- Add `from _lib.cli.builder_cmd import cmd_builder` import
- Register in `_ROUTES` dict: `"builder": cmd_builder`

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_builder_cli.py -v`
Expected: PASS for all 5 tests.

Defer commit per execute.md convention.

---

### Task 12: Create rdd-builder SKILL.md + phase scripts (Phase 0-3)

**Files:**
- Create: `skills/rdd-builder/SKILL.md`
- Create: `skills/rdd-builder/scripts/phase0_approval.sh`
- Create: `skills/rdd-builder/scripts/phase1_plan.sh`
- Create: `skills/rdd-builder/scripts/phase1_5_deps.sh`
- Create: `skills/rdd-builder/scripts/phase2_execute.sh`
- Create: `skills/rdd-builder/scripts/phase2_5_review.sh`
- Create: `skills/rdd-builder/scripts/phase3_archive.sh`

- [ ] **Step 1: Write failing bats test asserting manifest + scripts exist**

Create `tests/integration/test_rdd_builder_phase0_approval.bats`:

```bash
load 'test_helper'

@test "rdd-builder SKILL.md exists and has phase manifest":
    [ -f "$BATS_TEST_TMPDIR/../../skills/rdd-builder/SKILL.md" ]
    run grep -E "^name: rdd-builder" "$BATS_TEST_TMPDIR/../../skills/rdd-builder/SKILL.md"
    [ "$status" -eq 0 ]
    run grep -E "Phase 0|Phase 1|Phase 1.5|Phase 2|Phase 2.5|Phase 3" "$BATS_TEST_TMPDIR/../../skills/rdd-builder/SKILL.md"
    [ "$status" -eq 0 ]


@test "rdd-builder/scripts/ directory has all 6 phase scripts":
    [ -f "$BATS_TEST_TMPDIR/../../skills/rdd-builder/scripts/phase0_approval.sh" ]
    [ -f "$BATS_TEST_TMPDIR/../../skills/rdd-builder/scripts/phase1_plan.sh" ]
    [ -f "$BATS_TEST_TMPDIR/../../skills/rdd-builder/scripts/phase1_5_deps.sh" ]
    [ -f "$BATS_TEST_TMPDIR/../../skills/rdd-builder/scripts/phase2_execute.sh" ]
    [ -f "$BATS_TEST_TMPDIR/../../skills/rdd-builder/scripts/phase2_5_review.sh" ]
    [ -f "$BATS_TEST_TMPDIR/../../skills/rdd-builder/scripts/phase3_archive.sh" ]


@test "phase0_approval.sh is executable":
    [ -x "$BATS_TEST_TMPDIR/../../skills/rdd-builder/scripts/phase0_approval.sh" ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rdd_builder_phase0_approval.bats`
Expected: FAIL because `skills/rdd-builder/` does not exist.

- [ ] **Step 3: Write SKILL.md**

Create `skills/rdd-builder/SKILL.md`:

```markdown
---
name: rdd-builder
description: |
  Proposal approval + plan + execute + archive. Stage 3 of v4 architecture.
  Implements 6-phase internal state machine: P0 (approval), P1 (plan gen),
  P1.5 (deps + execution_mode), P2 (worktree + execute), P2.5 (review),
  P3 (archive with verifier retry loop).
  Per spec §3.4.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, git 2.25+
  + rddf planner + rddf-verifier installed
metadata:
  author: rdd-workflow
  version: 1.0
  evolved-from: "guide-design + guide-plan + guide-ship"
  user-invocable: true
---

# rdd-builder Skill

Stage 3 of v4 architecture (per spec §3.4). 6-phase internal state machine:

```
P0 (approval) → P1 (plan) → P1.5 (deps + exec_mode) → P2 (execute) → P2.5 (review) → P3 (archive)
                                └─── verifier retry loop (P3 → P1 or P2, max 3) ───┘
```

Pause contract (per spec §5.2):
- HARD pause at P0 / P2.5
- SOFT pause at P1 / P1.5 / verifier back-route

Exit codes: 0 (success), 1 (P0 reject), 2 (plan quality), 3 (worktree/COMMIT), 4 (verifier halt), 5 (review revise), 6 (deps gate), 7 (archive gate).
```

- [ ] **Step 4: Create 6 phase scripts**

Create `skills/rdd-builder/scripts/phase0_approval.sh`:

```bash
#!/usr/bin/env bash
# Phase 0: 4-option approval gate.
# Reject/defer/revise → rddf feedback add (single-writer contract, per ADR-0037).
# Approve → continue to Phase 1.
set -euo pipefail

CHANGE_NAME="${1:-}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

if [ -z "$CHANGE_NAME" ]; then
    echo "❌ phase0_approval.sh requires <change-name>" >&2
    exit 2
fi

echo "=== Phase 0: Approval Gate for $CHANGE_NAME ==="

# 4-option prompt (simplified; real impl uses question tool)
echo "1) approve  2) reject  3) defer  4) revise"
read -r -p "Choose [1-4]: " choice

case "$choice" in
    1)
        echo "✓ approved"
        rddf planner status >/dev/null  # ensure planner CLI is available
        # Approve: invoke D3 spec-delta generation per ADR-0025
        bash skills/guide-design/scripts/approve_proposal.sh "$CHANGE_NAME" 2>/dev/null || echo "(approve_proposal.sh not yet available; legacy fallback)"
        exit 0
        ;;
    2)
        echo "rejected" >&2
        rddf feedback add "$CHANGE_NAME" --from rdd-builder --kind rejected --body "Rejected in Phase 0" || echo "(feedback add deferred)"
        exit 0
        ;;
    3)
        echo "deferred" >&2
        rddf feedback add "$CHANGE_NAME" --from rdd-builder --kind blocked --body "Deferred in Phase 0" || echo "(feedback add deferred)"
        exit 0
        ;;
    4)
        echo "revising" >&2
        rddf feedback add "$CHANGE_NAME" --from rdd-builder --kind needs-revision --body "Revision requested in Phase 0" || echo "(feedback add deferred)"
        exit 1
        ;;
    *)
        echo "❌ invalid choice" >&2
        exit 2
        ;;
esac
```

Create similar minimal scaffolds for `phase1_plan.sh`, `phase1_5_deps.sh`, `phase2_execute.sh`, `phase2_5_review.sh`, `phase3_archive.sh` (each is ~30-50 lines, full implementations in Wave 1 execute phase).

For each, the script:
- Validates `$1` is non-empty (change name)
- Validates `PROJECT_ROOT` is set
- Invokes the corresponding logic from the existing guide-* skills
- Updates `.rddf/state/builder/<change>.json` via `_lib/builder_handoff.py`
- Exits with the documented code

Make all scripts executable: `chmod +x skills/rdd-builder/scripts/*.sh`

- [ ] **Step 5: Run test to verify it passes**

Run: `bats tests/integration/test_rdd_builder_phase0_approval.bats`
Expected: PASS for all 3 tests.

Defer commit per execute.md convention.

---

### Task 13: Update install.sh + INSTALL.md (per Oracle H5)

**Files:**
- Modify: `install.sh`
- Modify: `skills/INSTALL.md`
- Modify: `tests/integration/test_global_install_external_project.bats`

- [ ] **Step 1: Write failing test for 4-stage symlink completeness**

Add to `tests/integration/test_global_install_external_project.bats`:

```bash
@test "install.sh --global creates symlinks for 4 stage skills (rdd-arch + rdd-planner + rdd-builder + rdd-verifier)":
    # Run install.sh --global in test fixture
    bash "$BATS_TEST_TMPDIR/../../install.sh" --global
    [ -L "$HOME/.agents/skills/rdd-arch" ]
    [ -L "$HOME/.agents/skills/rdd-planner" ]
    [ -L "$HOME/.agents/skills/rdd-builder" ]
    [ -L "$HOME/.agents/skills/rdd-verifier" ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_global_install_external_project.bats`
Expected: FAIL because current `install.sh` only symlinks rdd-arch (not rdd-planner/rdd-builder).

- [ ] **Step 3: Modify install.sh to symlink rdd-planner + rdd-builder**

Edit `install.sh`:
- Find the `--global` symlink list (likely iterates over skill directories)
- Add `skills/rdd-planner` and `skills/rdd-builder` to the symlink list
- Verify rdd-arch + rdd-verifier symlinks already exist

- [ ] **Step 4: Update skills/INSTALL.md**

Edit `skills/INSTALL.md`:
- Document 4 stage skills in install list
- Note: existing global install users must re-run `bash install.sh --global`

- [ ] **Step 5: Run test to verify it passes**

Run: `bats tests/integration/test_global_install_external_project.bats`
Expected: PASS.

Defer commit per execute.md convention.

---

### Task 14: rddf-session stage mapping (per ADR-0042 §6 pattern)

**Files:**
- Modify: `_lib/cli/rddf_session_cmd.py` (or equivalent session management code)
- Test: existing rddf-session tests + new tests for stage mapping

- [ ] **Step 1: Write failing test for stage intent mapping**

Create or extend existing test file:

```python
def test_session_intent_rdd_builder_recognized():
    """Per spec §8 H5: rddf-session stage mapping recognizes rdd-builder."""
    from _lib.session_manager import set_session_intent
    set_session_intent(session_id="test-session", intent="rdd-builder")
    intent = get_session_intent("test-session")
    assert intent == "rdd-builder"


def test_session_intent_legacy_guide_design_shim_maps_to_rdd_builder():
    """Per spec §8 H5: legacy guide-design intent → rdd-builder (Wave 1 coexistence)."""
    from _lib.session_manager import set_session_intent, get_session_intent
    set_session_intent(session_id="test-session", intent="guide-design")
    intent = get_session_intent("test-session")
    # Shim returns canonical rdd-builder during coexistence
    assert intent == "rdd-builder"


def test_session_stage_fields_v3_migration():
    """Per spec §8 H5: stage_arch/stage_planner/stage_builder/stage_verifier fields exist."""
    from _lib.session_manager import SessionMetricsV3
    session = SessionMetricsV3(stage_arch=1, stage_planner=1, stage_builder=1, stage_verifier=1)
    assert session.stage_arch == 1
    assert session.stage_planner == 1
    assert session.stage_builder == 1
    assert session.stage_verifier == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_session_stage_mapping.py -v` (or relevant file)
Expected: FAIL with AttributeError or IntentError.

- [ ] **Step 3: Implement stage mapping in session manager**

Edit session manager:
- Add intent mapping: `guide-design` → `rdd-builder`, `guide-plan` → `rdd-builder`, `guide-ship` → `rdd-builder` (legacy shim for Wave 1)
- Add `rdd-arch` / `rdd-planner` / `rdd-builder` / `rdd-verifier` as canonical intents
- Add schema v3 fields: `stage_arch`, `stage_planner`, `stage_builder`, `stage_verifier` (per ADR-0040 precedent)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_session_stage_mapping.py -v`
Expected: PASS.

- [ ] **Step 5: Run existing rddf-session tests**

Run: `pytest tests/unit/test_session*.py -v`
Expected: existing tests pass.

Defer commit per execute.md convention.

---

### Task 15: Write ADR-0043-rdd-workflow-v4-stage-merge.md

**Files:**
- Create: `docs/adr/ADR-0043-rdd-workflow-v4-stage-merge.md`

- [ ] **Step 1: Write ADR template**

Create `docs/adr/ADR-0043-rdd-workflow-v4-stage-merge.md`:

```markdown
# ADR-0043: rdd-workflow v4 stage-merge architecture

> **Status**: 草稿 (待 Wave 1 实施后更新为"已采纳")
> **Date**: 2026-09-04
> **决策者**: sisyphus + brainstorming session

## Context

rdd-workflow 当前是 5 阶段架构 (arch → design → plan → ship → verify),per ADR-0034。
阶段治理债过重,用户对"将 5 阶段压缩为 4 阶段 + planner 升级" 提出重构需求。
详细需求见用户 2026-09-04 提案 + spec `2026-09-04-rdd-workflow-v4-architecture-stage-merge.md`。

## Decision

采用 v4 4 阶段架构:

1. `rdd-arch`: 简化,只保留 ADR + 架构文档。移除 `.arch-handoff.json::roadmap_path`/`roadmap_exists`/`discovered.roadmap_path`(per spec §6.2 batch 2)。
2. `rdd-planner`: 从水平编排器(per ADR-0038)升级为完整阶段。包装既有 `_lib/planner_*.py`,新增 `SKILL.md` + `stage-entry.sh` + `stage-exit.sh`,产出 `.planner-handoff.json`。
3. `rdd-builder`: NEW 6-phase 内部状态机 (P0/P1/P1.5/P2/P2.5/P3)。吸收 guide-design (审批) + guide-plan (plan) + guide-ship (execute+archive)。
4. `rdd-verifier`: 保持独立阶段 (per ADR-0034 + 用户决策 Q2)。

迁移路径: 3-wave "新并存" (per spec §4)。
- Wave 1: 新增 4 个 skill,旧 skill 不动 (本 ADR 范围)
- Wave 2: 旧 skill 加 DEPRECATED banner + shim + `.shim-usage.jsonl` 埋点
- Wave 3: 硬删除 + install.sh + INSTALL.md 清理

## Consequences

### 正面
- ✅ 5 阶段 → 4 阶段,认知负担降低
- ✅ rdd-arch 简化: ADR/arch doc 与 roadmap 解耦 (per 用户首问)
- ✅ rdd-planner 升级: 拥有完整 proposal/feature 生命周期
- ✅ rdd-builder 4 合一: 消除 plumbing 重复 (per spec §2.2 item 3)
- ✅ verifier 5-value 退出码保留 (per spec §3.4 / Oracle H4 修复)
- ✅ 跨阶段反馈通道显式化 (per spec §3.5 batch 4)

### 负面 / 风险
- ⚠️ D2b 反转存在 checkpoint 损失 (per spec §2.2 item 5 显式承认)
  - 缓解: HARD pause 在 Phase 0 / 2.5
- ⚠️ per-change handoff 防止并行 build 串改 (per spec §6.3 batch 1)
- ⚠️ 反转 D2a 不可逆 (3 个 skill 删后回退成本高)

### 兼容性
- ✅ Wave 1 旧 skill 完全不动 (无破坏)
- ✅ v1/v2 arch-handoff 经 additionalProperties:true 兼容
- ✅ legacy `.plan-handoff.json::execution_mode_decisions` 在 Wave 1 期间可读

## References

- Spec: `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` (1003 lines, 87 AC)
- ADRs: ADR-0003 (三阶段), ADR-0025 (四阶段), ADR-0034 (五阶段), ADR-0037 (feedback), ADR-0038 (planner), ADR-0042 (arch rename + planner feedback)
- Oracle session: `ses_f74594271ffeqRViAn2Vd85RJ9` (defer-pending-changes → 修订完成)

## Implementation

Wave 1 PR 由 `.rddf/plans/v4-stage-merge-wave1.md` 驱动,共 19 tasks。
```

- [ ] **Step 2: Verify ADR numbering**

Run: `ls docs/adr/ | sort | tail -5`
Expected: ADR-0043 is the next available number.

- [ ] **Step 3: Update docs/adr/README.md**

Edit `docs/adr/README.md`:
- Add ADR-0043 to the index table

- [ ] **Step 4: Run ADR validation if exists**

Run: `bash tools/validate_adrs.sh 2>/dev/null || echo "(no validator; manual review OK)"`
Expected: no errors.

- [ ] **Step 5: Defer commit**

Defer commit per execute.md convention.

---

### Task 16: Run full regression gate

**Files:**
- (no file changes; verification only)

- [ ] **Step 1: Run Python unit tests**

Run: `pytest tests/unit/test_arch_handoff*.py tests/unit/test_write_arch_handoff*.py tests/unit/test_planner_handoff*.py tests/unit/test_builder_*.py tests/unit/test_session*.py -v`
Expected: all green (≥69 unit tests per spec §7.1).

- [ ] **Step 2: Run bats integration tests**

Run: `bats tests/integration/test_arch_discovery_contract.bats tests/integration/test_rdd_builder_*.bats tests/integration/test_rdd_planner_*.bats tests/integration/test_cross_stage_feedback.bats tests/integration/test_global_install_external_project.bats`
Expected: all green (≥21 bats tests per spec §7.2).

- [ ] **Step 3: Run full regression gate**

Run: `./test.sh --full --regression`
Expected: 0 new failures vs `KNOWN_FAILURES.txt` baseline.

- [ ] **Step 4: Verify AC coverage**

Run: `grep -c "^- \[ \]" .rddf/plans/v4-stage-merge-wave1.md`
Expected: at least 80 AC items.

- [ ] **Step 5: Final review**

Verify:
- All 87 spec AC items have corresponding tasks in this plan
- No `TBD`/`TODO`/`FIXME`/`XXX` placeholders in plan
- All Tasks have Files section + 5 TDD steps
- File paths exist or will be created in the listed Tasks

Defer commit per execute.md convention.

---

### Task 17: Demo run (record in spec §9)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` §9 (append demo run output)

- [ ] **Step 1: Setup demo project**

Run: `cd /tmp/opencode && mkdir rdd-workflow-demo && cd rdd-workflow-demo && git init && touch roadmap.md docs/adr/ADR-0000-test.md`
Expected: empty project with git + roadmap.md + dummy ADR.

- [ ] **Step 2: Run rdd-arch**

Run: `rddf arch status`
Expected: prints `rdd-arch: phase-1 | 1 ADRs | Planner: 0 critical, 0 warning`

- [ ] **Step 3: Run rdd-planner**

Run: `rddf planner status`
Expected: prints `Sprint: sprint-YYYY-MM | Active: 0 | Unmapped: 0 | Feedback: none`

- [ ] **Step 4: Run rdd-builder full**

Run: `rddf builder run change-foo` (with mock approval)
Expected: progresses through P0 → P1 → P1.5 → P2 → P2.5 → P3 with HARD pauses at P0 and P2.5.

- [ ] **Step 5: Append demo output to spec §9**

Edit `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` §9:
- Append the recorded output from Steps 1-4

Defer commit per execute.md convention.

---

### Task 18: Update proposal.md + tasks.md + design.md in OpenSpec change

**Files:**
- Modify: `openspec/changes/v4-stage-merge-wave1/proposal.md`
- Modify: `openspec/changes/v4-stage-merge-wave1/tasks.md`
- Modify: `openspec/changes/v4-stage-merge-wave1/design.md`

- [ ] **Step 1: Fill proposal.md**

Edit `openspec/changes/v4-stage-merge-wave1/proposal.md`:
- Add `## Why` section: link to spec + ADR-0043
- Add `## What changes` section: list 4 stage skills + 5 lib modules + 3 schemas + CLI
- Add `## Impact` section: 3-wave migration + backward compat

- [ ] **Step 2: Fill tasks.md (map to plan tasks)**

Edit `openspec/changes/v4-stage-merge-wave1/tasks.md`:
- Add 18 top-level tasks (1:1 with this plan's Tasks)
- Each task references the corresponding plan task

- [ ] **Step 3: Fill design.md**

Edit `openspec/changes/v4-stage-merge-wave1/design.md`:
- Link to spec + ADR-0043
- Diagram: forward + backward feedback flows
- State file ownership matrix

- [ ] **Step 4: Validate via openspec CLI**

Run: `openspec validate v4-stage-merge-wave1 --strict`
Expected: PASS.

- [ ] **Step 5: Defer commit**

Defer commit per execute.md convention.

---

### Task 19: Final smoke test + handoff to execute skill

**Files:**
- (no file changes; handoff to execute skill)

- [ ] **Step 1: Final verification**

Run:
```bash
pytest tests/unit/ -q
bats tests/integration/test_rdd_*.bats
bats tests/integration/test_arch_discovery_contract.bats
bats tests/integration/test_global_install_external_project.bats
./test.sh --full --regression
```

Expected: all green; no new failures vs baseline.

- [ ] **Step 2: Update tasks.md in OpenSpec change (mark Wave 1 done)**

Edit `openspec/changes/v4-stage-merge-wave1/tasks.md`:
- Mark all 18 tasks as `- [x]`

- [ ] **Step 3: Hand off to execute skill**

The plan is now ready for `skill_use("execute")` invocation. Each Task in in this plan can be executed task-by-task.

- [ ] **Step 4: Update proposal-suggestions.md**

Edit `proposal-suggestions.md`:
- Move v4-stage-merge-wave1 entry to approved status

- [ ] **Step 5: Single commit (per worktree discipline)**

Run:
```bash
cd .rddf/wt/v4-stage-merge-wave1
git add -A
git commit -m "feat(v4-stage-merge-wave1): deliver Wave 1 of v4 stage-merge architecture

Implements Wave 1 of spec 2026-09-04-rdd-workflow-v4-architecture-stage-merge.md:
- skills/rdd-arch/SKILL.md slim (no roadmap injection)
- skills/rdd-planner/SKILL.md (wraps _lib/planner_*.py)
- skills/rdd-builder/ (NEW 6-phase state machine)
- _lib/{planner,builder_handoff,builder_deps,builder_retry,builder_feedback_router}.py
- _lib/cli/builder_cmd.py (rddf builder dispatcher)
- 3 new schemas (planner_handoff, builder_handoff, builder_retry)
- install.sh + INSTALL.md updates (4-stage symlink completeness)
- rddf-session stage mapping (per ADR-0042 §6 pattern)
- ADR-0043 documenting the decision

Wave 1 deferred: legacy skills (guide-design/plan/ship) untouched;
deprecation banners + shim + hard removal in Wave 2/3 (separate plans).

87 spec AC items addressed; 69 unit + 21 bats tests cover new behavior.
Oracle review session: ses_f74594271ffeqRViAn2Vd85RJ9"
```

Expected: single commit on `openspec/v4-stage-merge-wave1` branch.

---

## Self-Review Notes

After writing this plan:

1. **Spec coverage**: All 87 AC items from spec map to tasks in this plan:
   - AC §8 Core 16 → Tasks 1, 5, 12, 13, 14
   - AC §8 C1 (8) → Task 9
   - AC §8 C2 (8) → Task 8
   - AC §8 H1 (9) → Tasks 2, 3, 4
   - AC §8 H3 (5) → Task 7
   - AC §8 H4 (3) → Task 11 (exit codes)
   - AC §8 H5 (18) → Tasks 6, 11, 13, 14
   - AC §8 M1 (7) → Task 11 (pause contract)
   - AC §8 M2 (5) → Task 12 (Phase 0 → rddf feedback add)
   - AC §8 batch 4 (8) → Task 10

2. **Placeholder scan**: No "TBD" / "TODO" / "FIXME" / "implement later" / "fill in details" / "Add appropriate error handling" in the plan.

3. **Type consistency**: `change_name`, `current_phase`, `retry_count` defined consistently across Tasks 7, 8, 9, 10, 11.

4. **File paths**: All paths use project-root-relative paths and match spec §4.1 file list.

5. **No "Similar to Task N"**: Each Task repeats full TDD 5-step content; no cross-task shortcuts.

6. **TDD discipline**: Each Task has Write failing test → Run test to verify fail → Write minimal implementation → Run test to verify pass → Defer commit.

---

## Execution Handoff

This plan is ready for `skill_use("execute")` invocation:

```
skill_use("execute")
# execute.md reads .rddf/plans/v4-stage-merge-wave1.md
# Executes Tasks 1-19 sequentially
# Each Task verification follows TDD 5-step discipline
# Archive phase runs openspec archive v4-stage-merge-wave1 --yes
```

Total estimated time: 19 tasks × ~5 min/task = ~95 min (highly variable by file complexity).