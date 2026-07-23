#!/usr/bin/env python3
"""Helper for archive operations with change_type awareness."""
import os
import json
import re
from pathlib import Path
from typing import Optional, Literal

ChangeType = Literal["test-only", "doc-only", "refactor-only", "feature", "debt"]


def get_change_type(project_root: str, change_name: str) -> ChangeType:
    """Get change type from proposal-suggestions.md or infer from proposal.md."""
    suggestions_path = Path(project_root) / "proposal-suggestions.md"
    
    # Try to read from suggestions
    if suggestions_path.exists():
        try:
            with open(suggestions_path) as f:
                entries = json.load(f)
            for e in entries:
                if e.get("name") == change_name:
                    return e.get("change_type", "feature")
        except:
            pass
    
    # Try to infer from proposal.md
    proposal_path = Path(project_root) / "openspec/changes" / change_name / "proposal.md"
    if proposal_path.exists():
        try:
            with open(proposal_path) as f:
                content = f.read()
            
            # Import infer function
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / "propose" / "scripts"))
            from infer_change_type import infer_change_type
            
            return infer_change_type(content, change_name)
        except:
            pass
    
    return "feature"


def should_skip_delta_check(change_type: ChangeType) -> bool:
    """Return True if change type should skip delta checks."""
    return change_type in ("test-only", "doc-only", "refactor-only")


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        project_root = sys.argv[1]
        change_name = sys.argv[2]
        ct = get_change_type(project_root, change_name)
        skip = should_skip_delta_check(ct)
        print(f"change_type={ct}")
        print(f"skip_delta_check={skip}")
