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
        """Create a new issue in the Hub repo. Returns dict with number + html_url.

        gh CLI <2.50 does not support `--json` on `issue create`. We rely on
        stdout URL output ("https://github.com/<owner>/<repo>/issues/<N>")
        and tolerate label-creation warnings that don't abort the issue.
        """
        args = [
            "issue", "create",
            "--repo", f"{self.owner}/{self.repo}",
            "--title", title,
            "--body", body,
        ]
        if labels:
            for label in labels:
                args.extend(["--label", label])

        try:
            result = subprocess.run(
                ["gh"] + args, capture_output=True, text=True, check=False
            )
        except FileNotFoundError:
            raise RuntimeError("gh CLI not installed. Install from https://cli.github.com/")

        stderr = result.stderr or ""
        stdout = (result.stdout or "").strip()

        if result.returncode != 0 and "could not add label" not in stderr:
            if "rate limit" in stderr.lower() or "403" in stderr:
                raise RateLimitError(f"GitHub API rate limit: {stderr}")
            raise RuntimeError(f"gh command failed: {stderr}")

        # Try JSON parse (future gh CLI / unit-test mocks)
        try:
            data = json.loads(stdout)
            if isinstance(data, dict) and "number" in data:
                return {
                    "number": int(data["number"]),
                    "html_url": data.get("html_url") or data.get("url") or "",
                }
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: parse URL from stdout
        import re
        m = re.search(r'https?://github\.com/[^/\s]+/[^/\s]+/issues/(\d+)', stdout)
        if m:
            return {"number": int(m.group(1)), "html_url": m.group(0)}

        raise RuntimeError(
            f"Could not parse issue URL from gh output: stdout={stdout!r} stderr={stderr!r}"
        )

    def get_issue_status(self, issue_number: int) -> dict:
        """Get status (state, stateReason, title) of a single issue."""
        return self._run([
            "issue", "view", str(issue_number),
            "--repo", f"{self.owner}/{self.repo}",
            "--json", "number,state,stateReason,title",
        ])

    def batch_get_issues_status(self, issue_numbers: List[int]) -> List[dict]:
        """Batch-fetch issue statuses. Falls back to N REST calls because GitHub
        GraphQL IssueFilters does not accept a `numbers` argument; we resolve
        each issue by number via `issue view` for reliability.
        """
        results = []
        for num in issue_numbers:
            try:
                results.append(self.get_issue_status(num))
            except RuntimeError:
                continue
        return results
