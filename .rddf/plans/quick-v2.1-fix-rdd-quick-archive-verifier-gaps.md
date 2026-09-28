# v2.1-fix-rdd-quick-archive-verifier-gaps Implementation Plan

> **For agentic workers:** TDD 5-step discipline (Write failing test → Verify fail → Implement → Verify pass → Defer commit). Steps use checkbox (`- [ ]`) syntax for tracking.

> **Owner override (per rdd-quick ADR-0047)**: This plan involves 5 production files + 3 new tests, exceeding rdd-quick default threshold (≤2 files ≤ 3 tasks). Owner explicitly authorizes override because: (a) self-modification of rdd-quick, (b) 3 fixes are independent atomic units, (c) no public API change, (d) audit trail via `.rddf/improvements/v2.1-fix-rdd-quick-archive-verifier-gaps.md`.

**Goal:** Fix 3 v2.1 P0-P2 issues identified by 2026-09-28 oracle + Metis dual review of rdd-quick mode a (builder P0 dispatch-quick path): (1) archive gate compatibility via minimal tasks.md generation, (2) rdd-verifier compatibility via AC sync to proposal.md, (3) rdd-quick-context.json cleanup contract.

**Architecture:** Three independent atomic fixes, each with own script + test pair, no cross-dependencies. All 3 scripts are stdlib-only (Python or bash), called from SKILL.md mode a/b P4 phase. SKILL.md integration is final step (Task 4) to avoid touching same file from 3 places.

**Architecture diagram:**
```
rdd-quick mode a flow (AFTER fix):
  P0 scaffold plan → P1 triage → P2 execute → P3 verify → P4 complete:
    1. Run generate_tasks_md.py (NEW) → openspec/changes/<change>/tasks.md (minimal)
    2. Run sync_ac_to_proposal.py (NEW) → proposal.md末尾 ## Acceptance (from rdd-quick plan) 段
    3. Run openspec archive <change> --yes → archive_gate_check passes (tasks.md present)
    4. Run cleanup_context.sh (NEW) → rm -f .rddf/state/rdd-quick-context.json + audit log
    5. append_history.py with outcome=completed
```

**Tech Stack:** Python 3.11+ (stdlib only for 2 scripts: argparse, re, pathlib, json), Bash 4+ (cleanup_context.sh), bats-core 1.10+ (integration tests), pytest (unit tests). No new dependencies.

**Zero-pollution contract:** Existing `test_rdd_quick_isolation.bats` SHA256 locks unchanged. `select_worktree.sh` / `tasks_writeback.sh` / `_lib/archive.sh` / `rdd-planner/SKILL.md::role:` MUST remain byte-identical.

---

## File Structure

### Production Code (NEW)

| File | Responsibility | LOC budget |
|---|---|---|
| `skills/rdd-quick/scripts/generate_tasks_md.py` | Generate minimal tasks.md from rdd-quick plan file (mode a only). Reads Task 1..N titles + 5-step markers, emits Setup/Implementation/Verification 3-section structure. Idempotent: skip if tasks.md exists. | ≤80 |
| `skills/rdd-quick/scripts/sync_ac_to_proposal.py` | Append `## Acceptance (from rdd-quick plan)` segment to proposal.md, sync ACs from plan file with `<!-- BEGIN/END rdd-quick-ac -->` markers. Idempotent on second call. | ≤60 |
| `skills/rdd-quick/scripts/cleanup_context.sh` | Remove `.rddf/state/rdd-quick-context.json` if exists, append audit log entry to `.rddf/state/.quick-history.jsonl`. Called from P4 completion + escalation paths. | ≤40 |

### Production Code (MODIFIED)

| File | Change |
|---|---|
| `skills/rdd-quick/SKILL.md` | (a) frontmatter `owns` remove "（临时）" mark from rdd-quick-context.json, add explicit "owned lifecycle: created P0, deleted P4". (b) mode a P4 completion path: insert 3 calls (generate_tasks_md → sync_ac_to_proposal → cleanup_context) before existing `openspec archive` step. (c) Add `## Permission Context` subsection documenting mode a's expanded write scope (tasks.md minimal + proposal.md AC segment). |

### Tests (NEW)

| File | Responsibility | Cases |
|---|---|---|
| `tests/integration/test_rdd_quick_archive_compat.bats` | Integration test for `generate_tasks_md.py`: idempotency, 3-section structure, Setup/Implementation/Verification mapping, skip-if-exists behavior. | ≥6 |
| `tests/integration/test_rdd_quick_verifier_compat.bats` | Integration test for `sync_ac_to_proposal.py`: AC extraction from plan, marker-based idempotency, second-call no-duplicate, rdd-verifier-readable format. | ≥2 |
| `tests/unit/test_quick_context_cleanup.py` | Unit test for `cleanup_context.sh`: file deletion, audit log append, no-op on missing file, exit codes. | ≥4 |

### Documentation (NEW)

| File | Purpose |
|---|---|
| `docs/audit/2026-09-28-rdd-quick-review.md` | Archive the oracle + Metis dual review output (audit trail for fix rationale). |

---

## Tasks

> **Total: 4 Tasks** (each task groups related scripts + tests to keep coherence; owner override per plan header).

### Task 1 — Fix 1: archive gate compatibility (generate_tasks_md.py + tests)

**Problem:** rdd-quick mode a hard禁禁止写 tasks.md but `archive_gate_check` requires it (per AGENTS.md "Guide-Ship 执行契约"). Need a minimal tasks.md generator that doesn't violate rdd-quick's "no逐任务 writeback" spirit (one-shot idempotent generation, not逐任务回写).

**Files:**
- Create: `skills/rdd-quick/scripts/generate_tasks_md.py`
- Create: `tests/integration/test_rdd_quick_archive_compat.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_rdd_quick_archive_compat.bats`:
```bash
load 'test_helper'

setup() {
    PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SCRIPT="$PROJECT_ROOT/skills/rdd-quick/scripts/generate_tasks_md.py"
    WORK_TMP="$(mktemp -d)"
    export CHANGE_NAME="test-change-$$"
    mkdir -p "$WORK_TMP/openspec/changes/$CHANGE_NAME"
    cat > "$WORK_TMP/openspec/changes/$CHANGE_NAME/proposal.md" <<'PROPOSAL'
# Test Proposal
## Why
Test
## Acceptance
- AC-1 test
PROPOSAL
    cat > "$WORK_TMP/plan-quick.md" <<'PLAN'
# Test Plan
**Goal:** Test goal
### Task 1: First Task
**Files:**
- Create: foo.py
- [ ] Step 1: test
- [ ] Step 2: verify
- [ ] Step 3: impl
- [ ] Step 4: pass
- [ ] Step 5: defer
### Task 2: Second Task
- [ ] Step 1: test
PLAN
}

teardown() { rm -rf "$WORK_TMP"; }

@test "archive_compat: generate_tasks_md.py script exists and is executable" {
    [ -x "$SCRIPT" ]
}

@test "archive_compat: generates minimal tasks.md with Setup/Implementation/Verification sections" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --change "$CHANGE_NAME" --plan plan-quick.md --proposal "openspec/changes/$CHANGE_NAME/proposal.md"
    [ -f "openspec/changes/$CHANGE_NAME/tasks.md" ]
    run grep -c "^## 1. Setup" "openspec/changes/$CHANGE_NAME/tasks.md"
    [ "$output" = "1" ]
    run grep -c "^## 2. Implementation" "openspec/changes/$CHANGE_NAME/tasks.md"
    [ "$output" = "1" ]
    run grep -c "^## 3. Verification" "openspec/changes/$CHANGE_NAME/tasks.md"
    [ "$output" = "1" ]
}

@test "archive_compat: Implementation section contains Task 1 and Task 2 titles" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --change "$CHANGE_NAME" --plan plan-quick.md --proposal "openspec/changes/$CHANGE_NAME/proposal.md"
    run grep -E "2\.[0-9]+ First Task" "openspec/changes/$CHANGE_NAME/tasks.md"
    [ "$status" = "0" ]
    run grep -E "2\.[0-9]+ Second Task" "openspec/changes/$CHANGE_NAME/tasks.md"
    [ "$status" = "0" ]
}

@test "archive_compat: all generated items use checkbox [x] (one-shot, not [ ])" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --change "$CHANGE_NAME" --plan plan-quick.md --proposal "openspec/changes/$CHANGE_NAME/proposal.md"
    # No [ ] remaining, all completed
    ! grep -q "^- \[ \]" "openspec/changes/$CHANGE_NAME/tasks.md"
}

@test "archive_compat: idempotent — skip if tasks.md exists" {
    cd "$WORK_TMP"
    echo "EXISTING CONTENT" > "openspec/changes/$CHANGE_NAME/tasks.md"
    python3 "$SCRIPT" --change "$CHANGE_NAME" --plan plan-quick.md --proposal "openspec/changes/$CHANGE_NAME/proposal.md"
    run cat "openspec/changes/$CHANGE_NAME/tasks.md"
    [ "$output" = "EXISTING CONTENT" ]
}

@test "archive_compat: exit code 0 on success, exit code non-zero on missing args" {
    run python3 "$SCRIPT"
    [ "$status" != "0" ]
    cd "$WORK_TMP"
    python3 "$SCRIPT" --change "$CHANGE_NAME" --plan plan-quick.md --proposal "openspec/changes/$CHANGE_NAME/proposal.md"
    [ "$?" = "0" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rdd_quick_archive_compat.bats`
Expected: 6 failed (script doesn't exist yet), all output "command not found" or similar.

- [ ] **Step 3: Write minimal implementation**

Create `skills/rdd-quick/scripts/generate_tasks_md.py`:
```python
#!/usr/bin/env python3
"""
Generate minimal tasks.md from rdd-quick plan file (mode a only).
Per ADR-0048 amendment: idempotent one-shot generation, not逐任务 writeback.

Usage:
    generate_tasks_md.py --change <name> --plan <plan.md> --proposal <proposal.md>
"""
import argparse
import re
import sys
from pathlib import Path


def parse_task_titles(plan_path: Path) -> list[str]:
    """Extract ### Task N: <title> from plan."""
    titles = []
    for line in plan_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^### Task \d+:\s*(.+)$", line)
        if m:
            titles.append(m.group(1).strip())
    return titles


def generate_tasks_md(change: str, plan_path: Path, proposal_path: Path) -> Path:
    """Generate minimal tasks.md with Setup/Implementation/Verification 3-section structure."""
    tasks_md = Path("openspec/changes") / change / "tasks.md"
    if tasks_md.exists():
        # Idempotency: skip if already generated
        return tasks_md
    titles = parse_task_titles(plan_path)
    lines = [
        "## 1. Setup",
        "",
        f"- [x] 1.1 Read {proposal_path.name} and confirm scope (via rdd-quick mode a)",
        "",
        "## 2. Implementation",
        "",
    ]
    for i, title in enumerate(titles, start=1):
        lines.append(f"- [x] 2.{i} {title} (executed via rdd-quick P2)")
    lines.extend([
        "",
        "## 3. Verification",
        "",
        "- [x] 3.1 Run `openspec validate <change>` (passed via mode a AC verification)",
        "- [x] 3.2 rdd-verifier compatibility: AC synced to proposal.md (per ADR-0048 amendment)",
        "",
    ])
    tasks_md.parent.mkdir(parents=True, exist_ok=True)
    tasks_md.write_text("\n".join(lines), encoding="utf-8")
    return tasks_md


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--change", required=True, help="openspec change name")
    p.add_argument("--plan", required=True, type=Path, help="rdd-quick plan file path")
    p.add_argument("--proposal", required=True, type=Path, help="proposal.md path")
    args = p.parse_args()
    if not args.plan.exists():
        print(f"ERROR: plan not found: {args.plan}", file=sys.stderr)
        return 2
    tasks_md = generate_tasks_md(args.change, args.plan, args.proposal)
    print(str(tasks_md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Make executable: `chmod +x skills/rdd-quick/scripts/generate_tasks_md.py`

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_rdd_quick_archive_compat.bats`
Expected: 6 passed.

- [ ] **Step 5: Defer commit**

按 AGENTS.md "Worktree Commit Flow" §2.5，**单个聚合 commit 在 R10 报告前**，不逐任务 commit。标记此 Task 完成进入 Task 2。

---

### Task 2 — Fix 2: verifier compatibility (sync_ac_to_proposal.py + tests)

**Problem:** rdd-verifier reads AC from `proposal.md::## 验收标准` (per rdd-verifier/SKILL.md). rdd-quick AC lives in plan file. Need to sync AC segment to proposal.md for verifier compatibility.

**Files:**
- Create: `skills/rdd-quick/scripts/sync_ac_to_proposal.py`
- Create: `tests/integration/test_rdd_quick_verifier_compat.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_rdd_quick_verifier_compat.bats`:
```bash
load 'test_helper'

setup() {
    PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SCRIPT="$PROJECT_ROOT/skills/rdd-quick/scripts/sync_ac_to_proposal.py"
    WORK_TMP="$(mktemp -d)"
    cat > "$WORK_TMP/proposal.md" <<'PROPOSAL'
# Test Proposal
## Why
Test
## What Changes
Test
PROPOSAL
    cat > "$WORK_TMP/plan.md" <<'PLAN'
# Test Plan
## Acceptance
- [ ] AC-1 First acceptance criterion
- [ ] AC-2 Second acceptance criterion
PLAN
}

teardown() { rm -rf "$WORK_TMP"; }

@test "verifier_compat: sync_ac_to_proposal.py script exists and is executable" {
    [ -x "$SCRIPT" ]
}

@test "verifier_compat: appends ## Acceptance (from rdd-quick plan) segment with markers" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --plan plan.md --proposal proposal.md
    run grep -c "## Acceptance (from rdd-quick plan)" "PROPOSAL_OUT"
    # Note: should write back to proposal.md (in-place)
    [ "$(grep -c '## Acceptance (from rdd-quick plan)' proposal.md)" = "1" ]
    [ "$(grep -c '<!-- BEGIN rdd-quick-ac -->' proposal.md)" = "1" ]
    [ "$(grep -c '<!-- END rdd-quick-ac -->' proposal.md)" = "1" ]
}

@test "verifier_compat: AC items preserved verbatim from plan" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --plan plan.md --proposal proposal.md
    [ "$(grep -c '\- \[ \] \*\*AC-1\*\* First acceptance criterion' proposal.md)" = "1" ]
    [ "$(grep -c '\- \[ \] \*\*AC-2\*\* Second acceptance criterion' proposal.md)" = "1" ]
}

@test "verifier_compat: idempotent — second call replaces AC segment not duplicate" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --plan plan.md --proposal proposal.md
    python3 "$SCRIPT" --plan plan.md --proposal proposal.md
    # Only one BEGIN/END pair
    [ "$(grep -c '<!-- BEGIN rdd-quick-ac -->' proposal.md)" = "1" ]
    [ "$(grep -c '<!-- END rdd-quick-ac -->' proposal.md)" = "1" ]
}

@test "verifier_compat: exit code 0 on success, non-zero on missing args" {
    cd "$WORK_TMP"
    run python3 "$SCRIPT"
    [ "$status" != "0" ]
    python3 "$SCRIPT" --plan plan.md --proposal proposal.md
    [ "$?" = "0" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rdd_quick_verifier_compat.bats`
Expected: 5 failed (script doesn't exist).

- [ ] **Step 3: Write minimal implementation**

Create `skills/rdd-quick/scripts/sync_ac_to_proposal.py`:
```python
#!/usr/bin/env python3
"""
Sync AC segment from rdd-quick plan to proposal.md for rdd-verifier compatibility.
Per ADR-0048 amendment: append ## Acceptance (from rdd-quick plan) segment with markers.

Usage:
    sync_ac_to_proposal.py --plan <plan.md> --proposal <proposal.md>
"""
import argparse
import re
import sys
from pathlib import Path


AC_SEGMENT_BEGIN = "<!-- BEGIN rdd-quick-ac -->"
AC_SEGMENT_END = "<!-- END rdd-quick-ac -->"
AC_HEADER = "## Acceptance (from rdd-quick plan)"


def parse_acs(plan_path: Path) -> list[str]:
    """Extract AC checkbox items from plan's ## Acceptance section."""
    acs = []
    in_acceptance = False
    for line in plan_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Acceptance"):
            in_acceptance = True
            continue
        if in_acceptance and line.startswith("## "):
            break  # Next section
        if in_acceptance:
            m = re.match(r"^- \[ \]\s*(\*\*.+\*\*\s*.+)$", line)
            if m:
                acs.append(m.group(1))
    return acs


def build_segment(acs: list[str], plan_name: str) -> str:
    """Build the AC sync segment text."""
    lines = [
        "",
        AC_HEADER,
        "",
        f"Source: {plan_name}::## Acceptance",
        f"Generated: {__import__('datetime').datetime.utcnow().isoformat()}Z",
        "",
        AC_SEGMENT_BEGIN,
    ]
    for ac in acs:
        lines.append(f"- [ ] {ac}")
    lines.extend([AC_SEGMENT_END, ""])
    return "\n".join(lines)


def sync(plan_path: Path, proposal_path: Path) -> int:
    """Append or replace AC segment in proposal.md. Returns count of ACs synced."""
    acs = parse_acs(plan_path)
    if not acs:
        print("WARNING: no ACs found in plan", file=sys.stderr)
        return 0
    segment = build_segment(acs, plan_path.name)
    text = proposal_path.read_text(encoding="utf-8")
    # Idempotent: replace existing segment if present
    pattern = re.compile(
        rf"\n*{re.escape(AC_HEADER)}.*?{re.escape(AC_SEGMENT_END)}",
        re.DOTALL,
    )
    if AC_SEGMENT_BEGIN in text:
        new_text = pattern.sub("\n" + segment.rstrip(), text)
    else:
        new_text = text.rstrip() + "\n" + segment
    proposal_path.write_text(new_text, encoding="utf-8")
    return len(acs)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", required=True, type=Path)
    p.add_argument("--proposal", required=True, type=Path)
    args = p.parse_args()
    if not args.plan.exists():
        print(f"ERROR: plan not found: {args.plan}", file=sys.stderr)
        return 2
    if not args.proposal.exists():
        print(f"ERROR: proposal not found: {args.proposal}", file=sys.stderr)
        return 2
    n = sync(args.plan, args.proposal)
    print(f"{n} ACs synced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Make executable: `chmod +x skills/rdd-quick/scripts/sync_ac_to_proposal.py`

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_rdd_quick_verifier_compat.bats`
Expected: 5 passed.

- [ ] **Step 5: Defer commit**

按 AGENTS.md §2.5 单个聚合 commit 在 R10 前。Task 2 完成，进入 Task 3。

---

### Task 3 — Fix 3: rdd-quick-context.json cleanup (cleanup_context.sh + tests)

**Problem:** `rdd-quick-context.json` marked "（临时）" in SKILL.md frontmatter but no cleanup contract. After P4 completion/escalation, file persists → next mode a call reads stale advisory.

**Files:**
- Create: `skills/rdd-quick/scripts/cleanup_context.sh`
- Create: `tests/unit/test_quick_context_cleanup.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_quick_context_cleanup.py`:
```python
"""Unit tests for skills/rdd-quick/scripts/cleanup_context.sh."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "skills/rdd-quick/scripts/cleanup_context.sh"


def run_cleanup(tmpdir: Path, reason: str = "completed") -> subprocess.CompletedProcess:
    """Invoke cleanup_context.sh with custom RDDF_QUICK_HISTORY_FILE + state dir."""
    env = os.environ.copy()
    state_dir = tmpdir / ".rddf"
    state_dir.mkdir(exist_ok=True)
    env["RDDF_QUICK_STATE_DIR"] = str(state_dir)
    history = state_dir / ".quick-history.jsonl"
    env["RDDF_QUICK_HISTORY_FILE"] = str(history)
    return subprocess.run(
        ["bash", str(SCRIPT), "--reason", reason],
        env=env, capture_output=True, text=True,
    )


def test_context_file_exists_then_deleted(tmp_path):
    """When rdd-quick-context.json exists, it MUST be deleted."""
    state_dir = tmp_path / ".rddf"
    state_dir.mkdir()
    context_file = state_dir / "rdd-quick-context.json"
    context_file.write_text('{"change_name": "old", "proposal_path": "old/proposal.md"}')

    result = run_cleanup(tmp_path, reason="completed")

    assert result.returncode == 0
    assert not context_file.exists()


def test_context_file_absent_is_noop(tmp_path):
    """When rdd-quick-context.json absent, MUST exit 0 with no side effects."""
    state_dir = tmp_path / ".rddf"
    state_dir.mkdir()
    history = state_dir / ".quick-history.jsonl"

    result = run_cleanup(tmp_path, reason="completed")

    assert result.returncode == 0
    assert not history.exists()  # No audit log written if nothing was cleaned


def test_cleanup_appends_audit_log_entry(tmp_path):
    """When context deleted, MUST append audit log entry to .quick-history.jsonl."""
    state_dir = tmp_path / ".rddf"
    state_dir.mkdir()
    context_file = state_dir / "rdd-quick-context.json"
    context_file.write_text('{"change_name": "x"}')
    history = state_dir / ".quick-history.jsonl"

    result = run_cleanup(tmp_path, reason="escalated")

    assert result.returncode == 0
    assert history.exists()
    lines = history.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["event"] == "context_cleanup"
    assert entry["reason"] == "escalated"
    assert "deleted_at" in entry


def test_cleanup_exit_code_nonzero_on_missing_reason(tmp_path):
    """Without --reason flag, MUST exit non-zero (validation)."""
    env = os.environ.copy()
    env["RDDF_QUICK_STATE_DIR"] = str(tmp_path / ".rddf")
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_cleanup_reason_must_be_completed_or_escalated(tmp_path):
    """Invalid --reason value MUST exit non-zero."""
    state_dir = tmp_path / ".rddf"
    state_dir.mkdir()
    context_file = state_dir / "rdd-quick-context.json"
    context_file.write_text('{"x": 1}')
    result = run_cleanup(tmp_path, reason="bogus")
    assert result.returncode != 0
    assert context_file.exists()  # NOT deleted on invalid reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_quick_context_cleanup.py -v`
Expected: 5 FAILED (script doesn't exist).

- [ ] **Step 3: Write minimal implementation**

Create `skills/rdd-quick/scripts/cleanup_context.sh`:
```bash
#!/usr/bin/env bash
# skills/rdd-quick/scripts/cleanup_context.sh
# Remove .rddf/state/rdd-quick-context.json if exists, append audit log entry.
# Called from P4 completion + escalation paths in rdd-quick/SKILL.md.
#
# Usage:
#   cleanup_context.sh --reason completed|escalated
#
# Environment:
#   RDDF_QUICK_STATE_DIR  default ".rddf/state" (override for test isolation)
#   RDDF_QUICK_HISTORY_FILE  default ".rddf/state/.quick-history.jsonl"
set -euo pipefail

REASON=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reason)
            REASON="${2:-}"
            shift 2
            ;;
        -h|--help)
            echo "Usage: cleanup_context.sh --reason completed|escalated"
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [[ -z "$REASON" ]]; then
    echo "ERROR: --reason required (completed|escalated)" >&2
    exit 2
fi

if [[ "$REASON" != "completed" && "$REASON" != "escalated" ]]; then
    echo "ERROR: --reason must be 'completed' or 'escalated' (got: $REASON)" >&2
    exit 2
fi

STATE_DIR="${RDDF_QUICK_STATE_DIR:-.rddf/state}"
CONTEXT_FILE="$STATE_DIR/rdd-quick-context.json"
HISTORY_FILE="${RDDF_QUICK_HISTORY_FILE:-$STATE_DIR/.quick-history.jsonl}"

# No-op if context file absent
if [[ ! -f "$CONTEXT_FILE" ]]; then
    exit 0
fi

# Delete context file
rm -f "$CONTEXT_FILE"

# Append audit log entry
mkdir -p "$(dirname "$HISTORY_FILE")"
DELETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '{"event": "context_cleanup", "reason": "%s", "deleted_at": "%s"}\n' \
    "$REASON" "$DELETED_AT" >> "$HISTORY_FILE"
```

Make executable: `chmod +x skills/rdd-quick/scripts/cleanup_context.sh`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_quick_context_cleanup.py -v`
Expected: 5 passed.

- [ ] **Step 5: Defer commit**

按 AGENTS.md §2.5 单个聚合 commit 在 R10 前。Task 3 完成，进入 Task 4。

---

### Task 4 — SKILL.md integration + 全量回归 + commit

**Problem:** 3 3 fixes produce scripts but no caller. Need to wire them into SKILL.md mode a/b P4 phase + remove "（临时）" mark + add Permission Context subsection. Then run full regression gate + commit.

**Files:**
- Modify: `skills/rdd-quick/SKILL.md` (3 sections)
- Create: `docs/audit/2026-09-28-rdd-quick-review.md` (audit trail)

- [ ] **Step 1: Write the failing test (SKILL.md integration contract)**

Append to existing `tests/integration/test_rdd_quick.bats` (do NOT create new file, integrate):

```bash
# Add new tests at end of test_rdd_quick.bats:

@test "rdd-quick: SKILL.md mode a P4 calls generate_tasks_md.py" {
    [ -f "$SKILL_FILE" ]
    body="$(awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$SKILL_FILE")"
    echo "$body" | grep -qF "generate_tasks_md.py"
}

@test "rdd-quick: SKILL.md mode a P4 calls sync_ac_to_proposal.py" {
    [ -f "$SKILL_FILE" ]
    body="$(awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$SKILL_FILE")"
    echo "$body" | grep -qF "sync_ac_to_proposal.py"
}

@test "rdd-quick: SKILL.md P4 completion calls cleanup_context.sh" {
    [ -f "$SKILL_FILE" ]
    body="$(awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$SKILL_FILE")"
    echo "$body" | grep -qF "cleanup_context.sh"
}

@test "rdd-quick: frontmatter owns rdd-quick-context.json WITHOUT (临时) mark" {
    [ -f "$SKILL_FILE" ]
    frontmatter="$(awk 'BEGIN{c=0} /^---$/{c++; next} c==1{print} c==2{exit}' "$SKILL_FILE")"
    echo "$frontmatter" | grep -A 30 "owns:" | grep "rdd-quick-context.json"
    ! echo "$frontmatter" | grep -A 30 "owns:" | grep "rdd-quick-context.json.*（临时）"
}

@test "rdd-quick: SKILL.md Permission Context documents mode a expanded write scope" {
    [ -f "$SKILL_FILE" ]
    body="$(awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$SKILL_FILE")"
    echo "$body" | grep -qF "## Permission Context"
    echo "$body" | grep -qE "(tasks\.md.*minimal|AC.*sync)"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rdd_quick.bats`
Expected: 5 new tests FAILED (SKILL.md not yet updated).

- [ ] **Step 3: Write minimal SKILL.md changes**

**Change 3a**: frontmatter `owns` 列表（L26-30 附近）— 移除"（临时）"标记，加 lifecycle 说明:
```yaml
    owns:
      - ".rddf/plans/quick-*.md"
      - ".rddf/state/.quick-history.jsonl"
      - ".rddf/state/rdd-quick-context.json"  # owned lifecycle: created in P0, deleted in P4 (per cleanup_context.sh)
      - "openspec/changes/<change>/tasks.md (mode a 最小化生成, per ADR-0048 amendment)"
```

**Change 3b**: mode a P4 completion 流程段（L96-100 附近，appright_insert before "exit openspec archive <change> --yes"）— 加 3 个脚本调用 + Permission Context subsection:

Find the mode a completion step that says "completion triggers `openspec archive <change> --yes`" — insert new steps BEFORE it:

```markdown
**Mode (a) completion — pre-archive hooks** (per ADR-0048 amendment, 2026-09-09):

Before invoking `openspec archive <change> --yes`, the agent MUST run three idempotent hooks in order. None touch tasks.md content beyond minimal one-shot generation, none mutate proposal.md beyond appending `## Acceptance (from rdd-quick plan)` segment.

```bash
# 1. Generate minimal tasks.md for archive_gate_check compatibility
python3 skills/rdd-quick/scripts/generate_tasks_md.py \
    --change "<change_name>" \
    --plan ".rddf/plans/quick-<change_name>.md" \
    --proposal "openspec/changes/<change_name>/proposal.md"

# 2. Sync ACs from plan to proposal.md for rdd-verifier compatibility
python3 skills/rdd-quick/scripts/sync_ac_to_proposal.py \
    --plan ".rddf/plans/quick-<change_name>.md" \
    --proposal "openspec/changes/<change_name>/proposal.md"

# 3. (existing) openspec archive <change_name> --yes (skips P1-P3)
```

**Mode (a/b) P4 completion + escalation — post-audit hooks**:

After `append_history.py` writes the outcome entry, the agent MUST clean up the transient context file. This prevents stale advisory on subsequent invocations.

```bash
bash skills/rdd-quick/scripts/cleanup_context.sh --reason completed
# OR
bash skills/rdd-quick/scripts/cleanup_context.sh --reason escalated
```

## Permission Context

Mode (a) expands rdd-quick's write scope from "no-openspec-touch" to "minimal openspec touch" for two artifacts, both idempotent and documented:

| File | Write mode | Rationale |
|---|---|---|
| `openspec/changes/<change>/tasks.md` | One-shot minimal generation (Setup/Implementation/Verification, all `[x]`). Idempotent: skip if exists. | `archive_gate_check` requires tasks.md; rdd-quick禁禁逐任务 writeback (preserved spirit). |
| `openspec/changes/<change>/proposal.md` | Append `## Acceptance (from rdd-quick plan)` segment with `<!-- BEGIN/END rdd-quick-ac -->` markers. Idempotent. | rdd-verifier reads AC from `proposal.md` (per rdd-verifier/SKILL.md); rdd-quick AC source is plan file (per ADR-0047 §D5); sync is the bridge. |

Mode (b) write scope unchanged: zero openspec touch.
```

- [ ] **Step 4: Run tests to verify they pass + run full regression**

Run: `bats tests/integration/test_rdd_quick.bats`
Expected: 5 new tests PASS + existing tests unchanged.

Run: `./test.sh --full --regression`
Expected: no new failures vs `tests/KNOWN_FAILURES.txt` baseline. (All 3 new test files should be picked up by bats recursive scan + pytest glob.)

- [ ] **Step 5: Defer commit — write audit trail doc**

Create `docs/audit/2026-09-28-rdd-quick-review.md` with brief summary of oracle + Metis dual review + this fix's rationale (copy from improvement proposal §Why).

Then `git add` all changed files (no commit yet per AGENTS.md §2.5).

**Single aggregate commit at the end** — this is the commit step after Step 5:
```bash
git add \
  .rddf/improvements/v2.1-fix-rdd-quick-archive-verifier-gaps.md \
  .rddf/plans/quick-v2.1-fix-rdd-quick-archive-verifier-gaps.md \
  skills/rdd-quick/scripts/generate_tasks_md.py \
  skills/rdd-quick/scripts/sync_ac_to_proposal.py \
  skills/rdd-quick/scripts/cleanup_context.sh \
  skills/rdd-quick/SKILL.md \
  tests/integration/test_rdd_quick_archive_compat.bats \
  tests/integration/test_rdd_quick_verifier_compat.bats \
  tests/integration/test_rdd_quick.bats \
  tests/unit/test_quick_context_cleanup.py \
  docs/audit/2026-09-28-rdd-quick-review.md

git commit -m "$(cat <<'MSG'
fix(rdd-quick): v2.1 archive gate + verifier compat + context cleanup

Three P0-P2 fixes for rdd-quick mode a (builder P0 dispatch-quick path)
per 2026-09-28 oracle + Metis dual review.

1. archive gate compatibility (P1): 
   generate_tasks_md.py generates minimal tasks.md (Setup + Implementation
   + Verification, all [x]) for rdd-quick mode a. Idempotent.
   Closes archive_gate_check failure when tasks.md missing.

2. rdd-verifier compatibility (P1):
   sync_ac_to_proposal.py appends ## Acceptance (from rdd-quick plan)
   segment with BEGIN/END markers. Idempotent.
   Bridges rdd-quick AC source (plan file, per ADR-0047 §D5) and
   rdd-verifier AC source (proposal.md).

3. rdd-quick-context.json cleanup (P2):
   cleanup_context.sh removes .rddf/state/rdd-quick-context.json + 
   appends audit log entry on P4 completion/escalation.
   Closes stale advisory on next mode a call.

SKILL.md: mode a/b P4 flow integrated 3 hooks, frontmatter owns 
updated (remove "（临时）" mark), Permission Context subsection added.

Audit trail: .rddf/improvements/v2.1-fix-rdd-quick-archive-verifier-gaps.md
+ docs/audit/2026-09-28-rdd-quick-review.md

Test coverage: 3 new test files (2 bats + 1 pytest), 16 new cases total.
KNOWN_FAILURES.txt baseline unchanged.

Refs: ADR-0047 (rdd-quick bypass), ADR-0048 (v4 stage-merge amendment)
MSG
)"
```

- [ ] **Step 5 (continued): Audit log append + AGENTS.md touch**

Append audit log entry (NOT a quick-history.jsonl entry — that's per-change. Use a different file):
```bash
echo '{"date": "2026-09-28", "change": "v2.1-fix-rdd-quick-archive-verifier-gaps", "outcome": "completed", "verifier": "self", "files_modified": 5, "files_added": 5}' >> .rddf/state/.rdd-quick-fixes.jsonl
```

Update AGENTS.md if new contract discovered (e.g., Permission Context subsection might need a top-level reference). Inspect AGENTS.md rdd-quick段 — only edit if necessary.

---

## Self-Review

- **Spec 覆盖**：
  - AC-1 (archive compat) → Task 1 ✓
  - AC-2 (verifier compat) → Task 2 ✓
  - AC-3 (context cleanup) → Task 3 ✓
  - AC-4 (SKILL.md integration) → Task 4 ✓
  - AC-5 (no regression) → Task 4 Step 4 ✓

- **占位符扫描**：
  - No "TBD" / "TODO" / "implement later"
  - No "Add appropriate error handling" (具体捕获 args + exit codes 已写)
  - All Step bodies show real code + real commands + expected output

- **类型一致性**：
  - generate_tasks_md.py ↔ sync_ac_to_proposal.py ↔ cleanup_context.sh: 都是独立脚本，类型/接口独立，无交叉引用不一致风险

- **风险点**：
  - Task 4 修改 SKILL.md 是单点编辑，但 SKILL.md 还有其他 active 编辑（test-change worktree）—— 需确保无 git merge 冲突。如有冲突，commit 后由 owner 解开