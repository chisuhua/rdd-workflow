#!/usr/bin/env python3
"""Detect cross-repo impact of a proposal against Hub contracts.

Usage:
  python3 detect_cross_repo_impact.py \
    --proposal .rddf/improvements/<name>.md \
    --hub-repo chisuhua/rdd-hub \
    --output .rddf/state/.cross-repo-detection-<name>.json

Behavior:
- Skips silently when RDDF_SKIP_CROSS_REPO_DETECTION=yes (or =true)
- Reads proposal body (skips head fields + frontmatter)
- Fetches Hub contracts/ via `gh api`
- For each contract: matches filename + keywords against body, parses
  x-owners, builds match report
- Writes JSON report to --output (atomic write)
- Prints human-readable warnings to stderr if matches found
- Failures are silent (no exception bubbling into add-improve)

Output JSON schema:
{
  "version": 1,
  "proposal_name": "<name>",
  "hub_repo": "org/repo",
  "created_at": "2026-08-19T...",
  "matches": [
    {
      "contract_name": "auth-v2.yaml",
      "contract_path": "contracts/auth-v2.yaml",
      "owners": ["org/repo-a", "org/repo-b"],
      "matched_keywords": ["auth", "v2"],
    }
  ],
  "suggested_stakeholders": ["org/repo-a", "org/repo-b"],
  "suggested_category": "cross-repo-federation"
}

Exit codes:
- 0: completed (with or without matches)
- 1: invalid args / file not found / schema violation
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SKIP_ENV_VARS = {"yes", "true", "1", "on"}


def extract_body(text: str) -> str:
    """Extract proposal body, skipping head fields and frontmatter.

    - Strips YAML frontmatter (between --- markers at file start)
    - Strips head fields (first 8 lines matching `**key**: value` pattern)
    - Returns remaining body for matching
    """
    lines = text.splitlines()
    out = []
    in_frontmatter = False
    frontmatter_seen = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if i == 0 and stripped == "---":
            in_frontmatter = True
            frontmatter_seen = True
            continue
        if in_frontmatter and stripped == "---":
            in_frontmatter = False
            continue
        if in_frontmatter:
            continue
        if i < 8 and re.match(r"^\*\*[^*]+\*\*\s*:", stripped):
            continue
        out.append(line)
    return "\n".join(out)


def body_matches(body: str, keywords: list) -> list:
    """Return subset of keywords that appear as substring in body (case-insensitive).

    Uses substring matching (not word boundary) for higher recall on technical
    identifiers like 'auth-v2.yaml' which may appear in prose as 'auth-v2 is good'
    or 'authenticator' (substring of 'auth'). False positives are acceptable for
    the suggestion layer (human review will filter).
    """
    body_lower = body.lower()
    found = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in body_lower:
            found.append(kw)
    return found


def detect(proposal_path: str, hub_repo: str) -> dict:
    """Run detection. Returns report dict. Network failures yield empty matches."""
    # Local import to avoid path issues when run from anywhere
    sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
    from hub_contract_metadata import (
        list_hub_contracts,
        fetch_contract_content,
        parse_x_owners,
        extract_match_keywords,
    )

    text = Path(proposal_path).read_text(encoding="utf-8", errors="replace")
    body = extract_body(text)
    proposal_name = Path(proposal_path).stem

    contracts = list_hub_contracts(hub_repo)

    matches = []
    all_owners = []

    for c in contracts:
        keywords = extract_match_keywords(c["name"])
        matched = body_matches(body, keywords)
        if not matched:
            continue

        owners = []
        content = fetch_contract_content(hub_repo, c["path"], c["sha"])
        if content:
            owners = parse_x_owners(content)
        for o in owners:
            if o not in all_owners:
                all_owners.append(o)

        matches.append({
            "contract_name": c["name"],
            "contract_path": c["path"],
            "owners": owners,
            "matched_keywords": matched,
        })

    report = {
        "version": 1,
        "proposal_name": proposal_name,
        "hub_repo": hub_repo,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "matches": matches,
        "suggested_stakeholders": all_owners,
        "suggested_category": "cross-repo-federation" if matches else None,
    }
    return report


def write_report_atomic(report: dict, output_path: str) -> None:
    """Atomic write: temp file + rename. Mirrors cross_repo_state pattern."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".cross-repo-detection-",
        suffix=".tmp",
        dir=str(out.parent),
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(report, f, indent=2)
        os.replace(tmp_path, output_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def print_warnings(report: dict, proposal_path: str) -> None:
    """Print human-readable warnings to stderr. No-op if no matches."""
    matches = report.get("matches", [])
    if not matches:
        return

    print(f"\n⚠️  Cross-repo impact detected for {report['proposal_name']}", file=sys.stderr)
    print(f"   Proposal: {proposal_path}", file=sys.stderr)
    print(f"   Hub:      {report['hub_repo']}", file=sys.stderr)
    print("", file=sys.stderr)
    for m in matches:
        print(f"   Match:    {m['contract_name']} (keywords: {', '.join(m['matched_keywords'])})", file=sys.stderr)
        if m["owners"]:
            print(f"   Owners:   {', '.join(m['owners'])}", file=sys.stderr)
        else:
            print(f"   Owners:   (no x-owners annotation)", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"   Suggested category: cross-repo-federation", file=sys.stderr)
    if report.get("suggested_stakeholders"):
        print(f"   Suggested stakeholders: {', '.join(report['suggested_stakeholders'])}", file=sys.stderr)
    print("", file=sys.stderr)
    print("   Run `rddf rfc-draft <name>` after proposal approval to generate RFC content.", file=sys.stderr)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Detect cross-repo impact of a proposal against Hub contracts.")
    parser.add_argument("--proposal", required=True, help="Path to .rddf/improvements/<name>.md")
    parser.add_argument("--hub-repo", required=True, help="Hub repo <owner>/<name>")
    parser.add_argument("--output", required=True, help="Path to write detection report JSON")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without side effects")
    args = parser.parse_args(argv)

    # Opt-out check
    skip_env = os.environ.get("RDDF_SKIP_CROSS_REPO_DETECTION", "").lower()
    if skip_env in SKIP_ENV_VARS:
        return 0

    # Validate proposal exists
    if not Path(args.proposal).is_file():
        print(f"ERROR: proposal file not found: {args.proposal}", file=sys.stderr)
        return 1

    # Validate hub-repo format
    if "/" not in args.hub_repo:
        print(f"ERROR: --hub-repo must be <owner>/<name>: {args.hub_repo}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"[DRY-RUN] would scan {args.proposal} against Hub {args.hub_repo}", file=sys.stderr)
        print(f"[DRY-RUN] would write report to {args.output}", file=sys.stderr)
        return 0

    try:
        report = detect(args.proposal, args.hub_repo)
    except Exception as e:
        # Silent failure: log to stderr but don't fail add-improve
        print(f"⚠️  detect_cross_repo_impact failed (silent): {e}", file=sys.stderr)
        return 0

    try:
        write_report_atomic(report, args.output)
    except OSError as e:
        print(f"⚠️  failed to write report: {e}", file=sys.stderr)
        return 0

    print_warnings(report, args.proposal)
    return 0


if __name__ == "__main__":
    sys.exit(main())