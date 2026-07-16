"""Generate deps-candidates.json (ADR-0016 Layer 2 contract).

Extracted from skills/guide-plan.md L451-L488.
Original code used python3 -c with $PROJECT_ROOT string interpolation
— Oracle C1 vulnerable. This module uses os.environ instead.
"""
import json
import os
import subprocess
from typing import List


def generate_deps_candidates(project_root: str) -> dict:
    """Build .rddf/state/.deps-candidates.json. Returns the dict.

    Reads all committed changes from openspec/changes/*/ and lists them
    in the candidates field. Only includes changes whose .openspec.yaml
    is committed to HEAD (per 'git show HEAD:' check).

    Args:
        project_root: Absolute path to project root.

    Returns:
        Dict with 'candidates' key (sorted list of change names).
    """
    changes_dir = os.path.join(project_root, "openspec", "changes")
    candidates: List[str] = []

    if os.path.isdir(changes_dir):
        for name in sorted(os.listdir(changes_dir)):
            # Only include changes committed to HEAD
            try:
                result = subprocess.run(
                    ["git", "show", f"HEAD:openspec/changes/{name}/.openspec.yaml"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    candidates.append(name)
            except (FileNotFoundError, subprocess.SubprocessError):
                # If git not available or change has issues, skip silently
                pass

    data = {"candidates": candidates}

    # Write to .rddf/state/.deps-candidates.json
    state_dir = os.path.join(project_root, ".rddf", "state")
    os.makedirs(state_dir, exist_ok=True)
    output_path = os.path.join(state_dir, ".deps-candidates.json")
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"生成候选列表: {candidates}")
    return data
