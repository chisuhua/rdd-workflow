#!/usr/bin/env python3
"""Update a change's status to "已完成" in proposal-suggestions.md."""
import json, sys

def update_proposal_status(change_name: str, project_root: str) -> bool:
    path = f"{project_root}/proposal-suggestions.md"
    try:
        with open(path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False

    found = False
    for item in data:
        if item.get("name") == change_name:
            item["status"] = "已完成"
            found = True
            break
    if not found:
        return False

    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True

if __name__ == "__main__":
    change_name = sys.argv[1]
    project_root = sys.argv[2] if len(sys.argv) > 2 else "."
    success = update_proposal_status(change_name, project_root)
    sys.exit(0 if success else 1)
