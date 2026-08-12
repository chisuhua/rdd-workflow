"""``rddf issue`` subcommand group: submit / list / show local issues.

Subcommands:
    rddf issue submit <file>    Submit a local .rddf/issues/<file>.md to GitHub
    rddf issue list [--state open|closed|all]   List local issues
    rddf issue show <hash>      Show a specific local issue body

Usage::

    python3 -m skills._lib.cli issue submit .rddf/issues/flow-bug-abc12345.md
    python3 -m skills._lib.cli issue list
    python3 -m skills._lib.cli issue show abc12345
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from issue_reporter import submit_issue_via_gh  # type: ignore[import-not-found]


def cmd_issue(args: list[str]) -> int:
    """Dispatch to issue submit / list / show based on first arg."""
    if not args:
        print("Usage: rddf issue {submit <file> | list | show <hash>}")
        return 2

    subcommand = args[0]
    rest = args[1:]

    if subcommand == "submit":
        return _issue_submit(rest)
    if subcommand == "list":
        return _issue_list(rest)
    if subcommand == "show":
        return _issue_show(rest)

    print(f"Unknown issue subcommand: {subcommand!r}. Expected: submit | list | show")
    return 2


def _issue_submit(args: list[str]) -> int:
    if not args:
        print("Usage: rddf issue submit <file>")
        return 2
    file_path = Path(args[0])
    if not file_path.is_file():
        print(f"❌ file not found: {file_path}")
        return 1

    category = _extract_category_from_filename(file_path.name)
    if not category:
        print(f"⚠️  cannot infer category from filename {file_path.name!r}; using 'manual'")
        category = "manual"

    gh_repo = os.environ.get("RDDF_REPORT_GH_REPO", "chisuhua/rdd-workflow")
    result = submit_issue_via_gh(file_path, category, gh_repo)
    if result.success:
        print(f"✅ submitted: {result.submitted_url}")
        return 0
    print(f"❌ submit failed: {result.error}")
    return 1


def _issue_list(args: list[str]) -> int:
    project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", os.getcwd()))
    issues_dir = project_root / ".rddf" / "issues"
    if not issues_dir.is_dir():
        print("ℹ️  no .rddf/issues/ directory (no issues recorded)")
        return 0

    state_filter = "all"
    if args and args[0] in ("--state",):
        if len(args) < 2:
            print("Usage: rddf issue list [--state open|closed|all]")
            return 2
        state_filter = args[1]

    files = sorted(issues_dir.glob("*.md"))
    if not files:
        print("ℹ️  no local issues")
        return 0

    for path in files:
        content = path.read_text(encoding="utf-8", errors="replace")
        submitted = "submitted: true" in content
        closed = "closed_at:" in content
        status = "closed" if closed else ("submitted" if submitted else "local")
        if state_filter == "open" and status != "local":
            continue
        if state_filter == "closed" and status != "closed":
            continue
        title = _extract_title(content) or "(no description)"
        print(f"  {path.name}  [{status}]  {title[:60]}")
    return 0


def _issue_show(args: list[str]) -> int:
    if not args:
        print("Usage: rddf issue show <hash>")
        return 2
    dedup_hash = args[0]
    project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", os.getcwd()))
    issues_dir = project_root / ".rddf" / "issues"

    for path in issues_dir.glob(f"*-{dedup_hash}.md"):
        print(path.read_text(encoding="utf-8", errors="replace"))
        return 0

    print(f"❌ no local issue with hash {dedup_hash}")
    return 1


def _extract_category_from_filename(name: str) -> str:
    m = re.match(r"^([a-z][a-z0-9-]+)-[0-9a-f]{8}\.md$", name)
    return m.group(1) if m else ""


def _extract_title(content: str) -> str:
    """Extract the human-readable title from an issue file body.

    Walks the markdown body after the frontmatter, skipping H2 section
    headers (``## Description`` etc.) to return the first line of actual
    content (which is the description text written by detect_issue).
    """
    in_fm = False
    past_fm = False
    for line in content.splitlines():
        if line.strip() == "---":
            in_fm = not in_fm
            if not in_fm:
                past_fm = True
            continue
        if in_fm or not past_fm:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("## "):
            continue
        return stripped
    return ""
