"""Hub Issue CRUD wrapper (uses existing gh_hub_client)."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from skills._lib.gh_hub_client import GhHubClient


def _get_client() -> GhHubClient:
    """Resolve GhHubClient with default Hub repo."""
    hub_repo = os.environ.get("RDDF_HUB_REPO", "rdd-hub")
    owner, repo = hub_repo.split("/", 1) if "/" in hub_repo else ("my-org", hub_repo)
    return GhHubClient(owner=owner, repo=repo)


def create_hub_issue(dep_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create Hub Issue for a cross-repo dependency."""
    client = _get_client()
    title = dep_info.get("title", "[RFC] cross-repo dependency")
    body = dep_info.get("body", "")
    return client.create_issue(title=title, body=body, labels=["rfc", "cross-repo"])


def find_existing_issue(issues: List[Dict[str, Any]], title_query: str) -> Optional[Dict[str, Any]]:
    """Find existing Hub Issue by title substring match."""
    for issue in issues:
        if title_query.lower() in issue.get("title", "").lower():
            return issue
    return None


def update_hub_issue(issue_number: int, dep_info: Dict[str, Any]) -> Dict[str, Any]:
    """Update Hub Issue status."""
    client = _get_client()
    status = dep_info.get("status", "in_progress")
    return client.hub_update_status(issue_number, status)
