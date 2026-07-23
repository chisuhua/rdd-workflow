#!/usr/bin/env python3
"""Auto-sync ADR index to docs/adr/README.md.

Scans docs/adr/ADR-*.md files, extracts title and status,
and updates the README.md table.

Usage:
    python3 skills/_lib/sync_adr_index.py [--dry-run]
"""
import argparse
import re
from pathlib import Path
from typing import Optional


def extract_adr_metadata(adr_path: Path) -> Optional[dict]:
    """Extract number, title, and status from ADR file."""
    content = adr_path.read_text()
    
    # Extract number from filename
    match = re.search(r"ADR-(\d{4})", adr_path.name)
    if not match:
        return None
    number = int(match.group(1))
    
    # Extract title from first markdown heading
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else adr_path.stem
    
    # Extract status from Status section
    status_match = re.search(r"##\s+Status\s*\n+(.+?)(?=\n##|\Z)", content, re.DOTALL)
    status = status_match.group(1).strip() if status_match else "待定"
    
    # Simplify status for display
    if "已采纳" in status:
        status = "已采纳"
    elif "已弃用" in status:
        status = "已弃用"
    elif "待定" in status:
        status = "待定"
    elif "已替代为" in status:
        # Extract the replacement ADR
        replacement = re.search(r"ADR-(\d{4})", status)
        if replacement:
            status = f"已替代为 ADR-{replacement.group(1)}"
    
    return {
        "number": number,
        "filename": adr_path.name,
        "title": title,
        "status": status,
    }


def generate_table(adrs: list[dict]) -> str:
    """Generate markdown table from ADR metadata."""
    lines = [
        "| ADR | 标题 | 状态 |",
        "|-----|------|------|",
    ]
    
    for adr in sorted(adrs, key=lambda x: x["number"]):
        if adr["number"] == 0:  # Skip template
            continue
        lines.append(
            f"| [ADR-{adr['number']:04d}]({adr['filename']}) | {adr['title']} | {adr['status']} |"
        )
    
    return "\n".join(lines)


def sync_adr_index(project_root: str, dry_run: bool = False) -> bool:
    """Sync ADR index to README.md. Returns True if changes made."""
    adr_dir = Path(project_root) / "docs" / "adr"
    readme_path = adr_dir / "README.md"
    
    if not adr_dir.exists():
        print(f"❌ ADR directory not found: {adr_dir}")
        return False
    
    # Scan ADR files
    adrs = []
    for adr_file in adr_dir.glob("ADR-*.md"):
        metadata = extract_adr_metadata(adr_file)
        if metadata:
            adrs.append(metadata)
    
    if not adrs:
        print("❌ No ADR files found")
        return False
    
    print(f"📄 Found {len(adrs)} ADR files")
    
    # Generate new table
    new_table = generate_table(adrs)
    
    if dry_run:
        print("\n📋 Generated table:")
        print(new_table)
        return True
    
    # Update README.md
    if readme_path.exists():
        content = readme_path.read_text()
        
        # Find and replace table section
        # Look for "## ADR 列表" section
        pattern = r"(## ADR 列表\s*\n+)(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            # Replace existing table
            new_content = content[:match.start(2)] + new_table + content[match.end(2):]
        else:
            # Append table after main content
            new_content = content.rstrip() + "\n\n## ADR 列表\n\n" + new_table + "\n"
        
        readme_path.write_text(new_content)
        print(f"✅ Updated {readme_path}")
        return True
    else:
        # Create new README.md
        readme_content = f"""# ADR 索引

> 架构决策记录 (Architecture Decision Records)

## ADR 列表

{new_table}
"""
        readme_path.write_text(readme_content)
        print(f"✅ Created {readme_path}")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync ADR index")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    sync_adr_index(args.project_root, args.dry_run)
