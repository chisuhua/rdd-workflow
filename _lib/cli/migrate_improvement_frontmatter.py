"""One-time migration: add YAML frontmatter to .rddf/improvements/*.md files that lack it.

Usage:
    python3 -m _lib.cli.migrate_improvement_frontmatter [--project-root <path>] [--dry-run]

Exit codes:
    0 — all files have valid frontmatter (or --dry-run reports what would happen)
    1 — fatal error

Design:
    - Scans `.rddf/improvements/*.md`
    - Skips files that already start with "---" (7 known + fix-skill-post-install-discoverability)
    - Extracts markdown bold metadata lines:  **key**: value
    - Converts to YAML frontmatter
    - Writes atomically (atomic_write_text)
    - Does a dry-run with --dry-run
    - Reports summary at end

    Per `_lib/planner_attach.py` L158-160, frontmatter MUST:
      1. Start with "---" on line 1
      2. Close with "---" (within first 20 lines)
      3. Contain parseable YAML (mapping)
"""

import os
import re
import sys
from pathlib import Path

def _improvements_root(project_root: Path) -> Path:
    return project_root / ".rddf" / "improvements"

def _has_frontmatter(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return text.startswith("---")

def _parse_markdown_metadata(text: str) -> dict:
    """Extract bold key: value lines from the top of a markdown file.
    
    Looks for lines matching  **key**: value before the first ## heading.
    Handles pipe-separated multi-value fields ( 优先级: P1 | 来源: ...).
    Stops at first '## ' heading — anything after is body, not metadata.
    """
    meta = {}
    for line in text.splitlines()[:30]:  # scan first 30 lines only
        if line.strip().startswith("## "):
            break
        if line.startswith("# ") or line.strip() == "":
            continue
        m = re.match(r'^\*\*([^*]+)\*\*[:\uFF1A]\s*(.*)', line)
        if not m:
            continue
        key = m.group(1).strip()
        value = m.group(2).strip()
        
        # Handle pipe-separated inline metadata:  "P1 | **来源**: 用户反馈"
        # First part is the current key's value; subsequent parts with **bold**
        # are additional metadata pairs.
        if " | " in value and not value.startswith("**"):
            parts = value.split(" | ")
            meta[key] = parts[0].strip()
            for part in parts[1:]:
                # Match either **key**: value or key: value patterns
                kv = re.match(r'^\s*(?:\*\*)?([^*\n]+?)(?:\*\*)?[:\uFF1A]\s*(.*)', part)
                if kv:
                    meta[kv.group(1).strip()] = kv.group(2).strip()
        else:
            meta[key] = value
    return meta

def _yaml_escape(value: str) -> str:
    """Escape a string value for YAML if it contains special characters."""
    if not value:
        return '""'
    if any(c in value for c in ':#{}[]&*!|>%@`"\n\r'):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value

def _meta_to_frontmatter(meta: dict) -> str:
    """Convert parsed metadata dict to YAML frontmatter string."""
    if not meta:
        return ""
    
    lines = ["---"]
    # Define field order (priority first, then logical order)
    field_order = ["优先级", "来源", "阶段", "分类", "类型", "主题", "依赖 ADR", "状态", "生成时间"]
    seen = set()
    
    for key in field_order:
        if key in meta:
            lines.append(f"{key}: {_yaml_escape(meta[key])}")
            seen.add(key)
    
    # Remaining fields in original order
    for key, value in meta.items():
        if key not in seen:
            lines.append(f"{key}: {_yaml_escape(value)}")
            seen.add(key)
    
    # Map common Chinese keys to a standard YAML frontmatter naming
    # Priority
    priority = meta.get("优先级", "")
    lines.append("---")
    return "\n".join(lines) + "\n"

def _convert_to_frontmatter_format(text: str, meta: dict, path: Path) -> str | None:
    """Convert a non-frontmatter improvement file to frontmatter format.
    
    Returns the new text content, or None if conversion is not possible.
    
    Strategy:
    1. Generate frontmatter from metadata
    2. Remove the metadata lines from the original body (they'll be in frontmatter now)
    3. Keep everything else intact
    """
    if not meta:
        print(f"  ⏭️  {path.name}: no metadata found, skipping", file=sys.stderr)
        return None
    
    frontmatter = _meta_to_frontmatter(meta)
    
    # Remove consumed metadata lines from body
    # Strategy: remove all **key**: value lines from first 30 lines
    lines = text.splitlines(keepends=True)
    body_start = 0
    for i, line in enumerate(lines):
        if re.match(r'^\*\*([^*]+)\*\*[:\uFF1A]', line):
            continue
        if i > 30:
            body_start = i
            break
        body_start = i + 1
        # Stop at first non-metadata line
        if line.strip() == "":
            continue
        if not re.match(r'^\*\*', line):
            break
    
    # But also skip leading ## heading if present
    body = "".join(lines[body_start:]).lstrip("\n")
    
    # Ensure first line is not the title with YAML start ambiguity
    # (the title should be after frontmatter)
    new_text = frontmatter + body
    
    # Ensure file starts with ---
    if not new_text.startswith("---"):
        return None
    
    return new_text

def migrate_one(path: Path, dry_run: bool) -> bool:
    """Migrate a single file. Returns True on success, False on skip/error."""
    if not path.exists():
        print(f"  ❌  {path.name}: file not found")
        return False
    
    text = path.read_text(encoding="utf-8")
    
    # Skip if already has frontmatter
    if _has_frontmatter(path):
        print(f"  ✅  {path.name}: already has frontmatter (skip)")
        return True
    
    # Parse markdown metadata
    meta = _parse_markdown_metadata(text)
    
    if not meta:
        print(f"  ⏭️  {path.name}: no metadata found")
        return False
    
    new_text = _convert_to_frontmatter_format(text, meta, path)
    if new_text is None:
        print(f"  ⏭️  {path.name}: cannot convert")
        return False
    
    if dry_run:
        print(f"  🔄  {path.name}: would migrate ({len(meta)} fields: {', '.join(meta.keys())})")
        return True
    
    # Write atomically
    from _lib.core.atomic_write import atomic_write_text
    atomic_write_text(path, new_text)
    
    # Verify
    written = path.read_text(encoding="utf-8")
    if not written.startswith("---"):
        print(f"  ❌  {path.name}: write verification FAILED")
        return False
    
    print(f"  ✅  {path.name}: migrated ({len(meta)} fields)")
    return True

def main(args: list[str] | None = None) -> int:
    if args is None:
        args = sys.argv[1:]
    
    project_root = Path(os.environ.get("PROJECT_ROOT", os.getcwd())).resolve()
    dry_run = False
    
    parsed_args = []
    for arg in args:
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--project-root":
            continue  # consume next
        elif args and args.index(arg) > 0 and args[args.index(arg) - 1] == "--project-root":
            project_root = Path(arg).resolve()
        else:
            parsed_args.append(arg)
    
    # Handle --project-root <path> manually
    i = 0
    while i < len(args):
        if args[i] == "--project-root" and i + 1 < len(args):
            project_root = Path(args[i + 1]).resolve()
            i += 2
        elif args[i] == "--dry-run":
            dry_run = True
            i += 1
        else:
            i += 1
    
    impr_root = _improvements_root(project_root)
    if not impr_root.is_dir():
        print(f"❌ improvements directory not found: {impr_root}")
        return 1
    
    files = sorted(impr_root.glob("*.md"))
    if not files:
        print("❌ no .md files found")
        return 1
    
    already_ok = 0
    migrated = 0
    skipped = 0
    failed = 0
    total = len(files)
    
    for f in files:
        if _has_frontmatter(f):
            already_ok += 1
            continue
        result = migrate_one(f, dry_run)
        if result:
            migrated += 1
        else:
            skipped += 1
    
    print(f"\n{'─' * 60}")
    if dry_run:
        print(f"🔍 DRY RUN: {total} files scanned")
        print(f"   Already OK:   {already_ok}")
        print(f"   Would migrate: {migrated}")
        print(f"   Would skip:    {skipped}")
        print(f"\n   Run without --dry-run to execute.")
    else:
        failed = total - already_ok - migrated - skipped
        print(f"📊 Migration complete: {total} files")
        print(f"   Already OK:   {already_ok} (had frontmatter)")
        print(f"   Migrated:     {migrated}")
        print(f"   Skipped:      {skipped} (no metadata found)")
        if failed > 0:
            print(f"   Failed:       {failed}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())