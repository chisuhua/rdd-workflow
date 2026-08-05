# Guide-Ship Execution Contract Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `guide-ship` the authoritative, gate-enforced execution contract for OpenSpec changes: discover candidates from filesystem ∪ plan-handoff ∪ iteration ∪ git, auto-select singletons, fail closed when `.rddf/plans/<change>.md` is missing or stale, share one completion gate across worktree and lightweight archive modes, and align the workspace + commit policy between `guide-ship` and `execute`.

**Architecture:**
- Add a single Python read-model `discover_ship_changes.py` that returns the union of disk + handoff + iteration + branch + worktree, normalized with `needs_reconciliation` flags.
- Promote `tasks.md` (OpenSpec scope) and `.rddf/plans/<change>.md` (executable) into a one-pager contract referenced by all three skills.
- Replace the `check_incomplete_tasks` undefined call with the existing `archive_gate_check` and wire it into both `archive_change` and the lightweight dispatch.
- Decide lightweight vs worktree **once** in `guide-ship` and pass the chosen `execution_root` to `execute` via an env var, so `execute` stops guessing.
- Make plan generation **fail closed** unless `SKIP_PROMETHEUS_PLANNING=yes` *and* `QUICK_FINISH_DETECTED=yes` are both set, eliminating the silent-success path.

**Tech Stack:** Python 3.11+ (skills), Bash (helpers), bats-core 1.10+ (integration tests), pytest 7+ (unit tests).

---

## File Structure

### Create

| Path | Responsibility |
|---|---|
| `skills/_lib/discover_ship_changes.py` | Read-only: returns union of disk/handoff/iteration/branch/worktree change candidates with normalized fields. |
| `skills/_lib/cli/discover_ship_changes_cmd.py` | `rddf discover-ship-changes --json` CLI handler; thin wrapper around the module. |
| `skills/_lib/discover_ship_changes.sh` | Bash wrapper that exports `SHIP_CANDIDATES_JSON` for SKILL.md bash consumers. |
| `docs/superpowers/specs/2026-08-05-guide-ship-execution-contract.md` | Contract one-pager (referenced from skills). |
| `tests/unit/test_discover_ship_changes.py` | Unit tests for the read-model. |
| `tests/integration/test_guide_ship_singleton.bats` | End-to-end: single change auto-selects. |
| `tests/integration/test_guide_ship_discovery.bats` | Disk-only, handoff-only, iteration-only, branch-only, worktree-only candidates. |
| `tests/integration/test_ship_archive_gate_wired.bats` | `archive_gate_check` is actually called by both archive modes. |
| `tests/integration/test_execute_workspace_root.bats` | `execute` honors `RDDF_EXECUTION_ROOT` env var. |

### Modify

| Path | Lines (approx.) | Change |
|---|---|---|
| `skills/guide-ship/SKILL.md` | L57-92, L175-210, L246-360, L452-493, L497-546 | Add contract preamble; replace interactive-only table with auto-select path; reference contract one-pager; align commit policy with `execute`. |
| `skills/execute/SKILL.md` | L17-50, L114-184 | Reference contract; honor `RDDF_EXECUTION_ROOT`; remove worktree-only assumption. |
| `skills/execute/scripts/select_worktree.sh` | L61-91 | Stop erroring on missing worktree when `RDDF_EXECUTION_ROOT` is set. |
| `skills/guide-ship/scripts/ship_plan.sh` | L144-202, L312-364, L425-476 | Use discover module; fail closed on missing plan; pass `RDDF_EXECUTION_ROOT` to `execute`. |
| `skills/guide-ship/scripts/ship_archive.sh` | L120-229 | Replace `check_incomplete_tasks` call with `archive_gate_check`; unify both modes. |
| `skills/_lib/archive.sh` | L243-267, L269-368 | Make `archive_change` and `archive_change_for_mode` share one gate call. |
| `skills/guide-plan/scripts/plan_done_gate.py` | `_load_execution_mode_decisions` | Warn when `deps-analysis.json` is older than the change. |
| `skills/_lib/cli/__init__.py` | `__main__.py:39-154` | Register `discover-ship-changes` subcommand. |
| `skills/rddf_session.py` (and pkg copy) | session hooks | Refresh heartbeat when `record_iteration_status` transitions a change. |

### Existing helpers reused, not duplicated

- `archive_gate_check` (skills/_lib/archive.sh:243-267)
- `state_reader.read_iteration` (skills/_lib/state_reader.py:115-245)
- `find_default_branch` (skills/_lib/worktree.sh)
- `record_iteration_status` (skills/guide-ship/scripts/ship_plan.sh L400-408)

---

## Task 1: Contract One-Pager (Documentation)

**Files:**
- Create: `docs/superpowers/specs/2026-08-05-guide-ship-execution-contract.md`

- [ ] **Step 1: Write the spec**

Create the file with this exact content:

```markdown
# guide-ship Execution Contract (v1)

## Authoritative files

| File | Owner | Read by | Written by |
|---|---|---|---|
| `openspec/changes/<name>/proposal.md` | guide-plan | guide-plan, guide-ship | guide-plan |
| `openspec/changes/<name>/design.md` | guide-plan | guide-plan, guide-ship | guide-plan |
| `openspec/changes/<name>/tasks.md` | guide-plan | all phases (progress only) | guide-plan, execute (writeback) |
| `.rddf/plans/<name>.md` | guide-ship | execute | guide-ship (via writing-plans) |
| `.rddf/state/iteration.json` | guide-plan + guide-ship | rddf CLI, dashboard | guide-plan, guide-ship |
| `.rddf/state/.plan-handoff.json` | guide-plan → guide-ship | guide-ship | guide-plan, guide-ship |
| `openspec/<name>` branch / `.rddf/wt/<name>` worktree | guide-ship | execute | guide-ship |

## Execution authority

- `tasks.md` is the OpenSpec scope and completion checklist.
- `.rddf/plans/<change>.md` is the **only** executable implementation contract.
- `execute` consumes the plan and writes completion state back to `tasks.md`.
- `guide-ship` does not execute `tasks.md` directly under any circumstance.

## Quick Finish

Quick Finish is a degenerate exit from this contract, not a separate contract.
Conditions (all required):
- ≤2 remaining tasks in `tasks.md`
- no uncommitted source changes
- no non-trivial keywords (refactor, migration, schema, breaking)
- no active blockers
- user explicitly confirms with `--quick-finish`

If any condition fails, the full plan → execute path is mandatory.

## Workspace

- `guide-ship` chooses `lightweight` (branch on main repo) or `worktree` (isolated worktree) **once** in Phase 1.
- The chosen workspace is exported as `RDDF_EXECUTION_ROOT` for `execute`.
- `execute` does not re-detect its workspace; it honors the env var.

## Commit policy

- `execute` does not commit per task.
- `guide-ship` Phase 2.7 creates one aggregate commit per change before archive.
- `archive.sh::check_worktree_commits` runs in both lightweight and worktree modes; the gate does not skip lightweight.
```

- [ ] **Step 2: Commit**

```bash
cd /workspace/project/rdd-workflow
git add docs/superpowers/specs/2026-08-05-guide-ship-execution-contract.md
git commit -m "docs: add guide-ship execution contract spec"
```

---

## Task 2: Discover Module — Python Read-Model

**Files:**
- Create: `skills/_lib/discover_ship_changes.py`
- Test: `tests/unit/test_discover_ship_changes.py`

- [ ] **Step 1: Write the failing unit test**

Create `tests/unit/test_discover_ship_changes.py`:

```python
"""Unit tests for the unified ship-change discovery read-model."""

import json
import subprocess
from pathlib import Path

import pytest

# Skip if the module isn't built yet
pytest.importorskip("skills._lib.discover_ship_changes")


def _make_change(tmp_path: Path, name: str, *, tasks: int = 0, done: int = 0) -> Path:
    change_dir = tmp_path / "openspec" / "changes" / name
    change_dir.mkdir(parents=True)
    tasks_md = change_dir / "tasks.md"
    lines = ["# Tasks\n"]
    for i in range(tasks):
        prefix = "- [x]" if i < done else "- [ ]"
        lines.append(f"{prefix} Task {i}\n")
    tasks_md.write_text("".join(lines))
    return change_dir


def test_disk_only_candidate_marked_needs_reconciliation(tmp_path: Path, monkeypatch):
    _make_change(tmp_path, "alpha", tasks=3, done=1)
    monkeypatch.chdir(tmp_path)
    from skills._lib.discover_ship_changes import discover

    result = discover(tmp_path)
    names = {c["name"] for c in result}
    assert "alpha" in names
    candidate = next(c for c in result if c["name"] == "alpha")
    assert candidate["filesystem_present"] is True
    assert candidate["iteration_status"] is None
    assert candidate["flags"] == ["needs_reconciliation"]


def test_executable_priority_order(tmp_path: Path, monkeypatch):
    """Disk + branch should outrank disk-only."""
    _make_change(tmp_path, "a", tasks=3, done=1)
    _make_change(tmp_path, "b", tasks=3, done=0)
    monkeypatch.chdir(tmp_path)
    # Fake branch for `a` only
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "openspec/a"], cwd=tmp_path, check=True)

    from skills._lib.discover_ship_changes import discover

    result = discover(tmp_path)
    names = [c["name"] for c in result]
    assert names.index("a") < names.index("b")
    assert "executable" in next(c for c in result if c["name"] == "a")["flags"]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_discover_ship_changes.py -q --tb=short
```

Expected: `ModuleNotFoundError` or `ImportError` for `skills._lib.discover_ship_changes`.

- [ ] **Step 3: Write the implementation**

Create `skills/_lib/discover_ship_changes.py`:

```python
"""Unified read-model for guide-ship change discovery.

Returns the union of:
  - non-archived filesystem change directories
  - names in .plan-handoff.json (current_change, committed_changes)
  - iteration.json entries whose status is not archived
  - openspec/* branch names
  - openspec/* worktree branch names

Each candidate carries normalized fields and a `flags` list so guide-ship can
rank them without re-implementing the discovery logic in bash.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Candidate:
    name: str
    filesystem_present: bool = False
    artifact_complete: bool = False
    iteration_status: Optional[str] = None
    branch: Optional[str] = None
    worktree: Optional[str] = None
    tasks_done: int = 0
    tasks_total: int = 0
    plan_present: bool = False
    plan_valid: bool = False
    blocked_by: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _disk_candidates(project_root: Path) -> dict[str, Candidate]:
    changes_dir = project_root / "openspec" / "changes"
    out: dict[str, Candidate] = {}
    if not changes_dir.exists():
        return out
    for entry in sorted(changes_dir.iterdir()):
        if not entry.is_dir() or entry.name == "archive":
            continue
        cand = Candidate(name=entry.name, filesystem_present=True)
        tasks_md = entry / "tasks.md"
        if tasks_md.exists():
            text = tasks_md.read_text(encoding="utf-8")
            cand.tasks_done = text.count("- [x]")
            cand.tasks_total = text.count("- [ ]") + cand.tasks_done
            proposal = (entry / "proposal.md").exists()
            design = (entry / "design.md").exists()
            cand.artifact_complete = proposal and design
        out[entry.name] = cand
    return out


def _handoff_candidates(project_root: Path) -> dict[str, Candidate]:
    handoff = _read_json(project_root / ".rddf" / "state" / ".plan-handoff.json")
    out: dict[str, Candidate] = {}
    for name in handoff.get("committed_changes", []) or []:
        out.setdefault(name, Candidate(name=name))
    cur = handoff.get("current_change")
    if cur:
        out.setdefault(cur, Candidate(name=cur))
    return out


def _iteration_candidates(project_root: Path) -> dict[str, Candidate]:
    data = _read_json(project_root / ".rddf" / "state" / "iteration.json")
    out: dict[str, Candidate] = {}
    for entry in data.get("changes", []) or []:
        status = entry.get("status")
        if status == "archived":
            continue
        cand = out.setdefault(entry["name"], Candidate(name=entry["name"]))
        cand.iteration_status = status
    return out


def _git_candidates(project_root: Path) -> dict[str, Candidate]:
    out: dict[str, Candidate] = {}
    # branches
    try:
        branches = subprocess.run(
            ["git", "branch", "--list", "openspec/*"],
            cwd=project_root, capture_output=True, text=True, check=True,
        ).stdout.splitlines()
    except subprocess.CalledProcessError:
        branches = []
    for line in branches:
        # "* openspec/foo" or "  openspec/foo"
        name = line.split()[-1].removeprefix("openspec/")
        cand = out.setdefault(name, Candidate(name=name))
        cand.branch = f"openspec/{name}"

    # worktrees
    try:
        wt = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=project_root, capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        wt = ""
    for block in wt.split("\n\n"):
        path = None
        branch = None
        for line in block.splitlines():
            if line.startswith("worktree "):
                path = line[len("worktree "):]
            elif line.startswith("branch "):
                branch = line[len("branch "):].removeprefix("refs/heads/")
        if branch and branch.startswith("openspec/"):
            name = branch.removeprefix("openspec/")
            cand = out.setdefault(name, Candidate(name=name))
            cand.worktree = path
    return out


def _merge(base: Candidate, overlay: Candidate) -> Candidate:
    """Overlay wins for non-default fields."""
    for field_name in (
        "filesystem_present", "artifact_complete", "iteration_status",
        "branch", "worktree", "tasks_done", "tasks_total",
        "plan_present", "plan_valid",
    ):
        overlay_val = getattr(overlay, field_name)
        default_val = getattr(Candidate(name=""), field_name)
        if overlay_val != default_val:
            setattr(base, field_name, overlay_val)
    base.blocked_by = list(set(base.blocked_by) | set(overlay.blocked_by))
    return base


def _classify(cand: Candidate) -> None:
    if not cand.filesystem_present:
        cand.flags.append("missing_disk")
    if not cand.artifact_complete:
        cand.flags.append("artifacts_incomplete")
    if cand.iteration_status is None and cand.filesystem_present:
        cand.flags.append("needs_reconciliation")
    if cand.worktree or cand.branch:
        cand.flags.append("in_progress" if cand.tasks_total - cand.tasks_done > 0 else "ready_to_archive")
    elif cand.filesystem_present and cand.artifact_complete:
        cand.flags.append("executable")
    else:
        cand.flags.append("needs_planning")


def discover(project_root: Path | str) -> List[Candidate]:
    root = Path(project_root)
    union: dict[str, Candidate] = {}
    for source in (_disk_candidates, _handoff_candidates, _iteration_candidates, _git_candidates):
        for name, cand in source(root).items():
            base = union.setdefault(name, Candidate(name=name))
            _merge(base, cand)
    # Plan presence
    for cand in union.values():
        plan = root / ".rddf" / "plans" / f"{cand.name}.md"
        cand.plan_present = plan.exists()
        cand.plan_valid = cand.plan_present  # caller may tighten with parse
    # Order: executable first, then in_progress, then others; alphabetical within tier
    priority = {
        "in_progress": 0,
        "executable": 1,
        "ready_to_archive": 2,
        "needs_planning": 3,
        "needs_reconciliation": 4,
        "artifacts_incomplete": 5,
        "missing_disk": 6,
    }
    decorated: list[tuple[tuple[int, str], Candidate]] = []
    for cand in union.values():
        _classify(cand)
        best = min((priority.get(f, 99) for f in cand.flags), default=99)
        decorated.append(((best, cand.name), cand))
    decorated.sort(key=lambda x: x[0])
    return [c for _, c in decorated]


if __name__ == "__main__":
    import sys
    out = [c.to_dict() for c in discover(sys.argv[1] if len(sys.argv) > 1 else ".")]
    print(json.dumps(out, indent=2))
```

- [ ] **Step 4: Run the unit test to verify it passes**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_discover_ship_changes.py -q --tb=short
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/discover_ship_changes.py tests/unit/test_discover_ship_changes.py
git commit -m "feat(ship): add unified change-discovery read-model"
```

---

## Task 3: Bash Wrapper for SKILL.md Bash Consumers

**Files:**
- Create: `skills/_lib/discover_ship_changes.sh`

- [ ] **Step 1: Write the wrapper**

```bash
#!/usr/bin/env bash
# Wrapper for skills._lib.discover_ship_changes.discover.
# Usage:
#   source skills/_lib/discover_ship_changes.sh
#   ship_candidates_json <project_root>   # echoes JSON list to stdout
#
# Side effect: sets SHIP_CANDIDATES_JSON in the calling shell.

set -euo pipefail

ship_candidates_json() {
    local project_root="${1:-.}"
    python3 -c "
import json, sys
sys.path.insert(0, '.')
from skills._lib.discover_ship_changes import discover
out = [c.to_dict() for c in discover('$project_root')]
print(json.dumps(out))
"
}

ship_candidate_count() {
    local project_root="${1:-.}"
    python3 -c "
import json, sys
sys.path.insert(0, '.')
from skills._lib.discover_ship_changes import discover
print(len(discover('$project_root')))
"
}

ship_top_candidate() {
    local project_root="${1:-.}"
    python3 -c "
import json, sys
sys.path.insert(0, '.')
from skills._lib.discover_ship_changes import discover
items = discover('$project_root')
print(items[0].name if items else '')
"
}
```

Make it executable:

```bash
chmod +x skills/_lib/discover_ship_changes.sh
```

- [ ] **Step 2: Commit**

```bash
git add skills/_lib/discover_ship_changes.sh
git commit -m "feat(ship): bash wrapper for change-discovery"
```

---

## Task 4: CLI Subcommand `rddf discover-ship-changes`

**Files:**
- Create: `skills/_lib/cli/discover_ship_changes_cmd.py`

- [ ] **Step 1: Inspect existing CLI handlers for the dispatch pattern**

```bash
cd /workspace/project/rdd-workflow
cat skills/_lib/cli/dashboard_cmd.py | head -60
```

Use this to mirror the dispatch style.

- [ ] **Step 2: Write the handler**

```python
"""rddf discover-ship-changes — print the unified candidate set as JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from skills._lib.discover_ship_changes import discover


def run(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    out = [c.to_dict() for c in discover(root)]
    if args.pretty:
        print(json.dumps(out, indent=2))
    else:
        print(json.dumps(out))
    return 0


def add_subparser(subparsers) -> None:
    p = subparsers.add_parser(
        "discover-ship-changes",
        help="Unified list of changes that may need guide-ship action",
    )
    p.add_argument("--project-root", default=".", help="Project root (default: cwd)")
    p.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    p.set_defaults(func=run)
```

- [ ] **Step 3: Register in `__main__.py`**

Open `skills/_lib/cli/__main__.py`. Find the block that registers other subparsers (search for `add_subparser` calls). Add:

```python
from skills._lib.cli import discover_ship_changes_cmd

discover_ship_changes_cmd.add_subparser(subparsers)
```

Do not duplicate imports if a parent `subparsers` symbol already exists.

- [ ] **Step 4: Smoke test**

```bash
cd /workspace/project/rdd-workflow
rddf discover-ship-changes --pretty | head -40
```

Expected: JSON array with one entry, `"name": "fix-rddf-init-broken-layout"`, `"flags": ["needs_reconciliation"]`.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/cli/discover_ship_changes_cmd.py skills/_lib/cli/__main__.py
git commit -m "feat(rddf): add discover-ship-changes CLI subcommand"
```

---

## Task 5: Singleton Auto-Select in `guide-ship` Phase 1

**Files:**
- Modify: `skills/guide-ship/SKILL.md` (Phase 1 entry)
- Modify: `skills/guide-ship/scripts/ship_plan.sh` (`run_ship_phase1`)

- [ ] **Step 1: Write a bats test (failing)**

Create `tests/integration/test_guide_ship_singleton.bats`:

```bats
#!/usr/bin/env bats

setup() {
    load 'test_helper'
    TEST_REPO="$BATS_TMPDIR/test-ship-singleton"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO"
    cd "$TEST_REPO"
    git init -q
    git checkout -q -b main
    mkdir -p openspec/changes/alpha
    printf '# Tasks\n- [ ] a\n- [ ] b\n' > openspec/changes/alpha/tasks.md
    printf '# Proposal\n' > openspec/changes/alpha/proposal.md
    printf '# Design\n' > openspec/changes/alpha/design.md
    mkdir -p .rddf/state
    echo '{}' > .rddf/state/.plan-handoff.json
}

@test "singleton change is auto-selected" {
    run bash -c "source '$PROJECT_ROOT/skills/guide-ship/scripts/ship_plan.sh' && ship_top_candidate '$TEST_REPO'"
    [ "$status" -eq 0 ]
    [ "$output" = "alpha" ]
}

@test "multi-change falls through to menu logic" {
    mkdir -p openspec/changes/beta
    printf '# Tasks\n- [ ] x\n' > openspec/changes/beta/tasks.md
    printf '# P\n' > openspec/changes/beta/proposal.md
    printf '# D\n' > openspec/changes/beta/design.md
    run bash -c "source '$PROJECT_ROOT/skills/_lib/discover_ship_changes.sh' && ship_candidate_count '$TEST_REPO'"
    [ "$status" -eq 0 ]
    [ "$output" = "2" ]
}
```

- [ ] **Step 2: Run the test to verify it passes**

The wrapper from Task 3 already supports this, so the test should pass on this task without further code changes.

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_guide_ship_singleton.bats
```

Expected: both tests pass.

- [ ] **Step 3: Wire auto-select into `run_ship_phase1`**

In `skills/guide-ship/scripts/ship_plan.sh`, locate `run_ship_phase1()` (around L425). Before the Quick Finish detection (L446), insert:

```bash
  # Auto-select when exactly one executable candidate exists.
  if [ -z "${CHANGE_NAME:-}" ] || [ "${CHANGE_NAME}" = "fix-rddf-init-broken-layout" ] && [ "$CHANGE_NAME" = "fix-rddf-init-broken-layout" ]; then
    : # explicit pass-through for documented default
  fi
  if [ -z "${CHANGE_NAME:-}" ]; then
    source "$project_root/../_lib/discover_ship_changes.sh" 2>/dev/null \
      || source "$project_root/skills/_lib/discover_ship_changes.sh"
    _count=$(ship_candidate_count "$project_root")
    if [ "$_count" = "1" ]; then
      CHANGE_NAME=$(ship_top_candidate "$project_root")
      echo "📌 检测到 1 个可执行 change, 自动选择: $CHANGE_NAME" >&2
    fi
    unset -f ship_candidate_count ship_top_candidate
  fi
```

If `CHANGE_NAME` is set explicitly by the caller, skip auto-select.

- [ ] **Step 4: Re-run the bats test**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_guide_ship_singleton.bats
```

Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add skills/guide-ship/scripts/ship_plan.sh tests/integration/test_guide_ship_singleton.bats
git commit -m "feat(ship): auto-select singleton change in Phase 1"
```

---

## Task 6: Fail Closed When Plan Is Missing or Stale

**Files:**
- Modify: `skills/guide-ship/scripts/ship_plan.sh` (`generate_implementation_plan`, L312-364)

- [ ] **Step 1: Write a bats test (failing)**

Create `tests/integration/test_ship_plan_required.bats`:

```bats
#!/usr/bin/env bats

setup() {
    load 'test_helper'
    TEST_REPO="$BATS_TMPDIR/test-ship-plan"
    rm -rf "$TEST_REPO"
    mkdir -p "$TEST_REPO" && cd "$TEST_REPO"
    git init -q && git checkout -q -b main
    mkdir -p openspec/changes/alpha .rddf/state
    echo '{}' > .rddf/state/.plan-handoff.json
    echo '{}' > .rddf/state/iteration.json
}

@test "missing plan without QUICK_FINISH fails" {
    SKIP_PROMETHEUS_PLANNING=yes \
        run bash -c "PROJECT_ROOT='$TEST_REPO'; CHANGE_NAME='alpha'; source '$PROJECT_ROOT/../skills/guide-ship/scripts/ship_plan.sh' 2>/dev/null; generate_implementation_plan '$TEST_REPO' 'alpha' 'lightweight'"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "❌" ]]
}

@test "QUICK_FINISH=yes allows placeholder plan" {
    QUICK_FINISH_DETECTED=yes SKIP_PROMETHEUS_PLANNING=yes \
        run bash -c "source '$TEST_REPO/../skills/guide-ship/scripts/ship_plan.sh' 2>/dev/null; generate_implementation_plan '$TEST_REPO' 'alpha' 'lightweight'"
    [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_ship_plan_required.bats
```

Expected: the first test fails because the current code returns success on `SKIP_PROMETHEUS_PLANNING=yes`.

- [ ] **Step 3: Update `generate_implementation_plan`**

In `skills/guide-ship/scripts/ship_plan.sh` around L312-360, replace the early-skip block:

```bash
  if [ "${SKIP_PROMETHEUS_PLANNING:-no}" = "yes" ]; then
    if [ "${QUICK_FINISH_DETECTED:-no}" != "yes" ]; then
      echo "❌ SKIP_PROMETHEUS_PLANNING=yes requires QUICK_FINISH_DETECTED=yes (计划文件是 execute 的唯一执行契约, 复杂 change 不允许绕过)" >&2
      return 2
    fi
    echo "⚠️  Quick Finish 跳过实施计划生成" >&2
    mkdir -p "$project_root/.rddf/plans"
    printf '# Quick Finish Placeholder\n- [ ] skip-plan\n' > "$project_root/.rddf/plans/$change_name.md"
    echo 0
    return 0
  fi
```

Keep the rest of the function as-is.

- [ ] **Step 4: Re-run the bats test**

```bash
bats tests/integration/test_ship_plan_required.bats
```

Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add skills/guide-ship/scripts/ship_plan.sh tests/integration/test_ship_plan_required.bats
git commit -m "feat(ship): require QUICK_FINISH to skip plan generation"
```

---

## Task 7: Wire `archive_gate_check` Into Both Archive Modes

**Files:**
- Modify: `skills/guide-ship/scripts/ship_archive.sh` (L120-229)
- Modify: `skills/_lib/archive.sh` (L243-267, L269-368)

- [ ] **Step 1: Write a bats test (failing)**

Create `tests/integration/test_ship_archive_gate_wired.bats`:

```bats
#!/usr/bin/env bats

setup() {
    load 'test_helper'
    TEST_REPO="$BATS_TMPDIR/test-arch-gate"
    rm -rf "$TEST_REPO" && mkdir -p "$TEST_REPO" && cd "$TEST_REPO"
    git init -q && git checkout -q -b main
    mkdir -p openspec/changes/alpha
    printf -- '- [ ] a\n- [ ] b\n' > openspec/changes/alpha/tasks.md
}

@test "archive_gate_check is called by archive_change" {
    run bash -c "PROJECT_ROOT='$TEST_REPO'; source '$PROJECT_ROOT/skills/_lib/archive.sh'; archive_change 'alpha' 'main' 2>&1"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "archive_gate_check" ]] || [[ "$output" =~ "incomplete" ]]
}

@test "lightweight archive also calls archive_gate_check" {
    # Lightweight mode lives in ship_archive.sh; assert the gate is referenced.
    grep -q 'archive_gate_check' "$PROJECT_ROOT/skills/guide-ship/scripts/ship_archive.sh"
}
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_ship_archive_gate_wired.bats
```

Expected: the first test fails because `archive_change` does not call `archive_gate_check`.

- [ ] **Step 3: Make `archive_change` call `archive_gate_check`**

In `skills/_lib/archive.sh`, find `archive_change()` (around L269). Insert at the top of the function body, after parameter parsing:

```bash
  archive_gate_check "$name" >/dev/null || return 3
```

Make sure `archive_gate_check` is sourced (it lives in the same file, so no extra source line is needed).

- [ ] **Step 4: Replace `check_incomplete_tasks` in `ship_archive.sh`**

In `skills/guide-ship/scripts/ship_archive.sh` around L120-129, replace:

```bash
  if ! check_incomplete_tasks "$change_name" 2>/dev/null; then
```

with:

```bash
  if ! archive_gate_check "$change_name" 2>/dev/null; then
```

Source `archive_gate_check` by adding near the top of `ship_archive.sh` (after existing source lines):

```bash
source "$PROJECT_ROOT/skills/_lib/archive.sh"
```

(or the equivalent resolver from your `skill_root.sh` shim).

- [ ] **Step 5: Re-run the bats test**

```bash
bats tests/integration/test_ship_archive_gate_wired.bats
```

Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add skills/guide-ship/scripts/ship_archive.sh skills/_lib/archive.sh tests/integration/test_ship_archive_gate_wired.bats
git commit -m "fix(archive): wire archive_gate_check into both modes"
```

---

## Task 8: Unify Workspace Choice (`RDDF_EXECUTION_ROOT`)

**Files:**
- Modify: `skills/guide-ship/scripts/ship_plan.sh` (`setup_execution_workspace`)
- Modify: `skills/execute/scripts/select_worktree.sh` (L61-91)
- Modify: `skills/guide-ship/SKILL.md`
- Modify: `skills/execute/SKILL.md`

- [ ] **Step 1: Write a bats test (failing)**

Create `tests/integration/test_execute_workspace_root.bats`:

```bats
#!/usr/bin/env bats

setup() {
    load 'test_helper'
}

@test "execute honors RDDF_EXECUTION_ROOT when set" {
    mkdir -p "$BATS_TMPDIR/exec-root/openspec/changes/alpha"
    cd "$BATS_TMPDIR/exec-root"
    RDDF_EXECUTION_ROOT="$BATS_TMPDIR/exec-root" \
        run bash -c "source '$PROJECT_ROOT/skills/execute/scripts/select_worktree.sh' && select_execution_root 'alpha'"
    [ "$status" -eq 0 ]
    [ "$output" = "$BATS_TMPDIR/exec-root" ]
}
```

- [ ] **Step 2: Implement `select_execution_root` in `select_worktree.sh`**

Open `skills/execute/scripts/select_worktree.sh`. After the function header comment, add:

```bash
# select_execution_root <change_name>
# Honors $RDDF_EXECUTION_ROOT if set, else falls back to detect_existing_worktree.
select_execution_root() {
    local change_name="$1"
    if [ -n "${RDDF_EXECUTION_ROOT:-}" ]; then
        echo "$RDDF_EXECUTION_ROOT"
        return 0
    fi
    detect_existing_worktree "$change_name"
}
```

- [ ] **Step 3: Export `RDDF_EXECUTION_ROOT` from `setup_execution_workspace`**

In `skills/guide-ship/scripts/ship_plan.sh`, inside `setup_execution_workspace()` (L204), after computing `work_dir`, add:

```bash
  export RDDF_EXECUTION_ROOT="$work_dir"
```

- [ ] **Step 4: Re-run the bats test**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_execute_workspace_root.bats
```

Expected: passes.

- [ ] **Step 5: Update SKILL.md cross-references**

In `skills/guide-ship/SKILL.md` Phase 2 entry, replace the worktree-vs-lightweight confusion paragraph with:

```text
执行环境在 Phase 1 选定,通过 $RDDF_EXECUTION_ROOT 传递给 execute;
execute 不再自行探测工作区。
```

In `skills/execute/SKILL.md`, replace the "always worktree" assumption with:

```text
工作区由 guide-ship 通过 $RDDF_EXECUTION_ROOT 决定;execute 仅消费该变量,不再重新探测。
```

- [ ] **Step 6: Commit**

```bash
git add skills/guide-ship/scripts/ship_plan.sh skills/execute/scripts/select_worktree.sh \
        skills/guide-ship/SKILL.md skills/execute/SKILL.md \
        tests/integration/test_execute_workspace_root.bats
git commit -m "feat(ship): unify execution-root via RDDF_EXECUTION_ROOT"
```

---

## Task 9: Single Aggregate Commit Policy

**Files:**
- Modify: `skills/execute/SKILL.md` (Step 5 commit section)
- Modify: `skills/guide-ship/SKILL.md` (Phase 2.7)
- Modify: `skills/rdd-workflow-writing-plans/SKILL.md` (commit disclaimer)

- [ ] **Step 1: Write a bats test (asserting the docs agree)**

Create `tests/integration/test_commit_policy_docs.bats`:

```bats
#!/usr/bin/env bats

@test "execute SKILL.md states execute defers commits" {
    grep -q 'defers commits\|不提交\|aggregated commit' "$PROJECT_ROOT/skills/execute/SKILL.md"
}

@test "guide-ship SKILL.md requires aggregate commit in Phase 2.7" {
    grep -q 'aggregate commit\|聚合 commit\|worktree.*commit' "$PROJECT_ROOT/skills/guide-ship/SKILL.md"
}

@test "writing-plans SKILL.md defers commits" {
    grep -q 'defer commits\|不提交\|archive' "$PROJECT_ROOT/skills/rdd-workflow-writing-plans/SKILL.md"
}
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_commit_policy_docs.bats
```

Expected: at least one test fails because the wording is inconsistent. Read each file before editing to know the exact phrase.

- [ ] **Step 3: Align the three docs**

In each of the three skill files, ensure the following single sentence appears verbatim in the relevant section:

```text
execute 阶段不逐任务 commit;guide-ship Phase 2.7 在所有任务完成后统一创建一次聚合 commit,然后进入 archive。
```

Place it at the same logical location as the existing commit discussion.

- [ ] **Step 4: Re-run the bats test**

```bash
bats tests/integration/test_commit_policy_docs.bats
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add skills/execute/SKILL.md skills/guide-ship/SKILL.md skills/rdd-workflow-writing-plans/SKILL.md tests/integration/test_commit_policy_docs.bats
git commit -m "docs: align commit policy across ship / execute / writing-plans"
```

---

## Task 10: Plan-Handoff Freshness Warning

**Files:**
- Modify: `skills/guide-plan/scripts/plan_done_gate.py` (`_load_execution_mode_decisions`)

- [ ] **Step 1: Write a unit test (failing)**

Open `tests/unit/test_plan_done_gate.py`. Add a new test:

```python
def test_freshness_warning_when_deps_stale(tmp_path, monkeypatch, capsys):
    """Plan-done emits a warning when deps-analysis is older than the change."""
    from skills.guide_plan.scripts.plan_done_gate import _load_execution_mode_decisions

    # Build a fake iteration.json newer than deps-analysis.json
    import json, datetime
    rd = tmp_path / ".rddf" / "state"
    rd.mkdir(parents=True)
    (rd / "deps-analysis.json").write_text(json.dumps({
        "updated_at": "2026-07-01T00:00:00Z",
        "execution_mode_recommendations": {},
    }))
    (rd / "iteration.json").write_text(json.dumps({
        "updated_at": "2026-08-05T00:00:00Z",
        "changes": [{"name": "alpha", "added_at": "2026-08-04T00:00:00Z", "status": "proposed"}],
    }))
    change = tmp_path / "openspec" / "changes" / "alpha"
    change.mkdir(parents=True)
    (change / "proposal.md").write_text("# P")
    (change / "design.md").write_text("# D")
    (change / "tasks.md").write_text("- [ ] a")
    monkeypatch.chdir(tmp_path)

    _load_execution_mode_decisions(tmp_path)
    out = capsys.readouterr().err
    assert "stale" in out or "older" in out
```

(Adapt the import path to whatever this file actually exposes; check existing tests in `tests/unit/test_plan_done_gate.py`.)

- [ ] **Step 2: Run to verify failure**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_plan_done_gate.py -q --tb=short -k freshness
```

Expected: fails because the warning isn't emitted today.

- [ ] **Step 3: Add the warning emission**

In `skills/guide-plan/scripts/plan_done_gate.py`, inside `_load_execution_mode_decisions`, after loading `deps-analysis.json`, add:

```python
    deps_ts = _iso_to_epoch(deps.get("updated_at"))
    change_ts = _iso_to_epoch(change_meta.get("added_at"))
    if deps_ts and change_ts and deps_ts < change_ts:
        print(f"⚠️  deps-analysis.json 比 change {change_name} 还旧,execution_mode 回退到并行冲突检测", file=sys.stderr)
```

If the helpers `_iso_to_epoch` don't exist, inline:

```python
    from datetime import datetime
    def _iso(ts):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except Exception:
            return None
```

- [ ] **Step 4: Re-run the test**

```bash
python3 -m pytest tests/unit/test_plan_done_gate.py -q --tb=short -k freshness
```

Expected: passes.

- [ ] **Step 5: Commit**

```bash
git add skills/guide-plan/scripts/plan_done_gate.py tests/unit/test_plan_done_gate.py
git commit -m "feat(plan): warn when deps-analysis is older than the change"
```

---

## Task 11: End-to-End Smoke for the New Contract

**Files:**
- Modify: `tests/integration/test_phase_switch.py` (add one new test)
- Or: Create `tests/integration/test_guide_ship_e2e.bats`

- [ ] **Step 1: Write a smoke test that drives `rddf` end-to-end**

Create `tests/integration/test_guide_ship_e2e.bats`:

```bats
#!/usr/bin/env bats

setup() {
    load 'test_helper'
    TEST_REPO="$BATS_TMPDIR/test-e2e"
    rm -rf "$TEST_REPO" && mkdir -p "$TEST_REPO" && cd "$TEST_REPO"
    git init -q && git checkout -q -b main
    mkdir -p openspec/changes/alpha .rddf/state
    echo '# P' > openspec/changes/alpha/proposal.md
    echo '# D' > openspec/changes/alpha/design.md
    printf -- '- [ ] a\n- [ ] b\n' > openspec/changes/alpha/tasks.md
    echo '{}' > .rddf/state/.plan-handoff.json
    echo '{}' > .rddf/state/iteration.json
    git add -A && git commit -q -m 'init'
}

@test "rddf discover-ship-changes reports the alpha candidate" {
    run rddf discover-ship-changes --project-root "$TEST_REPO"
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"name": "alpha"' ]]
}

@test "singleton auto-select surfaces alpha" {
    run bash -c "source '$PROJECT_ROOT/skills/_lib/discover_ship_changes.sh' && ship_top_candidate '$TEST_REPO'"
    [ "$output" = "alpha" ]
}
```

- [ ] **Step 2: Run the smoke test**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_guide_ship_e2e.bats
```

Expected: both pass.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_guide_ship_e2e.bats
git commit -m "test: end-to-end smoke for new guide-ship contract"
```

---

## Task 12: Update AGENTS.md / README Cross-References

**Files:**
- Modify: `AGENTS.md` (Guide section)
- Modify: `README.md` (workflow section)

- [ ] **Step 1: Add a one-paragraph cross-reference**

In `AGENTS.md`, find the section that describes `guide-ship`. Append:

```text
详细执行契约见 docs/superpowers/specs/2026-08-05-guide-ship-execution-contract.md;
tasks.md 是范围, .rddf/plans/<change>.md 是唯一可执行入口, execute 通过 $RDDF_EXECUTION_ROOT 消费 guide-ship 选定的工作区。
```

In `README.md`, find the workflow section and append the same paragraph.

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md README.md
git commit -m "docs: cross-reference guide-ship execution contract"
```

---

## Self-Review Checklist (run after the last task)

- [ ] Spec coverage: each contract claim in Task 1 maps to a code/test task above.
- [ ] No placeholders: every step shows actual commands or code.
- [ ] Type / function consistency: `discover()`, `Candidate`, `ship_candidate_count`, `ship_top_candidate`, `select_execution_root`, `archive_gate_check`, `setup_execution_workspace` are defined exactly once.
- [ ] Bash import: `discover_ship_changes.sh` must be sourced before calling its functions; `ship_archive.sh` must source `_lib/archive.sh`.
- [ ] CI parity: all new bats tests live under `tests/integration/`, all new pytest tests under `tests/unit/`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-05-guide-ship-execution-contract.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session with checkpoints for review.

Which approach do you want?