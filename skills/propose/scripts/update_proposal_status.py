#!/usr/bin/env python3
"""Update a change's completed status in proposal-approved.md."""
import sys
import os


def update_proposal_status(change_name: str, project_root: str) -> bool:
    """Mark a proposal as completed in proposal-approved.md.
    
    Moves the entry from the '## 已批准提案' table to '## 已实施' table.
    """
    import re
    path = os.path.join(project_root, "proposal-approved.md")
    if not os.path.exists(path):
        return False
    
    with open(path) as f:
        lines = f.readlines()
    
    found = False
    priority = "?"
    remove_index: int | None = None
    for i, line in enumerate(lines):
        if f"[{change_name}]" in line and line.strip().startswith("|"):
            # Extract priority
            m = re.search(r'\|\s*\[[^\]]+\]\([^)]+\)\s*\|\s*(\S+)\s*\|', line)
            if m:
                priority = m.group(1)
            # Mark for removal
            remove_index = i
            found = True
            break
    
    if not found or remove_index is None:
        return False
    
    # Filter out the marked line
    new_lines = [ln for idx, ln in enumerate(lines) if idx != remove_index]
    
    # Find insertion point (after ## 已实施 header, before next ## section)
    inserted = False
    result = []
    for i, line in enumerate(new_lines):
        result.append(line)
        if line.startswith("## 已实施") and not inserted:
            # Find the first non-header, non-table-header line after this
            # Insert new row after the header lines
            j = i + 1
            while j < len(new_lines) and (
                new_lines[j].startswith("|") or new_lines[j].strip() == ""
            ):
                j += 1
            # Insert completed row at position j
            from datetime import date
            completed_row = f"| [{change_name}](.rddf/improvements/{change_name}.md) | {priority} | {date.today().isoformat()} |\n"
            result.insert(j, completed_row)
            inserted = True
            # 不再 break —— 后续行（表头、分隔线、旧条目）继续被 append
    
    if not inserted:
        from datetime import date
        result.append(f"| [{change_name}](.rddf/improvements/{change_name}.md) | {priority} | {date.today().isoformat()} |\n")
    
    with open(path, "w") as f:
        f.writelines(result)
    return True


if __name__ == "__main__":
    change_name = sys.argv[1]
    project_root = sys.argv[2] if len(sys.argv) > 2 else "."
    success = update_proposal_status(change_name, project_root)
    sys.exit(0 if success else 1)
