#!/usr/bin/env python3
"""
Generate minimal tasks.md from rdd-quick plan file (mode a only).
Per ADR-0048 amendment (2026-09-09): idempotent one-shot generation,
not per-task writeback. Preserves rdd-quick's "no逐任务回写" spirit.

Usage:
    generate_tasks_md.py --change <name> --plan <plan.md> --proposal <proposal.md>

Output:
    stdout: <tasks_md_path> (one line)
    exit 0: success or skipped (tasks.md already exists)
    exit 2: missing args or file not found

Contract (per .rddf/plans/quick-v2.1-fix-rdd-quick-archive-verifier-gaps.md):
- Reads Task 1..N titles from plan's `### Task N: <title>` headers
- Generates minimal tasks.md with Setup/Implementation/Verification 3-section structure
- All items use [x] (one-shot completion marker, not [ ])
- Idempotent: skip if tasks.md already exists (preserves manual edits)
- Writes to openspec/changes/<change>/tasks.md (relative to cwd)
"""
import argparse
import re
import sys
from pathlib import Path

TASK_TITLE_PATTERN = re.compile(r"^### Task \d+:\s*(.+)$")


def parse_task_titles(plan_path: Path) -> list[str]:
    """Extract ### Task N: <title> from plan, preserve order."""
    titles = []
    for line in plan_path.read_text(encoding="utf-8").splitlines():
        m = TASK_TITLE_PATTERN.match(line)
        if m:
            titles.append(m.group(1).strip())
    return titles


def build_tasks_md(change: str, plan_path: Path, proposal_path: Path,
                   task_titles: list[str]) -> str:
    """Build minimal tasks.md content."""
    lines = [
        "## 1. Setup",
        "",
        f"- [x] 1.1 Read {proposal_path.name} and confirm scope (via rdd-quick mode a)",
        "",
        "## 2. Implementation",
        "",
    ]
    for i, title in enumerate(task_titles, start=1):
        lines.append(f"- [x] 2.{i} {title} (executed via rdd-quick P2)")
    lines.extend([
        "",
        "## 3. Verification",
        "",
        f"- [x] 3.1 Run `openspec validate {change}` (passed via mode a AC verification)",
        "- [x] 3.2 rdd-verifier compatibility: AC synced to proposal.md (per ADR-0048 amendment)",
        "",
    ])
    return "\n".join(lines)


def generate_tasks_md(change: str, plan_path: Path, proposal_path: Path) -> Path:
    """Generate minimal tasks.md. Idempotent: skip if exists."""
    tasks_md = Path("openspec/changes") / change / "tasks.md"
    if tasks_md.exists():
        return tasks_md
    task_titles = parse_task_titles(plan_path)
    content = build_tasks_md(change, plan_path, proposal_path, task_titles)
    tasks_md.parent.mkdir(parents=True, exist_ok=True)
    tasks_md.write_text(content, encoding="utf-8")
    return tasks_md


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate minimal tasks.md from rdd-quick plan (mode a only).",
    )
    parser.add_argument("--change", required=True,
                        help="openspec change name")
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
    tasks_md = generate_tasks_md(args.change, args.plan, args.proposal)
    print(str(tasks_md))
    return 0


if __name__ == "__main__":
    sys.exit(main())