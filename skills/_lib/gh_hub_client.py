"""GitHub Hub API client (REST + GraphQL via gh CLI).

Provides high-level operations for cross-repo federation: create RFC issues,
poll issue status, batch query via GraphQL. All operations respect GitHub
API rate limits (raises RateLimitError when exhausted).
"""
from __future__ import annotations

import json
import subprocess
from typing import List, Optional


class RateLimitError(Exception):
    """Raised when GitHub API rate limit is hit (403 + retry-after)."""


class GhHubClient:
    """Thin wrapper around `gh` CLI for Hub operations."""

    def __init__(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo

    def _run(self, args: List[str], input_data: Optional[str] = None) -> dict:
        """Run gh CLI command and return parsed JSON output."""
        cmd = ["gh"] + args
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, input=input_data
            )
        except FileNotFoundError:
            raise RuntimeError("gh CLI not installed. Install from https://cli.github.com/")
        if result.returncode != 0:
            stderr = result.stderr or ""
            if "rate limit" in stderr.lower() or "403" in stderr:
                raise RateLimitError(f"GitHub API rate limit: {stderr}")
            raise RuntimeError(f"gh command failed: {stderr}")
        if result.stdout.strip():
            return json.loads(result.stdout)
        return {}

    def create_issue(
        self, title: str, body: str, labels: Optional[List[str]] = None
    ) -> dict:
        """Create a new issue in the Hub repo. Returns dict with number + html_url."""
        args = [
            "issue", "create",
            "--repo", f"{self.owner}/{self.repo}",
            "--title", title,
            "--body", body,
            "--json", "number,html_url",
        ]
        if labels:
            for label in labels:
                args.extend(["--label", label])
        return self._run(args)

    def get_issue_status(self, issue_number: int) -> dict:
        """Get status (state, state_reason, title) of a single issue."""
        return self._run([
            "issue", "view", str(issue_number),
            "--repo", f"{self.owner}/{self.repo}",
            "--json", "number,state,state_reason,title",
        ])

    def batch_get_issues_status(self, issue_numbers: List[int]) -> List[dict]:
        """Batch-fetch issue statuses via GraphQL (more efficient than N REST calls)."""
        if not issue_numbers:
            return []
        numbers_str = ",".join(str(n) for n in issue_numbers)
        query = f"""
        query {{ repository(owner: "{self.owner}", name: "{self.repo}") {{
            issues(first: {len(issue_numbers)}, filterBy: {{ numbers: [{numbers_str}] }}) {{
                nodes {{ number state stateReason title }}
            }}
        }} }}
        """
        result = self._run(["api", "graphql", "-f", f"query={query}"])
        nodes = (
            result.get("data", {}).get("repository", {}).get("issues", {}).get("nodes", [])
        )
        return nodes
