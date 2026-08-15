#!/usr/bin/env python3
"""Main logic for add-improve --from-issue mode.

Reads validated env-vars (from from_issue.env.py), reads pre-fetched issue
metadata, writes a proposal scaffold with **issue_ref** + **gh_repo** frontmatter.

HARD-GATE: does NOT auto-approve or modify proposal-suggestions.md — user must
still run rdd-workflow-brainstorm for section approval.

Usage:
    Called from from_issue.sh after env validation. All inputs come from
    env-vars (Oracle C1 anti-injection pattern):
      ADD_IMPROVE_FROM_ISSUE   — issue number (positive integer)
      ADD_IMPROVE_GH_REPO      — owner/repo (e.g. foo/bar)
      ADD_IMPROVE_ISSUE_TITLE  — issue title (max 200 chars)
      ADD_IMPROVE_ISSUE_BODY   — issue body (max 4000 chars, truncated upstream)
      PROJECT_ROOT             — absolute path to project root
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


_BODY_MAX_CHARS = 4000
_BODY_TRUNCATION_SUFFIX = "\n\n... (剩余 {remaining} 字符，参见 {url})\n"


@dataclass
class DedupHit:
    path: str
    source: str  # "improvements" or "roadmap-meta"


def _print_error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def slugify(title: str) -> str:
    temp = re.sub(r"[^\w\s]", "-", title)
    cleaned = re.sub(r"[\s-]+", "-", temp.strip())
    cleaned = re.sub(r"[A-Z]+", lambda m: m.group(0).lower(), cleaned)
    return cleaned.strip("-")


def truncate_body(body: str, issue_url: str, max_chars: int = _BODY_MAX_CHARS) -> str:
    """Truncate body to ``max_chars`` and append reference URL."""
    suffix = _BODY_TRUNCATION_SUFFIX.format(remaining=len(body) - max_chars, url=issue_url)
    if len(body) <= max_chars:
        return body
    return body[: max_chars - len(suffix)] + suffix


def _parse_improvement_frontmatter(path: Path) -> Optional[int]:
    """Return ``issue_ref`` from a .rddf/improvements/<name>.md frontmatter, or None."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    # Simple frontmatter parse (yaml-free)
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    fm = text[3:end]
    for line in fm.splitlines():
        line = line.strip()
        if line.startswith("issue_ref:"):
            value = line.split(":", 1)[1].strip()
            if value.isdigit():
                return int(value)
    return None


def _parse_roadmap_meta_issue_refs(path: Path) -> List[int]:
    """Return ``issue_refs`` list from a roadmap-meta.yaml, or []."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    refs = []
    in_list = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("issue_refs:"):
            value = stripped.split(":", 1)[1].strip()
            if value.startswith("["):
                # Inline list: issue_refs: [42, 99]
                for tok in re.findall(r"\d+", value):
                    refs.append(int(tok))
            else:
                # Block list: starts on next line
                in_list = True
                continue
        if in_list:
            tok = stripped.lstrip("- ").strip()
            if tok.isdigit():
                refs.append(int(tok))
            elif stripped and not stripped.startswith("-"):
                in_list = False
    return refs


def check_dedup(issue_num: int, project_root: Path) -> List[DedupHit]:
    """Scan two locations for existing references to ``issue_num``.

    Returns a list of DedupHit (empty list = no conflict).
    """
    hits: List[DedupHit] = []

    improvements_dir = project_root / ".rddf" / "improvements"
    if improvements_dir.is_dir():
        for path in improvements_dir.glob("*.md"):
            ref = _parse_improvement_frontmatter(path)
            if ref == issue_num:
                hits.append(DedupHit(
                    path=str(path.relative_to(project_root)),
                    source="improvements",
                ))

    changes_dir = project_root / "openspec" / "changes"
    if changes_dir.is_dir():
        for change_dir in changes_dir.iterdir():
            if not change_dir.is_dir():
                continue
            meta_path = change_dir / "roadmap-meta.yaml"
            if not meta_path.is_file():
                continue
            refs = _parse_roadmap_meta_issue_refs(meta_path)
            if issue_num in refs:
                hits.append(DedupHit(
                    path=str(meta_path.relative_to(project_root)),
                    source="roadmap-meta",
                ))

    return hits


def write_scaffold(
    *,
    project_root: Path,
    issue_num: int,
    gh_repo: str,
    title: str,
    body: str,
) -> Path:
    """Write the proposal scaffold and return the resolved file path.

    Slug collision is handled by appending ``-i<N>`` when the default slug
    is already taken.
    """
    base_slug = slugify(title)
    candidate_slug = f"{base_slug}-i{issue_num}"
    # If the -i<N> variant itself collides, append -counter
    counter = 1
    final_slug = candidate_slug
    improvements_dir = project_root / ".rddf" / "improvements"
    while (improvements_dir / f"{final_slug}.md").exists():
        counter += 1
        final_slug = f"{candidate_slug}-{counter}"

    proposal_name = final_slug
    proposal_file = improvements_dir / f"{proposal_name}.md"

    issue_url = f"https://github.com/{gh_repo}/issues/{issue_num}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    truncated_body = truncate_body(body, issue_url)

    content = (
        f"---\n"
        f"issue_ref: {issue_num}\n"
        f"gh_repo: {gh_repo}\n"
        f"---\n"
        f"# {proposal_name}\n"
        f"\n"
        f"**优先级**: TBD | **来源**: from-issue ({gh_repo}#{issue_num})\n"
        f"**issue_ref**: {issue_num}\n"
        f"**gh_repo**: {gh_repo}\n"
        f"**类型**: feature\n"
        f"\n"
        f"## 架构依据\n"
        f"\n"
        f"_待 brainstorm 填写 (上游 issue: {issue_url})_\n"
        f"\n"
        f"## 范围\n"
        f"\n"
        f"- **In Scope**: _待 brainstorm 确认_\n"
        f"- **Out Scope**: _待 brainstorm 确认_\n"
        f"\n"
        f"## 关键场景\n"
        f"\n"
        f"- GIVEN _待 brainstorm 填写_\n"
        f"  WHEN _\n"
        f"  THEN _\n"
        f"\n"
        f"## 技术约束\n"
        f"\n"
        f"- MUST _\n"
        f"- MUST NOT _\n"
        f"- SHOULD _\n"
        f"\n"
        f"## 验收标准\n"
        f"\n"
        f"- [ ] _\n"
        f"\n"
        f"## 上游 Issue 原文\n"
        f"\n"
        f"**title**: {title}\n"
        f"\n"
        f"<!-- 引用自 {issue_url} ({timestamp}) -->\n"
        f"\n"
        f"{truncated_body}\n"
    )

    try:
        improvements_dir.mkdir(parents=True, exist_ok=True)
        proposal_file.write_text(content, encoding="utf-8")
    except OSError as e:
        _print_error(f"Failed to write proposal file: {e}")
        raise

    return proposal_file


def main() -> int:
    required = [
        "ADD_IMPROVE_FROM_ISSUE",
        "ADD_IMPROVE_GH_REPO",
        "ADD_IMPROVE_ISSUE_TITLE",
        "PROJECT_ROOT",
    ]
    missing = [v for v in required if not os.environ.get(v, "").strip()]
    if missing:
        _print_error(f"Missing required env-vars: {', '.join(missing)}")
        return 1

    try:
        issue_num = int(os.environ["ADD_IMPROVE_FROM_ISSUE"])
    except ValueError:
        _print_error(f"ADD_IMPROVE_FROM_ISSUE must be int (got {os.environ['ADD_IMPROVE_FROM_ISSUE']!r})")
        return 1

    project_root = Path(os.environ["PROJECT_ROOT"])
    gh_repo = os.environ["ADD_IMPROVE_GH_REPO"]
    title = os.environ["ADD_IMPROVE_ISSUE_TITLE"]
    body = os.environ.get("ADD_IMPROVE_ISSUE_BODY", "").strip()

    # Dedup check
    hits = check_dedup(issue_num, project_root)
    if hits:
        _print_error(
            f"Issue #{issue_num} 已在以下位置被引用，跳过写入：\n"
            + "\n".join(f"  - {h.path} (来源: {h.source})" for h in hits)
        )
        return 2

    # Write scaffold
    try:
        proposal_file = write_scaffold(
            project_root=project_root,
            issue_num=issue_num,
            gh_repo=gh_repo,
            title=title,
            body=body,
        )
    except OSError as e:
        _print_error(f"Failed to write scaffold: {e}")
        return 1

    print(f"✅ Scaffold created: {proposal_file}")
    print(f"   issue_ref: {issue_num}")
    print(f"   gh_repo: {gh_repo}")
    print("   Next: run rdd-workflow-brainstorm interactively to fill scaffold and approve")
    print("   HARD-GATE: --from-issue mode does NOT bypass brainstorm section approval.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
