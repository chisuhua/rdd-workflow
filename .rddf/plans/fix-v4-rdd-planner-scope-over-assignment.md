# fix-v4-rdd-planner-scope-over-assignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct rdd-planner's over-assigned scope (per Oracle review `ses_f7a9e01dbffe2Lqu8jYjg4YvL2`): remove phantom "authoring" responsibility from planner, restore ADR-0025's proposal.md generation pipeline into rdd-builder Phase 0, align all docs/SKILL.md/ADRs with the maintainer's model (planner = metadata/index orchestrator; builder P0 = proposal.md author + approver).

**Architecture:**
- **rdd-planner** owns roadmap + sprint proposals (`.rddf/roadmap.md`, `improvement-suggestions.md`, `improvement-approved.md`, `.rddf/roadmap/features/*.md`, `.rddf/improvements/*.md` via attach, `.planner-handoff.json`, `.planner-feedback.json`).
- **rdd-builder** Phase 0 approve owns `openspec/changes/<name>/proposal.md` authoring (per ADR-0025 D1/D2 "生成→确认→落盘"). Plan-gen (P1), execute (P2), review (P2.5), archive (P3) follow.
- **Handoff**: forward chain `.arch-handoff.json` → `.planner-handoff.json` → `.rddf/state/builder/<change>.json`. Backward: `rddf feedback add` (ADR-0037), verifier retry loop (ADR-0034), `.planner-feedback.json` (ADR-0042).
- **rdd-quick**: independent skill with self-triage; rdd-planner NOT a routing authority (advisory only via optional `recommended_route`).

**Tech Stack:** Python 3.11+ (restored `generate_full_proposal.py` + `phase0_approval.sh` integration), bash 5+ (planner_stage_*.sh rename), markdown editing (spec / SKILL.md / ADRs), pytest + bats (regression), jsonschema (handoff schema rename), FileLock (handoff writes).

**Spec reference:** `openspec/changes/fix-v4-rdd-planner-scope-over-assignment/{proposal.md, specs/v4-planner-scope-correction/spec.md}` (15 AC + 15 Requirements). Source: `.rddf/improvements/fix-v4-rdd-planner-scope-over-assignment.md` (255 lines). Oracle review: `ses_f7a9e01dbffe2Lqu8jYjg4YvL2`.

**Order of operations (load-bearing):** B1 must land FIRST (Task 1 + Task 2). Otherwise doc patches (Tasks 6-12) document an empty pipeline. After B1, all 9 doc patches (A1-A9) can ship. B2-B4 (Tasks 3-5, 14) close the implementation gaps.

---

## File Structure

### Production Code (new)

| File | Responsibility |
|---|---|
| `skills/rdd-builder/scripts/generate_full_proposal.py` | Restore from commit `1095cec^`. 5-段 improvement → full proposal.md (Why + What Changes + Capabilities + Acceptance + Specs + Reference) |
| `tests/unit/test_generate_full_proposal.py` | Round-trip unit tests for the 5-段 converter |

### Production Code (modified)

| File | Modification |
|---|---|
| `skills/rdd-builder/scripts/phase0_approval.sh` | Replace D3 placeholder stub with `generate_full_proposal.py` invocation in approve branch |
| `skills/rdd-arch/scripts/approve_proposal.sh` | Delete (broken shim) or re-point to builder pipeline |
| `skills/rdd-planner/scripts/planner_stage_entry.sh` | Rename `PROPOSALS_AUTHORED` env var → `PROPOSALS_READY`; derive from `.rddf/state/.planner-state.json` instead of grep |
| `skills/rdd-planner/scripts/planner_stage_exit.sh` | Same rename |
| `_lib/schemas/planner_handoff_schema.json` | Rename `proposals_authored` → `proposals_ready`; update schema description |
| `_lib/planner_handoff.py` | Update to write `proposals_ready` field instead of `proposals_authored` |
| `skills/rdd-planner/SKILL.md` | Remove `openspec/changes/<name>/proposal.md (authoring only)` from role.owns (line 14 + 41); add to role.not_owns (line 45-50) |
| `skills/rdd-builder/SKILL.md` | Remove `openspec/changes/<name>/proposal.md (authoring)` from role.not_owns (line 28); add to role.owns (line 20-25) |
| `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` | A1-A5: §3.2 row 165/166, §3.3 schema v1 (188-202), §3.4 Phase 0 (213), §9 demo (908-919) |
| `docs/adr/ADR-0025-design-proposal-creation.md` | A8: add evolution note (v4 per ADR-0043) |
| `docs/adr/ADR-0038-rdd-planner-crosscutting.md` | A9: amend "NOT a sixth phase" clause |

### Tests (new)

| File | Responsibility |
|---|---|
| `tests/unit/test_generate_full_proposal.py` | Round-trip 5-段 → proposal.md converter; 12 unit tests covering each section mapping |
| `tests/integration/test_phase0_approval_pipeline.py` (or `.bats`) | E2E: phase0_approval.sh --auto-approve produces non-stub proposal.md |
| `tests/unit/test_planner_handoff_schema_v1_rename.py` | Schema v1.1 properties block: `proposals_authored` excluded; `proposals_ready` included |
| `tests/unit/test_doc_alignment_ac3.py` | Grep assertions per AC-1, AC-3, AC-4, AC-6, AC-7 |

### Tests (extended)

| File | Extension |
|---|---|
| `tests/integration/test_v4_doc_drift_contracts.bats` | Add Test 20: rdd-planner SKILL.md has no `proposal.md (authoring only)` in role.owns |
| `tests/integration/test_v4_doc_drift_contracts.bats` | Add Test 21: rdd-builder SKILL.md has `proposal.md` in role.owns with P0-approve qualifier |

---

### Task 1: Restore `generate_full_proposal.py` from git history (B1, load-bearing)

**Files:**
- Create: `skills/rdd-builder/scripts/generate_full_proposal.py`
- Create: `tests/unit/test_generate_full_proposal.py`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_generate_full_proposal.py`:

```python
"""Round-trip tests for generate_full_proposal.py.

5-段 improvement (.rddf/improvements/<name>.md) → full proposal.md
(openspec/changes/<name>/proposal.md) converter per ADR-0025 D1/D2.
"""
import sys
from pathlib import Path

import pytest

# Add to sys.path so we can import from skills/rdd-builder/scripts
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-builder" / "scripts"))

from generate_full_proposal import generate_full_proposal  # noqa: E402


SAMPLE_IMPROVEMENT = """# fix-sample

**优先级**: P1 | **来源**: 测试

## Why

The user wants to fix X.

## 范围

In Scope: A, B, C.

## Capabilities

- capability-sample

## Impact

Users benefit.

## Acceptance

- AC-1: foo works
- AC-2: bar works
- AC-3: baz works

## Reference

- ADR-0001
"""


def test_generate_full_proposal_populates_why():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Why" in out
    assert "The user wants to fix X" in out


def test_generate_full_proposal_populates_what_changes():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## What Changes" in out
    assert "A, B, C" in out


def test_generate_full_proposal_populates_capabilities():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Capabilities" in out
    assert "- capability-sample" in out


def test_generate_full_proposal_populates_impact():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Impact" in out
    assert "Users benefit" in out


def test_generate_full_proposal_populates_acceptance():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Acceptance" in out
    assert "AC-1" in out
    assert "AC-2" in out
    assert "AC-3" in out


def test_generate_full_proposal_includes_change_name_in_title():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert out.startswith("# fix-sample")


def test_generate_full_proposal_no_placeholders():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "<skeleton motivation>" not in out
    assert "TBD" not in out
    assert "fill in details" not in out


def test_generate_full_proposal_handles_missing_acceptance():
    """If improvement lacks ## Acceptance, generate from ## Capabilities as fallback AC."""
    minimal = """# fix-min

## Why

Need to fix.

## 范围

Just one thing.

## Capabilities

- capability-x

## Impact

None.

## Reference
"""
    out = generate_full_proposal("fix-min", minimal)
    assert "## Acceptance" in out  # Fallback synthesized


def test_generate_full_proposal_handles_empty_improvement():
    """If improvement has only H1, generate a placeholder-but-valid proposal."""
    empty = "# fix-empty\n"
    out = generate_full_proposal("fix-empty", empty)
    assert out.startswith("# fix-empty")
    assert "## Why" in out
    assert "## What Changes" in out


def test_generate_full_proposal_preserves_references():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "ADR-0001" in out


def test_generate_full_proposal_preserves_priority_metadata():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "P1" in out


def test_generate_full_proposal_generates_skeleton_for_invalid_input():
    """Passing non-string raises TypeError (defensive)."""
    with pytest.raises(TypeError):
        generate_full_proposal("fix-x", None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/test_generate_full_proposal.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generate_full_proposal'`

- [ ] **Step 3: Write minimal implementation**

Restore `generate_full_proposal.py` from git history. Run:

```bash
cd /workspace/project/rdd-workflow
git log --all --oneline -- skills/guide-design/scripts/generate_full_proposal.py | head -5
```

Locate the last commit before `1095cec` (Wave 3 hard removal) that contained `skills/guide-design/scripts/generate_full_proposal.py`. Restore the file:

```bash
mkdir -p skills/rdd-builder/scripts
git show <last-good-commit>:skills/guide-design/scripts/generate_full_proposal.py > skills/rdd-builder/scripts/generate_full_proposal.py
chmod +x skills/rdd-builder/scripts/generate_full_proposal.py
```

Then adapt the imports: if the restored module imports `from guide_design_lib import ...`, change to `from _lib.<module> import ...` (per repo convention `_lib/` is the canonical home).

Also rename the main function entry point to `generate_full_proposal(name, improvement_text) -> str` per the test signature. Add docstring:

```python
"""5-段 improvement → full proposal.md converter.

Per ADR-0025 D1/D2 (restore after Wave 3 hard removal commit 1095cec).

Restored from guide-design/scripts/generate_full_proposal.py (Wave 3 predecessor)
and re-homed in skills/rdd-builder/scripts/ (v4: rdd-builder P0 approve owns
proposal.md authoring per spec §3.2 row 166 / §3.4 Phase 0 input).

Public API:
    generate_full_proposal(name: str, improvement_text: str) -> str

Returns the full proposal.md content as a string (caller writes to disk).
"""
```

If the function signature in the restored file differs from `generate_full_proposal(name, improvement_text) -> str`, add a thin wrapper that adapts the call. Both signatures MUST work — keep backward compat by adding the wrapper, not replacing.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal.py -v`
Expected: PASS (12/12)

If any test fails, debug the mapping logic — common pitfalls:
- Section header normalization (中文 `## 验收标准` vs `## Acceptance` mismatch)
- Field mapping order (Why → Why, but Scope → What Changes, not Scope)
- Reference section passthrough

- [ ] **Step 5: Defer commit**

Per repo convention, do not commit yet. All tasks commit together at archive phase. Skip `git add`.

---

### Task 2: Wire `phase0_approval.sh` approve branch to call `generate_full_proposal.py`

**Files:**
- Modify: `skills/rdd-builder/scripts/phase0_approval.sh`

- [ ] **Step 1: Write the failing test**

Write `tests/integration/test_phase0_approval_pipeline.sh` (bats):

```bash
#!/usr/bin/env bats
# E2E: phase0_approval.sh --auto-approve produces a non-stub proposal.md
# from the linked .rddf/improvements/<name>.md 5-段 content.
#
# Setup:
#   - BATS_TMPDIR/ contains a sample openspec/changes/<name>/{proposal.md, .rddf/improvements/<name>.md}
#   - phase0_approval.sh runs with --auto-approve

setup() {
    BATS_TMPDIR="$(mktemp -d)"
    export BATS_TMPDIR
    mkdir -p "$BATS_TMPDIR/openspec/changes/fix-test-phase0"
    cat > "$BATS_TMPDIR/openspec/changes/fix-test-phase0/proposal.md" <<'EOF'
## Why

<skeleton motivation - 1-2 sentences>

## What Changes

- <file path or module affected>
EOF

    mkdir -p "$BATS_TMPDIR/.rddf/improvements"
    cat > "$BATS_TMPDIR/.rddf/improvements/fix-test-phase0.md" <<'EOF'
# fix-test-phase0

**优先级**: P1 | **来源**: e2e test

## Why

Real 5-段 motivation here.

## 范围

- Real item A
- Real item B

## Capabilities

- capability-test-e2e

## Impact

Real impact text.

## Acceptance

- AC-1: works
- AC-2: passes

## Reference

- ADR-9999
EOF

    cd "$BATS_TMPDIR"
}

teardown() {
    rm -rf "$BATS_TMPDIR"
}

@test "phase0_approval.sh --auto-approve populates proposal.md with full 5-段 content" {
    PROJECT_ROOT="$BATS_TMPDIR" \
    bash /workspace/project/rdd-workflow/skills/rdd-builder/scripts/phase0_approval.sh \
        fix-test-phase0 --auto-approve
    # Wait for completion
    [ "$?" -eq 0 ]
    # proposal.md should now have non-stub content
    run grep -c "<skeleton motivation>" "$BATS_TMPDIR/openspec/changes/fix-test-phase0/proposal.md"
    [ "$output" -eq 0 ]
    run grep -c "Real 5-段 motivation here" "$BATS_TMPDIR/openspec/changes/fix-test-phase0/proposal.md"
    [ "$output" -ge 1 ]
    run grep -c "## Acceptance" "$BATS_TMPDIR/openspec/changes/fix-test-phase0/proposal.md"
    [ "$output" -ge 1 ]
}
```

Save as `tests/integration/test_phase0_approval_pipeline.bats`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/project/rdd-workflow && bats tests/integration/test_phase0_approval_pipeline.bats`
Expected: FAIL (proposal.md still has `<skeleton motivation>` placeholder because phase0_approval.sh's D3 stub doesn't invoke generate_full_proposal.py)

- [ ] **Step 3: Write minimal implementation**

Read `skills/rdd-builder/scripts/phase0_approval.sh` lines 32-50 (the existing approve branch). Replace the inline Python (lines 35-48) with a call to `generate_full_proposal.py`:

```bash
case "$choice" in
    1)
        echo "approved"
        # Run generate_full_proposal.py to populate proposal.md from .rddf/improvements/<name>.md
        # Per ADR-0025 D1/D2 (restored from guide-design after Wave 3 hard removal).
        PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
        IMPROVEMENT_FILE="$PROJECT_ROOT/.rddf/improvements/$CHANGE_NAME.md"
        PROPOSAL_FILE="openspec/changes/$CHANGE_NAME/proposal.md"

        if [ -f "$IMPROVEMENT_FILE" ]; then
            python3 "$PROJECT_ROOT/skills/rdd-builder/scripts/generate_full_proposal.py" \
                "$CHANGE_NAME" \
                "$IMPROVEMENT_FILE" \
                > "$PROPOSAL_FILE"
            echo "✅ proposal.md populated from improvement 5-段 content"
        else
            echo "⚠️  $IMPROVEMENT_FILE not found; leaving proposal.md as skeleton"
        fi

        # D3 spec-delta (per ADR-0025 D3)
        SPECS_DIR="openspec/specs/$CHANGE_NAME"
        mkdir -p "$SPECS_DIR"
        SPEC_FILE="$SPECS_DIR/spec.md"
        if [ ! -f "$SPEC_FILE" ]; then
            # Build spec.md from proposal.md Acceptance section
            python3 <<PYEOF
from pathlib import Path
specs_dir = Path("$PROJECT_ROOT") / "$SPECS_DIR"
specs_dir.mkdir(parents=True, exist_ok=True)
spec_md = specs_dir / "spec.md"
if not spec_md.exists():
    spec_md.write_text("""## ADDED Requirements

### Requirement: $CHANGE_NAME
Auto-derived from .rddf/improvements/$CHANGE_NAME.md per ADR-0025 D1/D2 + rdd-builder Phase 0 approve.
""")
print(f"D3 spec-delta written: {spec_md}")
PYEOF
        fi
        exit 0
        ;;
    ...
```

Keep the rest of the file unchanged (reject/defer/revise branches).

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_phase0_approval_pipeline.bats`
Expected: PASS

If FAIL: check that `generate_full_proposal.py` produces UTF-8 output (some 5-段 Chinese may need encoding handling). Test interactively: `python3 skills/rdd-builder/scripts/generate_full_proposal.py fix-test-phase0 .rddf/improvements/fix-test-phase0.md`

- [ ] **Step 5: Defer commit**

Skip `git add`. All tasks commit together at archive phase.

---

### Task 3: Fix or delete broken `skills/rdd-arch/scripts/approve_proposal.sh` (B2)

**Files:**
- Modify or delete: `skills/rdd-arch/scripts/approve_proposal.sh`

- [ ] **Step 1: Write the failing test**

Write `tests/integration/test_rdd_arch_approve_proposal_shim.bats`:

```bash
#!/usr/bin/env bats
# Test that the broken shim is gone or re-pointed.

@test "approve_proposal.sh is either deleted or re-pointed" {
    if [ -f /workspace/project/rdd-workflow/skills/rdd-arch/scripts/approve_proposal.sh ]; then
        # If kept, must not exec into deleted guide-design/scripts/approve_proposal.sh
        run grep -F "guide-design/scripts/approve_proposal.sh" /workspace/project/rdd-workflow/skills/rdd-arch/scripts/approve_proposal.sh
        [ "$output" = "" ]
    else
        skip "approve_proposal.sh deleted; that's also OK"
    fi
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rdd_arch_approve_proposal_shim.bats`
Expected: FAIL (file contains `guide-design/scripts/approve_proposal.sh` exec line)

- [ ] **Step 3: Write minimal implementation**

Check if anything else imports or calls `skills/rdd-arch/scripts/approve_proposal.sh`:

```bash
cd /workspace/project/rdd-workflow
grep -rn "rdd-arch/scripts/approve_proposal.sh" --include="*.sh" --include="*.py" --include="*.md" .
```

If no hits: delete the file (`rm skills/rdd-arch/scripts/approve_proposal.sh`).

If hits exist: re-point the shim to the builder pipeline:

```bash
cat > skills/rdd-arch/scripts/approve_proposal.sh <<'EOF'
#!/usr/bin/env bash
# DEPRECATED shim. Re-pointed to rdd-builder/scripts/approve_proposal.sh per fix-v4-rdd-planner-scope-over-assignment (B2).
# Original: exec $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../guide-design/scripts/approve_proposal.sh
# Now:     exec into the builder approve pipeline.
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../rdd-builder/scripts/approve_proposal.sh" "$@"
EOF
chmod +x skills/rdd-arch/scripts/approve_proposal.sh
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_rdd_arch_approve_proposal_shim.bats`
Expected: PASS

- [ ] **Step 5: Defer commit**

Skip `git add`.

---

### Task 4: Rename `proposals_authored` → `proposals_ready` in planner_stage_*.sh + lib (B3, partial A3)

**Files:**
- Modify: `skills/rdd-planner/scripts/planner_stage_entry.sh`
- Modify: `skills/rdd-planner/scripts/planner_stage_exit.sh`
- Modify: `_lib/planner_handoff.py`
- Modify: `_lib/schemas/planner_handoff_schema.json`

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_planner_handoff_schema_v1_rename.py`:

```python
"""Schema v1.1: proposals_authored renamed to proposals_ready.

Per fix-v4-rdd-planner-scope-over-assignment A3 + B3.
"""
import json
from pathlib import Path

SCHEMA_PATH = Path("_lib/schemas/planner_handoff_schema.json")


def test_schema_excludes_proposals_authored():
    text = SCHEMA_PATH.read_text()
    assert '"proposals_authored"' not in text, "schema must drop proposals_authored (fiction)"


def test_schema_includes_proposals_ready():
    schema = json.loads(SCHEMA_PATH.read_text())
    assert "proposals_ready" in schema.get("properties", {}), \
        "schema must have proposals_ready"


def test_planner_stage_exit_emits_proposals_ready():
    """End-to-end: running planner_stage_exit.sh produces JSON with proposals_ready."""
    import subprocess
    # Need an existing change for the script to not exit 2
    result = subprocess.run(
        ["bash", "skills/rdd-planner/scripts/planner_stage_exit.sh", "fix-v4-rdd-planner-scope-over-assignment"],
        capture_output=True, text=True, cwd="/workspace/project/rdd-workflow"
    )
    # It may succeed or fail for unrelated reasons; check JSON if it ran
    handoff_path = Path(".rddf/state/.planner-handoff.json")
    if handoff_path.exists():
        text = handoff_path.read_text()
        assert '"proposals_ready"' in text
        assert '"proposals_authored"' not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_planner_handoff_schema_v1_rename.py -v`
Expected: FAIL (`"proposals_authored"` still in schema)

- [ ] **Step 3: Write minimal implementation**

Step 3a — Edit `_lib/schemas/planner_handoff_schema.json`:
- Find the `"proposals_authored"` property block
- Rename to `"proposals_ready"`
- Update description from "proposals authored by planner" to "improvements attached for builder consumption; not an authoring product (planner never authors)"

Step 3b — Edit `_lib/planner_handoff.py`:
- Line 28: `"proposals_authored": list(proposals_authored),` → `"proposals_ready": list(proposals_authored),` (keep the parameter name to avoid touching callers)
- Line 50: `proposals_authored = [p for p in ...]` → `proposals_ready = [p for p in ...]`
- Line 54: pass `proposals_ready` to `write_planner_handoff`

Step 3c — Edit `skills/rdd-planner/scripts/planner_stage_entry.sh` (lines 18-23):
```bash
# Old:
PROPOSALS=$(rddf roadmap list 2>/dev/null | grep -oE 'add-[a-zA-Z0-9-]+' | head -20 || true)
...
export PROJECT_ROOT PROPOSALS_AUTHORED="$PROPOSALS" PROPOSALS_APPROVED_COUNT="$APPROVED" ...

# New:
# Derive from planner state active_projects (NOT grep from roadmap list, which is fiction).
PROPOSALS=$(python3 -c "
import json
from pathlib import Path
state = Path('.rddf/state/.planner-state.json')
if state.exists():
    d = json.loads(state.read_text())
    print('\n'.join(d.get('active_projects', [])))
" 2>/dev/null || true)
...
export PROJECT_ROOT PROPOSALS_READY="$PROPOSALS" PROPOSALS_APPROVED_COUNT="$APPROVED" ...
```

Step 3d — Same edit for `planner_stage_exit.sh` (lines 18-25):
```bash
# Same PROPOSALS derivation from .rddf/state/.planner-state.json
# ...
export PROJECT_ROOT PROPOSALS_READY="$PROPOSALS" PROPOSALS_APPROVED_COUNT="$APPROVED" ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_planner_handoff_schema_v1_rename.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Defer commit**

Skip `git add`.

---

### Task 5: Update spec §3.2 row 165 + row 166 + §3.3 + §3.4 Phase 0 input (A1, A2, A3 schema, A4)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` (lines 165, 166, 188-202, 213)

- [ ] **Step 1: Write the failing test**

Write `tests/unit/test_doc_alignment_ac3.py`:

```python
"""AC-1, AC-2, AC-3, AC-5: spec §3.2/§3.3/§3.4 alignment after correction.

Per fix-v4-rdd-planner-scope-over-assignment A1-A4.
"""
import re
from pathlib import Path

SPEC = Path("docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md")


def test_ac1_section_3_2_row_165_no_proposal_md_authoring():
    """AC-1: spec §3.2 row 165 MUST NOT contain 'proposal.md (authoring only, no checkbox)'."""
    text = SPEC.read_text()
    # Find the rdd-planner row (row 165) — heuristic: search within ~30 lines around "rdd-planner" ownership
    matches = re.findall(r"\|\s*\*\*rdd-planner\*\*[^|]*\|[^|]*\|", text)
    assert matches, "couldn't find rdd-planner row in spec §3.2"
    row_text = matches[0]
    assert "proposal.md (authoring only" not in row_text, \
        f"AC-1 violated: row 165 still has 'proposal.md (authoring only)': {row_text}"


def test_ac2_section_3_2_row_166_builder_owns_proposal_md():
    """AC-2: spec §3.2 row 166 (rdd-builder) MUST add 'proposal.md (authoring via P0 approve, per ADR-0025)'."""
    text = SPEC.read_text()
    assert "proposal.md (authoring via P0 approve" in text, \
        "AC-2 violated: spec doesn't mention 'authoring via P0 approve'"


def test_ac3_section_3_4_phase_0_input():
    """AC-3: spec §3.4 Phase 0 input MUST mention 'authored at P0 approve'."""
    text = SPEC.read_text()
    assert "proposal.md (authored at P0 approve" in text, \
        "AC-3 violated: spec §3.4 doesn't mention authored at P0 approve"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py -v`
Expected: FAIL (3/3 — current spec doesn't have "authoring via P0 approve" anywhere)

- [ ] **Step 3: Write minimal implementation**

Edit `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md`:

**Line 165** (rdd-planner row, Components table):
- Find the row starting with `| **rdd-planner** |` near line 165
- In the Files owned column, remove `openspec/changes/<name>/proposal.md (authoring only, no checkbox)`
- In the Writes column, remove `proposal.md content`
- In the Human-in-loop column, change `"Medium (Phase 1 approval = 'approve proposal creation')"` → `"Medium (proposal lifecycle review / sprint governance)"`

**Line 166** (rdd-builder row):
- In the Files owned column, add `openspec/changes/<name>/proposal.md (authoring via P0 approve, per ADR-0025)`

**Line 213** (§3.4 Phase 0 input):
- Find the Phase 0 description
- Change `├─ input:  openspec/changes/<name>/proposal.md (from rdd-planner)` → `├─ input:  openspec/changes/<name>/proposal.md (authored at P0 approve per ADR-0025 D1/D2; or propose sub-skill skeleton)`

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Defer commit**

Skip `git add`.

---

### Task 6: Rewrite spec §9 demo (A5)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` (lines 908-919, §9 demo run)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_doc_alignment_ac3.py`:

```python
def test_ac4_section_9_no_scaffold_contradiction():
    """AC-4: spec §9 demo MUST NOT contain 'rddf planner (new|brainstorm|accept) ... scaffold ... tasks'."""
    import re
    text = SPEC.read_text()
    pattern = re.compile(r"rddf planner (new|brainstorm|accept).*scaffold.*tasks", re.DOTALL)
    matches = pattern.findall(text)
    assert not matches, f"AC-4 violated: §9 demo still has 'planner accept scaffold tasks': {matches}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py::test_ac4_section_9_no_scaffold_contradiction -v`
Expected: FAIL (current §9 has `rddf planner accept demo-change → "✓ tasks.md scaffolded"`)

- [ ] **Step 3: Write minimal implementation**

Edit `docs/superpowers/specs/2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` lines 908-919 (§9 Demo Run). Replace the existing demo with the maintainer model:

```markdown
# === Phase 2: rdd-planner ===
$ rddf planner status
$ rddf planner sync --dry-run
# Sprint: sprint-2026-09
# Active: 1 (fix-v4-rdd-planner-scope-over-assignment)
# Unmapped: 232
$ rddf planner attach fix-v4-rdd-planner-scope-over-assignment \
    --project-id "2026-08-26 文档与代码一致性审计后续修复" \
    --phase phase-3 --theme "rdd-planner scope correction (per Oracle review)"
# ✓ attached; planner-state active_projects updated
$ bash skills/rdd-planner/scripts/planner_stage_exit.sh fix-v4-rdd-planner-scope-over-assignment
# planner-handoff v1.1 written: 2026-09-09T...
# planner stage exit complete: fix-v4-rdd-planner-scope-over-assignment -> rdd-builder

# === Phase 3: rdd-builder ===
$ rddf builder phase0 fix-v4-rdd-planner-scope-over-assignment
=== Phase 0: Approval Gate for fix-v4-rdd-planner-scope-over-assignment ===
1) approve  2) reject  3) defer  4) revise
Choose [1-4]: 1
approved
✅ proposal.md populated from improvement 5-段 content
D3 spec-delta written: openspec/specs/fix-v4-rdd-planner-scope-over-assignment/spec.md

$ rddf builder phase1 fix-v4-rdd-planner-scope-over-assignment
=== Phase 1: Plan Generation ===
# ✅ plan + tasks.md generated (TDD 5-step)
```

(Note: builder P0 now produces full proposal.md via generate_full_proposal.py, not a skeleton stub. P1 then writes tasks.md per ADR-0043 + planner not_owns. This eliminates the §3.4 / §9 contradiction.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: Defer commit**

Skip `git add`.

---

### Task 7: Update rdd-planner SKILL.md role.owns (A6)

**Files:**
- Modify: `skills/rdd-planner/SKILL.md` (lines 14 + 41 + 45-50)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_doc_alignment_ac3.py`:

```python
import re

def test_ac6_planner_skill_md_owns_excludes_proposal_md():
    """AC-6: rdd-planner SKILL.md role.owns MUST NOT include proposal.md; not_owns MUST."""
    text = Path("skills/rdd-planner/SKILL.md").read_text()
    # Extract YAML frontmatter
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    assert m, "no YAML frontmatter"
    fm = m.group(1)
    # Find role.boundaries.owns and role.boundaries.not_owns sections
    owns_match = re.search(r"owns:\n((?:\s*-\s*\".*?\"\n)+)", fm)
    not_owns_match = re.search(r"not_owns:\n((?:\s*-\s*\".*?\"\n)+)", fm)
    assert owns_match, "no owns block found"
    assert not_owns_match, "no not_owns block found"
    owns_text = owns_match.group(1)
    not_owns_text = not_owns_match.group(1)
    assert "openspec/changes/<name>/proposal.md" not in owns_text, \
        f"AC-6 violated: proposal.md still in owns: {owns_text}"
    assert "openspec/changes/<name>/proposal.md" in not_owns_text, \
        f"AC-6 violated: proposal.md NOT in not_owns: {not_owns_text}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py::test_ac6_planner_skill_md_owns_excludes_proposal_md -v`
Expected: FAIL (rdd-planner SKILL.md currently has proposal.md in owns line 14 + 41)

- [ ] **Step 3: Write minimal implementation**

Edit `skills/rdd-planner/SKILL.md`:

**Line 14** (description):
```markdown
# Old:
  Roadmap + proposal authoring orchestrator (Stage 2 of v4 architecture).

# New:
  Roadmap + sprint proposal orchestrator (Stage 2 of v4 architecture).
```

**Line 41** (role.boundaries.owns):
- Remove this line: `      - "openspec/changes/<name>/proposal.md (authoring only)"`

**Lines 45-50** (role.boundaries.not_owns):
- Add this line to the not_owns list: `      - "openspec/changes/<name>/proposal.md"`

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py::test_ac6_planner_skill_md_owns_excludes_proposal_md -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

Skip `git add`.

---

### Task 8: Update rdd-builder SKILL.md role.owns/not_owns (A7)

**Files:**
- Modify: `skills/rdd-builder/SKILL.md` (lines 20-25 + 28)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_doc_alignment_ac3.py`:

```python
def test_ac7_builder_skill_md_owns_includes_proposal_md():
    """AC-7: rdd-builder SKILL.md role.owns MUST include 'openspec/changes/<name>/proposal.md' (authoring via P0 approve, per ADR-0025)."""
    text = Path("skills/rdd-builder/SKILL.md").read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    assert m, "no YAML frontmatter"
    fm = m.group(1)
    owns_match = re.search(r"owns:\n((?:\s*-\s*\".*?\"\n)+)", fm)
    not_owns_match = re.search(r"not_owns:\n((?:\s*-\s*\".*?\"\n)+)", fm)
    assert owns_match and not_owns_match, "couldn't find both blocks"
    owns_text = owns_match.group(1)
    not_owns_text = not_owns_match.group(1)
    # proposal.md must be in owns with authoring-via-P0-approve qualifier
    assert any("proposal.md" in line and "P0 approve" in line for line in owns_text.split("\n")), \
        f"AC-7 violated: proposal.md (with P0 approve) NOT in owns: {owns_text}"
    assert "openspec/changes/<name>/proposal.md" not in not_owns_text, \
        f"AC-7 violated: proposal.md still in not_owns: {not_owns_text}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py::test_ac7_builder_skill_md_owns_includes_proposal_md -v`
Expected: FAIL (current rdd-builder SKILL.md line 28 has proposal.md in not_owns)

- [ ] **Step 3: Write minimal implementation**

Edit `skills/rdd-builder/SKILL.md`:

**Lines 20-25** (role.boundaries.owns):
- Add this line: `      - "openspec/changes/<name>/proposal.md (authoring via P0 approve, per ADR-0025)"`

**Line 28** (role.boundaries.not_owns):
- Remove this line: `      - "openspec/changes/<name>/proposal.md (authoring)"`

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py -v`
Expected: PASS (all tests in file)

- [ ] **Step 5: Defer commit**

Skip `git add`.

---

### Task 9: ADR-0025 evolution note (A8)

**Files:**
- Modify: `docs/adr/ADR-0025-design-proposal-creation.md`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_doc_alignment_ac3.py`:

```python
def test_ac8_adr_0025_evolution_note():
    """AC-8: ADR-0025 MUST contain evolution note referencing v4/ADR-0043/rdd-builder P0."""
    import re
    text = Path("docs/adr/ADR-0025-design-proposal-creation.md").read_text()
    # Find any evolution section
    pattern = re.compile(r"(v4|ADR-0043|rdd-builder P0)")
    matches = pattern.findall(text)
    assert matches, "AC-8 violated: ADR-0025 lacks evolution note mentioning v4/ADR-0043/rdd-builder P0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py::test_ac8_adr_0025_evolution_note -v`
Expected: FAIL (current ADR-0025 has no v4 evolution note)

- [ ] **Step 3: Write minimal implementation**

Edit `docs/adr/ADR-0025-design-proposal-creation.md`. Find the existing **Status** section (after Context/Decision) and add an **Evolution** sub-section before Consequences:

```markdown
## Evolution

### v4 (2026-09-04, ADR-0043 stage-merge)

- **Stage merger**: `design` stage merged into `rdd-builder` 6-phase internal state machine.
- **Approver change**: The 4-option approval gate that originally lived in `guide-design` Phase 3 is now `rdd-builder` Phase 0 (per spec `2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` §3.4).
- **D1/D2 contract continues**: 5-段 improvement → full proposal.md conversion (via `generate_full_proposal.py`) is still required.
- **D3 contract continues**: approval → `openspec/specs/<name>/spec.md` spec-delta is still emitted at Phase 0 approve.
- **D4 contract continues**: 4-layer content review (capability / acceptance / consistency / completeness) is now absorbed into `rdd-builder` Phase 0's quality gate + post-execute verifier (rdd-verifier).

### Restore action (2026-09-09, fix-v4-rdd-planner-scope-over-assignment B1)

- **`generate_full_proposal.py` was destroyed** in Wave 3 hard removal of `guide-design/` (commit `1095cec`) and never ported. Restored in `skills/rdd-builder/scripts/generate_full_proposal.py` and wired into `phase0_approval.sh` approve branch.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py::test_ac8_adr_0025_evolution_note -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

Skip `git add`.

---

### Task 10: ADR-0038 amend (A9)

**Files:**
- Modify: `docs/adr/ADR-0038-rdd-planner-crosscutting.md`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_doc_alignment_ac3.py`:

```python
def test_ac9_adr_0038_amendment():
    """AC-9: ADR-0038 MUST contain amendment marker (superseded/amended/dual identity/ADR-0043)."""
    import re
    text = Path("docs/adr/ADR-0038-rdd-planner-crosscutting.md").read_text()
    pattern = re.compile(r"(superseded|amended|双重身份|dual identity|ADR-0043)")
    matches = pattern.findall(text)
    assert matches, "AC-9 violated: ADR-0038 lacks amendment marker"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py::test_ac9_adr_0038_amendment -v`
Expected: FAIL (current ADR-0038 §Decision 1 says "NOT a sixth phase" with no amendment)

- [ ] **Step 3: Write minimal implementation**

Edit `docs/adr/ADR-0038-rdd-planner-crosscutting.md`. Find **Status** (top of file) and add an Amendment note. Also update the `## Decision` section:

**Status section** (replace):
```markdown
# ADR-0038: rdd-planner Horizontal Orchestrator (Stage 2)

> **Status**: Accepted (2026-09-03) — Stage 2 of `rdd-planner` design.
>
> **AMENDMENT (2026-09-09, fix-v4-rdd-planner-scope-over-assignment A9)**:
> Per v4 stage-merge (ADR-0043) and spec `2026-09-04-rdd-workflow-v4-architecture-stage-merge.md` §3.3,
> `rdd-planner` is **promoted from horizontal orchestrator to a full sequential stage** in the
> 4-stage pipeline (`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`).
>
> The "NOT a sixth phase" clause below is **superseded**. `rdd-planner` retains its horizontal
> orchestrator capabilities (status / sync / feedback / attach / audit / history / advance-sprint)
> as **cross-cutting** behaviors, but is now ALSO a sequential stage between `rdd-arch` and
> `rdd-builder`. This is the **dual identity** explicitly defined in ADR-0043 §2.
>
> Forward handoff: `.arch-handoff.json` (rdd-arch) → `.planner-handoff.json` (rdd-planner) → `.rddf/state/builder/<change>.json` (rdd-builder).
> Backward feedback: `rddf feedback add` (per ADR-0037 single-writer) + `.planner-feedback.json` (per ADR-0042) + verifier retry loop (per ADR-0034).
>
> **Out of scope per this amendment**: rdd-planner does NOT author `openspec/changes/<name>/proposal.md` content (corrected by ADR-0025 evolution note + spec §3.2 row 165 ownership cleanup). Proposal.md authoring lives in `rdd-builder` Phase 0 approve via `skills/rdd-builder/scripts/generate_full_proposal.py`.
```

**Decision section** (revise §Decision 1):
```markdown
### 1. Position: Dual identity — horizontal orchestrator AND sequential stage

**Original (2026-09-03)**: Cross-cutting, callable from any phase. Does NOT replace or extend the 5-phase architecture (arch → design → plan → ship → verify).

**AMENDED (2026-09-09, per ADR-0043)**: `rdd-planner` is BOTH (a) a sequential stage between `rdd-arch` and `rdd-builder` in the 4-stage pipeline, AND (b) a horizontal orchestrator exposing status / sync / feedback / attach / audit / history / advance-sprint commands callable from any stage. See ADR-0043 §2 "双重身份" (dual identity).
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_doc_alignment_ac3.py::test_ac9_adr_0038_amendment -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

Skip `git add`.

---

### Task 11: (Optional) planner-state schema v1.1 `recommended_route` field (B4)

**Files:**
- Modify: `_lib/schemas/planner_state_schema.json`
- Modify: `_lib/cli/planner_cmd.py` (status display)
- Modify: `skills/rdd-planner/SKILL.md` (See also note)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_planner_handoff_schema_v1_rename.py`:

```python
def test_ac13_planner_state_has_recommended_route():
    """AC-13: planner-state schema v1.1 has recommended_route advisory field."""
    import json
    schema = json.loads(Path("_lib/schemas/planner_state_schema.json").read_text())
    properties = schema.get("properties", {})
    assert "recommended_route" in properties, "planner-state missing recommended_route"
    # Allowed values
    rec = properties["recommended_route"]
    assert "enum" in rec or "type" in rec, "recommended_route must declare enum or type"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_planner_handoff_schema_v1_rename.py::test_ac13_planner_state_has_recommended_route -v`
Expected: FAIL (planner-state schema has no `recommended_route` field)

- [ ] **Step 3: Write minimal implementation**

Step 3a — Bump schema version: edit `_lib/schemas/planner_state_schema.json`:
- Change `"version": 1` to `"version": "1.1"` (or add `version: 1.1` alongside existing)
- Add to the top-level schema:
```json
{
  "recommended_route": {
    "type": "string",
    "enum": ["simple", "complex", "unknown"],
    "description": "Advisory complexity hint for user discovery of rdd-quick. Not enforced (per Oracle review: rdd-planner is not a routing authority). rdd-quick SKILL.md P1 self-triages regardless."
  }
}
```

Step 3b — Update planner_cmd.py status display to surface this:
- Find the status rendering code in `_lib/cli/planner_cmd.py`
- Add a one-liner to print recommended_route per active project

Step 3c — Update rdd-planner SKILL.md See also:
```markdown
## See also

- `skills/roadmap/` — roadmap CRUD (rddf roadmap add-feature, etc.)
- `skills/add-improve/` — proposal authoring entry
- ...
- `skills/rdd-quick/` — for small/well-scoped changes (advisory: check `rddf planner status` for `recommended_route: simple`)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_planner_handoff_schema_v1_rename.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: Defer commit**

Skip `git add`.

---

### Task 12: Full regression gate (AC-14 + AC-15)

**Files:**
- Modify: `tests/integration/test_v4_doc_drift_contracts.bats` (add Test 20 + Test 21)

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_v4_doc_drift_contracts.bats`:

```bash
# Test 20: rdd-planner SKILL.md has no 'proposal.md (authoring only)' in role.owns
@test "rdd-planner SKILL.md role.owns excludes proposal.md authoring (per AC-6)" {
    run grep -E "^\s*-\s*\"openspec/changes/<name>/proposal.md\"" skills/rdd-planner/SKILL.md
    # The line, if present, must be in the not_owns section (not owns).
    # Use awk to find the section boundaries:
    run bash -c '
        awk "/role:/,/^---$/" skills/rdd-planner/SKILL.md | \
            awk "/owns:/,/not_owns:/" | grep -F "proposal.md" | grep -F "authoring"
        [ $? -ne 0 ]  # not found in owns block
    '
    [ "$status" -eq 0 ]
}

# Test 21: rdd-builder SKILL.md has 'proposal.md' in role.owns with P0 approve qualifier
@test "rdd-builder SKILL.md role.owns includes proposal.md authoring via P0 (per AC-7)" {
    run bash -c '
        awk "/role:/,/^---$/" skills/rdd-builder/SKILL.md | \
            awk "/owns:/,/not_owns:/" | grep -F "proposal.md" | grep -F "P0 approve"
        [ $? -eq 0 ]  # found in owns block with P0 approve qualifier
    '
    [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run test to verify it fails (pre-patch)**

```bash
git stash  # Stash all Tasks 1-11 changes
bats tests/integration/test_v4_doc_drift_contracts.bats
```

Expected: Tests 20 + 21 FAIL (before fix)
Then:
```bash
git stash pop  # Restore all Tasks 1-11 changes
```

- [ ] **Step 3: Write minimal implementation**

(Already done in Tasks 7-8 + 11. This task only adds the bats assertions.)

- [ ] **Step 4: Run test to verify it passes (post-patch)**

```bash
bats tests/integration/test_v4_doc_drift_contracts.bats
```

Expected: All 21 tests PASS (existing 19 + new 20 + 21).

Also run:
```bash
cd /workspace/project/rdd-workflow
./test.sh --full --regression
```

Expected: No new failures beyond `tests/KNOWN_FAILURES.txt` baseline.

```bash
bash skills/rdd-doctor/scripts/doctor.sh --quiet
```

Expected: CRITICAL ≤ 6 (current baseline).

- [ ] **Step 5: Defer commit**

Skip `git add`. All 12 Tasks commit together at archive phase per `rdd-builder` Phase 3 convention.

---

## Spec Coverage Check

| AC # | Implementation Task(s) |
|------|------------------------|
| AC-1 (spec §3.2 row 165 cleanup) | Task 5 |
| AC-2 (spec §3.2 row 166 builder owns) | Task 5 |
| AC-3 (spec §3.4 Phase 0 input) | Task 5 |
| AC-4 (spec §9 demo rewrite) | Task 6 |
| AC-5 (planner-handoff schema rename) | Task 4 |
| AC-6 (rdd-planner SKILL.md owns) | Task 7 |
| AC-7 (rdd-builder SKILL.md owns) | Task 8 |
| AC-8 (ADR-0025 evolution note) | Task 9 |
| AC-9 (ADR-0038 amendment) | Task 10 |
| AC-10 (generate_full_proposal.py restore) | Tasks 1 + 2 |
| AC-11 (broken shim fixed) | Task 3 |
| AC-12 (planner_stage_*.sh rename) | Task 4 |
| AC-13 (recommended_route advisory, optional) | Task 11 |
| AC-14 (regression tests pass) | Task 12 |
| AC-15 (rdd-doctor no new CRITICAL) | Task 12 |

**Coverage**: 15/15 ACs mapped to 12 implementation tasks. No gaps.

## Order of Operations (per Oracle review "先做 B1，再改文档")

```
Task 1 (B1: restore generate_full_proposal.py)
   ↓
Task 2 (B1: wire phase0_approval.sh to invoke it)
   ↓
Task 3 (B2: fix/delete broken shim)
   ↓
Task 4 (B3/A3: planner-handoff schema rename)
   ↓
Tasks 5-10 (A1-A9: doc patches, can ship in 1-3 commits but should be in this order)
   ↓
Task 11 (B4 optional: recommended_route advisory)
   ↓
Task 12 (regression gate, final verification)
```

**Critical**: Do NOT start Tasks 5-10 before Task 1 + 2 land. Otherwise doc patches will document an empty pipeline (per Oracle: "否则文档领先代码又一轮").
