#!/usr/bin/env python3
"""
Sync AC segment from rdd-quick plan to proposal.md for rdd-verifier compatibility.
Per ADR-0048 amendment (2026-09-09): append ## Acceptance (from rdd-quick plan)
segment with BEGIN/END markers. Idempotent.

Usage:
    sync_ac_to_proposal.py --plan <plan.md> --proposal <proposal.md>

Output:
    stdout: <count> ACs synced (one line)
    exit 0: success (with or without ACs)
    exit 2: missing args or file not found

Contract (per .rddf/plans/quick-v2.1-fix-rdd-quick-archive-verifier-gaps.md):
- Parses AC checkboxes from plan's `## Acceptance` section
- Appends segment to proposal.md with explicit BEGIN/END markers
- Idempotent: second call replaces segment (regex match + replace), no duplicates
- Preserves existing proposal.md content above the segment
- Bridges rdd-quick AC source (plan file, per ADR-0047 §D5) and rdd-verifier
  AC source (proposal.md, per rdd-verifier/SKILL.md Step 1)
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

AC_HEADER = "## Acceptance (from rdd-quick plan)"
AC_MARKER_BEGIN = "<!-- BEGIN rdd-quick-ac -->"
AC_MARKER_END = "<!-- END rdd-quick-ac -->"
# Match both `**AC-N** desc` and bare `AC-N desc` checkbox forms
AC_LINE_PATTERN = re.compile(r"^- \[ \]\s*(.+)$")


def parse_acs(plan_path: Path) -> list[str]:
    """Extract AC checkbox items from plan's ## Acceptance section.

    Captures the full checkbox line text (after `- [ ]`) verbatim, including
    any `**AC-N**` markdown emphasis prefix.
    """
    acs = []
    in_acceptance = False
    for line in plan_path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if stripped.startswith("## Acceptance"):
            in_acceptance = True
            continue
        if in_acceptance and stripped.startswith("## ") and not stripped.startswith("## Acceptance"):
            break  # Next H2 section
        if in_acceptance:
            m = AC_LINE_PATTERN.match(line)
            if m:
                acs.append(m.group(1).strip())
    return acs


def build_segment(acs: list[str], plan_name: str) -> str:
    """Build the AC sync segment text."""
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    lines = [
        "",
        AC_HEADER,
        "",
        f"Source: `{plan_name}` :: ## Acceptance",
        f"Generated: {timestamp}",
        "",
        AC_MARKER_BEGIN,
    ]
    for ac in acs:
        lines.append(f"- [ ] {ac}")
    lines.extend([AC_MARKER_END, ""])
    return "\n".join(lines)


def sync(plan_path: Path, proposal_path: Path) -> int:
    """Append or replace AC segment in proposal.md. Returns count of ACs synced."""
    acs = parse_acs(plan_path)
    if not acs:
        print("WARNING: no ACs found in plan", file=sys.stderr)
        return 0
    segment = build_segment(acs, plan_path.name)
    text = proposal_path.read_text(encoding="utf-8")
    # Idempotent: replace existing segment (between BEGIN and END markers)
    pattern = re.compile(
        rf"\n*{re.escape(AC_HEADER)}.*?{re.escape(AC_MARKER_END)}[^\n]*",
        re.DOTALL,
    )
    if AC_MARKER_BEGIN in text:
        # Drop the existing segment, then append fresh one
        new_text = pattern.sub("", text).rstrip() + "\n" + segment
    else:
        new_text = text.rstrip() + "\n" + segment
    proposal_path.write_text(new_text, encoding="utf-8")
    return len(acs)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync AC segment from rdd-quick plan to proposal.md.",
    )
    parser.add_argument("--plan", required=True, type=Path,
                        help="rdd-quick plan file path")
    parser.add_argument("--proposal", required=True, type=Path,
                        help="proposal.md path")
    args = parser.parse_args()
    if not args.plan.exists():
        print(f"ERROR: plan not found: {args.plan}", file=sys.stderr)
        return 2
    if not args.proposal.exists():
        print(f"ERROR: proposal not found: {args.proposal}", file=sys.stderr)
        return 2
    n = sync(args.plan, args.proposal)
    print(f"{n} ACs synced")
    return 0


if __name__ == "__main__":
    sys.exit(main())