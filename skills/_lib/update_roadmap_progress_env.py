#!/usr/bin/env python3
"""Entry-point script for skills/_lib/update_roadmap_progress.sh::update_roadmap_progress.

Reads env vars:
- PROJECT_ROOT (required) — absolute path to project root
- CHANGE_NAME (required) — name of the change to mark complete

All values flow through os.environ only — no bash string interpolation.
Oracle C1 safe.
"""
import os
import sys
from pathlib import Path


def main():
    project_root = os.environ.get("PROJECT_ROOT")
    change_name = os.environ.get("CHANGE_NAME")

    if not project_root or not change_name:
        print("ERROR: PROJECT_ROOT and CHANGE_NAME env vars required", file=sys.stderr)
        sys.exit(1)

    # Compute repo root from this script's location (grandparent of skills/_lib/)
    _repo_root = str(Path(__file__).resolve().parent.parent.parent)
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)

    from skills._lib import update_roadmap_progress as urmp

    result = urmp.update_roadmap_progress(project_root, change_name)

    if "error" in result:
        print(f"⚠️  Roadmap progress update skipped: {result['error']}", file=sys.stderr)
        sys.exit(0)  # Non-fatal — original inline block is gated behind if [ -f ... ]

    print(f"✅ 路线图进度已更新: {result['change_name']} → phase={result['phase']}, category={result['category']}")
    print(f"   完成变化: {', '.join(result['completed_changes'])}")
    if result["all_changes_complete"]:
        print(f"🎉 阶段 {result['phase']} 的所有 change 已完成！")
        print(f"   请检查阶段门控条件，准备进入下一阶段")
        print(f"   运行: skill_use(\"roadmap\", \"gate-report\")")


if __name__ == "__main__":
    main()