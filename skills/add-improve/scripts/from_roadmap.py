#!/usr/bin/env python3
"""Main logic for add-improve --from-roadmap mode.

Reads validated env-vars (from from_roadmap.env.py), writes proposal file
with **主题**: field populated. HARD-GATE: does NOT auto-approve or modify
proposal-suggestions.md — user must still go through rdd-workflow-brainstorm
for section approval.

Usage:
    Called from from_roadmap.sh after env validation. All inputs come from
    env-vars (Oracle C1 anti-injection pattern):
      ADD_IMPROVE_FROM_ROADMAP  — "phase_id/category_id"
      ADD_IMPROVE_THEME         — roadmap theme name
      BRAINSTORM_RATIONALE_DRAFT — optional AI-drafted rationale
      PROJECT_ROOT              — absolute path to project root
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _print_error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def main() -> int:
    required = ["ADD_IMPROVE_FROM_ROADMAP", "ADD_IMPROVE_THEME", "PROJECT_ROOT"]
    missing = [v for v in required if not os.environ.get(v, "").strip()]
    if missing:
        _print_error(f"Missing required env-vars: {', '.join(missing)}")
        return 1

    project_root = Path(os.environ["PROJECT_ROOT"])
    from_roadmap = os.environ["ADD_IMPROVE_FROM_ROADMAP"]
    theme = os.environ["ADD_IMPROVE_THEME"]
    rationale = os.environ.get("BRAINSTORM_RATIONALE_DRAFT", "").strip()

    phase_id, category_id = from_roadmap.split("/", 1)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    proposal_name = f"from-roadmap-{phase_id}-{category_id}".replace("/", "-")
    proposal_file = project_root / ".rddf" / "improvements" / f"{proposal_name}.md"

    rationale_section = (
        rationale if rationale else "_待 brainstorm 填写: AI 起草的 rationale 起草待用户确认_"
    )

    content = (
        f"# {proposal_name}\n"
        f"\n"
        f"**优先级**: P1 | **来源**: from-roadmap ({from_roadmap})\n"
        f"**阶段**: {phase_id} | **分类**: {category_id}\n"
        f"**类型**: functional\n"
        f"**主题**: {theme}\n"
        f"\n"
        f"## 架构依据\n"
        f"\n"
        f"{rationale_section}\n"
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
    )

    try:
        proposal_file.parent.mkdir(parents=True, exist_ok=True)
        proposal_file.write_text(content, encoding="utf-8")
    except OSError as e:
        _print_error(f"Failed to write proposal file: {e}")
        return 1

    print(f"✅ Scaffold created: {proposal_file}")
    print(f"   **主题**: {theme}")
    print(f"   Next: run rdd-workflow-brainstorm interactively to fill scaffold and approve")
    print(f"   HARD-GATE: --from-roadmap mode does NOT bypass brainstorm section approval.")
    return 0


if __name__ == "__main__":
    sys.exit(main())