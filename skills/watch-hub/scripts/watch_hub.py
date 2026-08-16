#!/usr/bin/env python3
"""rddf watch-hub: One-time poll Hub Issue statuses (designed for cron/CI).

Usage:
  rddf watch-hub --once --owner=<org/hub> [--filter <expr>]

Reads .rddf/state/.cross-repo-pending.json, batch-fetches Hub Issue
statuses via GraphQL. For any Issue that changed to "approved", calls
approve_proposal.sh and updates the pending entry.

Environment:
  RDDF_HUB_REPO       Hub repo (overrides --owner)
  RDDF_WATCH_DRY_RUN  If yes, print plan without network calls
  RDDF_PROJECT_ROOT   Project root (default: cwd)
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "skills", "_lib"))
from skills._lib.gh_hub_client import GhHubClient, RateLimitError
from skills._lib.cross_repo_state import (
    read_pending_state,
    update_pending_entry,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch Hub Issue statuses (one-shot)")
    parser.add_argument("--once", action="store_true", required=True)
    parser.add_argument("--owner", help="<org>/<repo> of Hub")
    parser.add_argument("--filter", help="Filter expression (e.g., 'Stakeholders:[email protected]')")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.once:
        print("ERROR: --once flag required (no long-running daemon supported)", file=sys.stderr)
        return 2

    hub_repo = args.owner or os.environ.get("RDDF_HUB_REPO", "rdd-hub")
    if "/" not in hub_repo:
        print(f"ERROR: Hub repo must be <owner>/<repo>: {hub_repo}", file=sys.stderr)
        return 2

    owner, repo = hub_repo.split("/", 1)
    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    state_dir = os.path.join(project_root, ".rddf", "state")

    state = read_pending_state(state_dir)
    pending = [e for e in state.get("entries", []) if e.get("status") == "pending"]

    if not pending:
        print("[DRY-RUN] No pending RFC entries to poll.")
        return 0

    dry_run = args.dry_run or os.environ.get("RDDF_WATCH_DRY_RUN") == "yes"

    if dry_run:
        print(f"[DRY-RUN] would poll {len(pending)} pending Issues in {hub_repo}:")
        for e in pending:
            print(f"  - {e['hub_issue_url']}")
        return 0

    # Extract issue numbers
    issue_numbers = []
    url_to_number = {}
    for e in pending:
        url = e["hub_issue_url"]
        # parse /issues/<num> from URL
        parts = url.rstrip("/").split("/")
        if "issues" in parts:
            idx = parts.index("issues")
            if idx + 1 < len(parts):
                num = int(parts[idx + 1])
                issue_numbers.append(num)
                url_to_number[url] = num

    if not issue_numbers:
        print("No parseable issue numbers in pending entries.")
        return 0

    client = GhHubClient(owner=owner, repo=repo)
    try:
        statuses = client.batch_get_issues_status(issue_numbers)
    except RateLimitError:
        print("ERROR: Rate limited, skipping this poll.", file=sys.stderr)
        return 3

    # Index by number
    by_number = {s["number"]: s for s in statuses}

    approved_count = 0
    for e in pending:
        url = e["hub_issue_url"]
        num = url_to_number.get(url)
        if not num or num not in by_number:
            continue
        s = by_number[num]
        if s["state"] == "closed" and s.get("stateReason") == "COMPLETED":
            # Approve locally
            subprocess.run([
                "bash", "scripts/approve_proposal.sh",
                f"hub-{num}", e["gate_type"], "watch-hub-bot", "auto-approved via watch-hub"
            ], check=False)
            update_pending_entry(state_dir, url, {"status": "approved"})
            approved_count += 1

    print(f"Polled {len(pending)} entries; approved {approved_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
