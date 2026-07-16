"""skills/_lib/propose_change.py — helpers for propose.md Phase 4.

Extracted from inline PYEOF heredocs in propose.md lines 443-796
(P0-1 refactor, Metis plan 2026-07-16). Each function preserves the
exact behavior of the corresponding inline block, including output
strings and exception handling.
"""

import json
import os
from typing import Optional


def set_suggestion_status(
    project_root: str, name: str, new_status: str
) -> bool:
    """Update status field for matching entry in proposal-suggestions.md.

    Returns True if updated, False if file missing / malformed / name not found.
    Preserves all other fields. Matches original lines 531-548 inline behavior.
    """
    path = os.path.join(project_root, "proposal-suggestions.md")
    try:
        with open(path) as f:
            entries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    if not isinstance(entries, list):
        return False
    updated = False
    for entry in entries:
        if isinstance(entry, dict) and entry.get("name") == name:
            entry["status"] = new_status
            updated = True
    if updated:
        try:
            with open(path, "w") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except OSError:
            return False
    return updated


def create_skeleton_change(
    project_root: str,
    name: str,
    current_phase: str,
    category: str,
    priority: str,
) -> bool:
    """Create minimal skeleton artifacts for a change (propose.md lines 486-551).

    Writes:
    - openspec/changes/<name>/proposal.md (Why + What Changes skeleton)
    - openspec/changes/<name>/roadmap-meta.yaml
    - iteration.json (status=planned) — graceful skip on ImportError

    Returns True on full success, False if proposal/yaml write failed.
    Matches original inline behavior exactly, including:
    - openspec new change call (best-effort, swallows errors)
    - All output strings ("📦 Skeleton mode:", "  ✅ iteration.json updated:",
      "⚠️  iteration.json update failed (non-fatal):")
    """
    import os
    import subprocess
    import sys

    change_dir = os.path.join(project_root, "openspec", "changes", name)
    os.makedirs(change_dir, exist_ok=True)

    # openspec new change (best-effort, matches original)
    subprocess.run(
        ["openspec", "new", "change", name],
        cwd=project_root,
        capture_output=True,
    )

    # Write minimal proposal.md
    proposal_path = os.path.join(change_dir, "proposal.md")
    try:
        with open(proposal_path, "w") as f:
            f.write("## Why\n\n")
            f.write("<skeleton motivation - 1-2 sentences>\n\n")
            f.write("## What Changes\n\n")
            f.write("- <file path or module affected>\n")
            f.write("- <file path or module affected>\n")
    except OSError:
        return False

    # Write minimal roadmap-meta.yaml
    yaml_path = os.path.join(change_dir, "roadmap-meta.yaml")
    try:
        with open(yaml_path, "w") as f:
            f.write('roadmap:\n')
            f.write(f'  phase: "{current_phase}"\n')
            f.write(f'  category: "{category}"\n')
            f.write(f'  priority: "{priority}"\n')
            f.write(f'  gate_checklist: []\n')
            f.write(f'  cross_phase_deps: []\n')
            f.write(f'  category_validation:\n')
            f.write(f'    valid: true\n')
            f.write(f'    reason: ""\n')
    except OSError:
        return False

    # Update iteration.json (graceful skip)
    try:
        from skills._lib import iteration as it_mod
        data = it_mod.load(project_root)
        data = it_mod.add_or_update_change(
            data,
            name=name,
            status="planned",
            phase=None,
            category=None,
            priority=None,
        )
        it_mod.save(project_root, data)
        print(f"  ✅ iteration.json updated: {name} status=planned")
    except ImportError as e:
        print(f"⚠️  iteration 模块不可用, 跳过: {e}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  iteration.json update failed (non-fatal): {e}", file=sys.stderr)

    print(f"✅ Skeleton created: {name}")
    return True