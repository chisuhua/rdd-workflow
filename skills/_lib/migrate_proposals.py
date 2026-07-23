#!/usr/bin/env python3
"""Migrate legacy JSON proposal-suggestions.md to individual improvements/*.md files.

Usage:
    python3 skills/_lib/migrate_proposals.py <project_root>

Steps:
1. Reads the OLD JSON content from ``git show HEAD:proposal-suggestions.md``
   (the current working-tree file has been rewritten as a Markdown index).
2. Backs up the old JSON to ``proposal-suggestions.json.bak``.
3. For each JSON entry, creates ``improvements/<name>.md`` with a structured
   template extracting the five ``## `` sections from the ``description`` field.
4. Skips entries whose target file already exists (idempotent).

The migration is safe to re-run: existing files are never overwritten.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

EXPECTED_SECTIONS = [
    "架构依据",
    "范围",
    "关键场景",
    "技术约束",
    "验收标准",
]


def extract_sections(description: str) -> dict[str, str]:
    """Parse ``## `` headers from description, return {section_name: content}.

    Handles entries where some sections are missing - absent sections get "".
    """
    # Split on '## ' to find all section headers and their content.
    # The split produces: [pre_text, 'Header1\nbody', 'Header2\nbody', ...]
    parts = re.split(r"^## ", description, flags=re.MULTILINE)
    sections: dict[str, str] = {}
    for part in parts[1:]:  # skip text before first '## '
        lines = part.split("\n", 1)
        header = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        sections[header] = body
    return sections


def build_md_content(entry: dict) -> str:
    """Build the Markdown file content from a single JSON entry."""
    name = entry.get("name", "unknown")
    priority = entry.get("priority", "?")
    source = entry.get("source", "?")
    phase = entry.get("phase", "default")
    category = entry.get("category", "general")
    change_type = entry.get("change_type", entry.get("type", "feature"))
    description = entry.get("description", "")

    sections = extract_sections(description)

    lines: list[str] = []
    lines.append(f"# {name}")
    lines.append("")
    lines.append(f"**优先级**: {priority} | **来源**: {source}")
    lines.append(f"**阶段**: {phase} | **分类**: {category}")
    lines.append(f"**类型**: {change_type}")
    lines.append("")

    for section_name in EXPECTED_SECTIONS:
        content = sections.get(section_name, "")
        lines.append(f"## {section_name}")
        lines.append(content if content else "（无）")
        lines.append("")

    return "\n".join(lines)


def get_old_json(project_root: str) -> list[dict]:
    """Retrieve the old JSON content from git HEAD.

    Falls back to reading proposal-suggestions.md directly if it still
    contains valid JSON (pre-rewrite state).
    """
    try:
        result = subprocess.run(
            ["git", "show", "HEAD:proposal-suggestions.md"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            if isinstance(data, list):
                return data
    except (subprocess.SubprocessError, json.JSONDecodeError):
        pass

    # Fallback: try reading the file directly (in case git show failed)
    ps_path = os.path.join(project_root, "proposal-suggestions.md")
    try:
        with open(ps_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    return []


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: migrate_proposals.py <project_root>", file=sys.stderr)
        return 1

    project_root = os.path.abspath(sys.argv[1])
    imp_dir = os.path.join(project_root, "improvements")
    os.makedirs(imp_dir, exist_ok=True)

    # Step 1: Get old JSON from git HEAD
    entries = get_old_json(project_root)
    if not entries:
        print("❌ No JSON entries found in git HEAD or proposal-suggestions.md",
              file=sys.stderr)
        return 1

    print(f"Found {len(entries)} entries to migrate")

    # Step 2: Backup old JSON
    bak_path = os.path.join(project_root, "proposal-suggestions.json.bak")
    # Write the raw JSON from git to the backup file
    try:
        result = subprocess.run(
            ["git", "show", "HEAD:proposal-suggestions.md"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=30,
        )
        if result.returncode == 0:
            with open(bak_path, "w", encoding="utf-8") as f:
                # Pretty-print the JSON for readability
                try:
                    parsed = json.loads(result.stdout)
                    json.dump(parsed, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                except json.JSONDecodeError:
                    f.write(result.stdout)
            print(f"✅ Backup written to {bak_path}")
    except subprocess.SubprocessError:
        # Fallback: backup from the file itself if it's still JSON
        ps_path = os.path.join(project_root, "proposal-suggestions.md")
        try:
            with open(ps_path, "r", encoding="utf-8") as f:
                content = f.read()
            json.loads(content)  # validate it's JSON
            shutil.copy2(ps_path, bak_path)
            print(f"✅ Backup written to {bak_path}")
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            print("⚠️  Could not create backup (file already rewritten?)",
                  file=sys.stderr)

    # Step 3: Create improvement files
    created = 0
    skipped = 0
    failed = 0

    for entry in entries:
        name = entry.get("name", "")
        if not name:
            print("⚠️  Skipping entry without name", file=sys.stderr)
            failed += 1
            continue

        target_path = os.path.join(imp_dir, f"{name}.md")

        # Idempotent: skip if file already exists
        if os.path.exists(target_path):
            print(f"  ⏭️  {name}.md already exists, skipping")
            skipped += 1
            continue

        try:
            content = build_md_content(entry)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  ✅ Created {name}.md")
            created += 1
        except (OSError, UnicodeEncodeError) as e:
            print(f"  ❌ Failed to create {name}.md: {e}", file=sys.stderr)
            failed += 1

    print(f"\n{'='*50}")
    print(f"Migration complete: {created} created, {skipped} skipped, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
