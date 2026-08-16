#!/usr/bin/env python3
"""rddf sync-hub: Pull contract files from Hub repo to local openspec/.

Usage:
  rddf sync-hub --contract <path>

Environment:
  RDDF_HUB_REPO        Hub repo (e.g., my-org/rdd-hub). Default: rdd-hub.
  RDDF_SYNC_DRY_RUN    If yes, print plan without network calls.
  RDDF_PROJECT_ROOT    Local project root (default: cwd).

Side effect:
  Downloads <contract> from Hub contracts/ to openspec/specs/<contract>/spec.md
"""
import argparse
import base64
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "skills", "_lib"))
from skills._lib.gh_hub_client import GhHubClient, RateLimitError


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync contract from Hub")
    parser.add_argument("--contract", required=True, help="Contract path in Hub contracts/")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    hub_repo = os.environ.get("RDDF_HUB_REPO", "rdd-hub")
    if "/" not in hub_repo:
        print(f"ERROR: RDDF_HUB_REPO must be <owner>/<repo>: {hub_repo}", file=sys.stderr)
        return 2

    owner, repo = hub_repo.split("/", 1)
    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    contract_name = args.contract.replace(".yaml", "").replace(".yml", "")
    target_path = os.path.join(
        project_root, "openspec", "specs", contract_name, "spec.md"
    )

    dry_run = args.dry_run or os.environ.get("RDDF_SYNC_DRY_RUN") == "yes"

    if dry_run:
        print(f"[DRY-RUN] would download:")
        print(f"  From: https://raw.githubusercontent.com/{owner}/{repo}/main/contracts/{args.contract}")
        print(f"  To:   {target_path}")
        return 0

    try:
        result = subprocess.run([
            "gh", "api",
            f"repos/{owner}/{repo}/contents/contracts/{args.contract}",
        ], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        content = base64.b64decode(data["content"]).decode("utf-8")
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w") as f:
            f.write(content)
        print(f"Synced {args.contract} -> {target_path}")
        return 0
    except subprocess.CalledProcessError as e:
        if "rate limit" in (e.stderr or "").lower():
            print(f"ERROR: Rate limited. Using cache if available.", file=sys.stderr)
            return 3
        if "404" in (e.stderr or ""):
            print(f"ERROR: Contract {args.contract} not found in Hub", file=sys.stderr)
            return 4
        raise


if __name__ == "__main__":
    sys.exit(main())
