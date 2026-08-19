#!/usr/bin/env python3
"""rddf report-issue --category=rfc: Create Hub RFC Issue.

Usage:
  rddf report-issue --category=rfc \\
    --title "[RFC] <title>" \\
    --stakeholders "<org/repo1>,<org/repo2>" \\
    --gate "<Design-Gate|Arch-Gate|Ship-Gate>" \\
    --contract-impact "<Low|Medium|High|Critical>"

Environment:
  RDDF_REPORT_GH_REPO   Hub repo (e.g., my-org/rdd-hub). Required.
  RDDF_REPORT_DRY_RUN   If yes, print plan without creating Issue.

Side effect:
  Appends entry to .rddf/state/.cross-repo-pending.json (in CWD or
  RDDF_PROJECT_ROOT).
"""
import argparse
import os
import sys
from datetime import datetime, timezone

# Ensure _lib importable (shim will handle global install path)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "skills", "_lib"))

from skills._lib.gh_hub_client import GhHubClient, RateLimitError
from skills._lib.cross_repo_state import add_pending_entry


def build_contract_draft_block(path: str) -> str:
    """Read contract file at <path>, base64-encode, return markdown details block.

    Limit: 49152 bytes (~48 KB). Larger files rejected with ValueError.
    """
    from pathlib import Path
    import base64
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"contract draft file not found: {path}")
    raw = p.read_bytes()
    if len(raw) > 49152:
        raise ValueError(
            f"contract draft too large ({len(raw)} bytes; max 49152). "
            "Hub Issue body limit is ~65536 chars (~48 KB base64)."
        )
    encoded = base64.b64encode(raw).decode("ascii")
    return (
        f"\n\n<details><summary>Contract draft ({path}, {len(raw)} bytes, base64)</summary>\n\n"
        f"```\n{encoded}\n```\n\n</details>"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Hub RFC Issue")
    parser.add_argument("--category", required=True, choices=["rfc"])
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", default="")
    parser.add_argument("--stakeholders", default="")
    parser.add_argument("--gate", default="Design-Gate")
    parser.add_argument("--contract-impact", default="Medium")
    parser.add_argument("--contract-draft", default="",
                        help="Path to contract draft file; base64-inlined into Hub Issue body as <details>")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    gh_repo = os.environ.get("RDDF_REPORT_GH_REPO")
    if not gh_repo:
        print("ERROR: RDDF_REPORT_GH_REPO env var required", file=sys.stderr)
        return 2

    if "/" not in gh_repo:
        print(f"ERROR: RDDF_REPORT_GH_REPO must be <owner>/<repo>, got: {gh_repo}", file=sys.stderr)
        return 2

    owner, repo = gh_repo.split("/", 1)
    body_parts = [args.body or f"Auto-generated RFC from rddf report-issue."]
    if args.stakeholders:
        body_parts.append(f"\n**Stakeholders**: {args.stakeholders}")
    if args.gate:
        body_parts.append(f"**Gate**: {args.gate}")
    if args.contract_impact:
        body_parts.append(f"\n**Contract Impact**: {args.contract_impact}")

    # Inline base64 contract draft if provided
    if args.contract_draft:
        try:
            contract_block = build_contract_draft_block(args.contract_draft)
            body_parts.append(contract_block)
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 4
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 4

    body = "\n".join(body_parts)

    dry_run = args.dry_run or os.environ.get("RDDF_REPORT_DRY_RUN") == "yes"

    if dry_run:
        print(f"[DRY-RUN] would create Issue in {gh_repo}:")
        print(f"  Title: {args.title}")
        print(f"  Labels: rfc,cross-repo")
        print(f"  Body:\n{body}")
        return 0

    client = GhHubClient(owner=owner, repo=repo)
    try:
        result = client.create_issue(
            title=args.title,
            body=body,
            labels=["rfc", "cross-repo"],
        )
    except RateLimitError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3

    # Record pending entry
    project_root = os.environ.get("RDDF_PROJECT_ROOT", os.getcwd())
    state_dir = os.path.join(project_root, ".rddf", "state")
    os.makedirs(state_dir, exist_ok=True)
    add_pending_entry(
        state_dir,
        {
            "hub_issue_url": result["html_url"],
            "gate_type": args.gate,
            "expected_status": "approved",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "title": args.title,
            "stakeholders": args.stakeholders,
            "contract_impact": args.contract_impact,
        },
    )

    print(f"Issue created: {result['html_url']}")
    print(f"   Pending entry recorded in .rddf/state/.cross-repo-pending.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
