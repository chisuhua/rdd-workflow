"""Design-done gate integration for Hub RFC pending checks.

Provides check_hub_pending() which queries .rddf/state/.cross-repo-pending.json
and returns True (block) if any pending RFC entries exist.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def check_hub_pending() -> bool:
    """Check if any Hub RFC Issues are still pending.

    Returns:
        True if there are pending RFC Issues (gate should BLOCK).
        False if all approved or no pending entries.
    """
    if os.environ.get("SKIP_HUB_CHECK", "").lower() == "true":
        return False

    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    state_dir = os.path.join(project_root, ".rddf", "state")
    pending_file = os.path.join(state_dir, ".cross-repo-pending.json")

    if not os.path.exists(pending_file):
        return False

    try:
        state = json.loads(open(pending_file).read())
    except (json.JSONDecodeError, OSError):
        return False

    return any(e.get("status") == "pending" for e in state.get("entries", []))


def check_cross_repo_approvals() -> bool:
    """Check if all cross-repo-federation proposals have audit log approvals.

    Returns True if any cross-repo proposal lacks a corresponding 'approved'
    entry in .rddf/state/.cross-repo-audit.jsonl (gate should BLOCK).
    """
    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    changes_dir = os.path.join(project_root, "openspec", "changes")
    if not os.path.isdir(changes_dir):
        return False

    audit_file = os.path.join(project_root, ".rddf", "state", ".cross-repo-audit.jsonl")
    approved_proposals = set()
    if os.path.exists(audit_file):
        for line in open(audit_file):
            try:
                record = json.loads(line)
                if record.get("decision") in ("approve", "approved"):
                    approved_proposals.add(record.get("proposal_name"))
            except (json.JSONDecodeError, KeyError):
                continue

    pending = []
    for entry in os.listdir(changes_dir):
        meta = os.path.join(changes_dir, entry, "roadmap-meta.yaml")
        if not os.path.isfile(meta):
            continue
        with open(meta) as f:
            for line in f:
                if line.startswith("category:"):
                    cat = line.split(":", 1)[1].strip().strip("'\"")
                    if cat == "cross-repo-federation" and entry not in approved_proposals:
                        pending.append(entry)
                    break

    return len(pending) > 0


_COMMANDS = {
    "check-hub-pending": check_hub_pending,
    "check-cross-repo-approvals": check_cross_repo_approvals,
}


def main(argv: list[str] | None = None) -> int:
    """CLI entry: `python3 design_done_gate.py <command>`.

    Exit 0 = pass (no block), 1 = block, 2 = usage error.
    Used by check_design_done_gate() in skills/guide-design/SKILL.md Phase 4.
    """
    import sys

    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in _COMMANDS:
        print(f"usage: design_done_gate.py <{'|'.join(_COMMANDS)}>", file=sys.stderr)
        return 2
    return 1 if _COMMANDS[args[0]]() else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
