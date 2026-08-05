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


def _disk_candidates(project_root: Path) -> dict:
    changes_dir = project_root / "openspec" / "changes"
    out: dict = {}
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


def _handoff_candidates(project_root: Path) -> dict:
    handoff = _read_json(project_root / ".rddf" / "state" / ".plan-handoff.json")
    out: dict = {}
    for name in handoff.get("committed_changes", []) or []:
        out.setdefault(name, Candidate(name=name))
    cur = handoff.get("current_change")
    if cur:
        out.setdefault(cur, Candidate(name=cur))
    return out


def _iteration_candidates(project_root: Path) -> dict:
    data = _read_json(project_root / ".rddf" / "state" / "iteration.json")
    out: dict = {}
    for entry in data.get("changes", []) or []:
        status = entry.get("status")
        if status == "archived":
            continue
        cand = out.setdefault(entry["name"], Candidate(name=entry["name"]))
        cand.iteration_status = status
    return out


def _git_candidates(project_root: Path) -> dict:
    out: dict = {}
    # branches
    try:
        branches = subprocess.run(
            ["git", "branch", "--list", "openspec/*"],
            cwd=project_root, capture_output=True, text=True, check=True,
        ).stdout.splitlines()
    except subprocess.CalledProcessError:
        branches = []
    for line in branches:
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
    if cand.iteration_status is None and cand.filesystem_present:
        cand.flags.append("needs_reconciliation")
    if cand.worktree or cand.branch:
        cand.flags.append("in_progress" if cand.tasks_total - cand.tasks_done > 0 else "ready_to_archive")
    elif cand.filesystem_present and cand.artifact_complete:
        cand.flags.append("executable")
    else:
        cand.flags.append("needs_planning")


def discover(project_root) -> List[Candidate]:
    root = Path(project_root)
    union: dict = {}
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
    decorated = []
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