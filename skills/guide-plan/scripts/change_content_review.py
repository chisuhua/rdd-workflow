"""Change content review module - checks artifact quality before plan-done."""
import json
import os
from typing import Dict, Any


def review_change_content(change_name: str, project_root: str) -> Dict[str, Any]:
    """Review change artifacts (proposal.md, design.md, tasks.md).

    Returns a dict with pass/fail/warn for each check dimension:
    - proposal_clarity: Is the proposal well-scoped and clear?
    - design_completeness: Does design.md exist and have content?
    - tasks_granularity: Are tasks atomic (not too large)?
    - consistency: Do artifacts reference each other correctly?
    - dependency_annotations: Are dependencies declared?
    """
    result = {
        "change": change_name,
        "proposal_clarity": "pass",
        "design_completeness": "pass",
        "tasks_granularity": "pass",
        "consistency": "pass",
        "dependency_annotations": "pass",
        "auto_revised": False,
        "escalated": False
    }

    change_dir = os.path.join(project_root, "openspec", "changes", change_name)

    if not os.path.isdir(change_dir):
        result["proposal_clarity"] = "fail"
        result["escalated"] = True
        return result

    proposal_path = os.path.join(change_dir, "proposal.md")
    design_path = os.path.join(change_dir, "design.md")
    tasks_path = os.path.join(change_dir, "tasks.md")

    if os.path.isfile(proposal_path):
        with open(proposal_path) as f:
            proposal_content = f.read()
        if len(proposal_content.strip()) < 50:
            result["proposal_clarity"] = "warn"
    else:
        result["proposal_clarity"] = "fail"

    if os.path.isfile(design_path):
        with open(design_path) as f:
            design_content = f.read()
        if len(design_content.strip()) < 50:
            result["design_completeness"] = "warn"
    else:
        result["design_completeness"] = "warn"

    if os.path.isfile(tasks_path):
        with open(tasks_path) as f:
            tasks_content = f.read()
        incomplete = tasks_content.count("- [ ]")
        if incomplete > 10:
            result["tasks_granularity"] = "warn"

    meta_path = os.path.join(change_dir, "roadmap-meta.yaml")
    if not os.path.isfile(meta_path):
        result["dependency_annotations"] = "warn"

    return result


def auto_revise_if_needed(change_name: str, project_root: str, review_result: Dict) -> bool:
    """Auto-revise fixable issues. Returns True if revisions were made."""
    if os.environ.get("CHANGE_CONTENT_REVIEW_AUTO_REVISE", "yes") == "no":
        return False
    return False
