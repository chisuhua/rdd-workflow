#!/usr/bin/env python3
"""Main logic for add-improve --from-roadmap mode.

Reads validated env-vars (from from_roadmap.env.py), writes proposal file
with **主题**: field populated. HARD-GATE: does NOT auto-approve or modify
proposal-suggestions.md — user must still go through rdd-workflow-brainstorm
for section approval.

Naming flexibility (improve-from-roadmap-naming-flexibility, 2026-08-28):
  - default (backward compat):          from-roadmap-<phase>-<category>
  - --name-prefix / --name-suffix:      <prefix><phase>-<category><suffix>
  - --auto-name:                        <prefix><phase>-<category>-<timestamp><suffix>
  - --multi <N>:                        N sub-proposals named <base>-sub-1..N
  - conflict (name already exists):     auto-append -2, -3, ... (never overwrite)

Usage:
    Called from from_roadmap.sh after env validation. All inputs come from
    env-vars (Oracle C1 anti-injection pattern):
      ADD_IMPROVE_FROM_ROADMAP   — "phase_id/category_id"
      ADD_IMPROVE_THEME          — roadmap theme name
      BRAINSTORM_RATIONALE_DRAFT — optional AI-drafted rationale
      ADD_IMPROVE_NAME_PREFIX    — optional name prefix (kebab-case)
      ADD_IMPROVE_NAME_SUFFIX    — optional name suffix (kebab-case)
      ADD_IMPROVE_AUTO_NAME      — optional yes/true/1 -> timestamp unique name
      ADD_IMPROVE_MULTI          — optional positive int -> N sub-proposals
      PROJECT_ROOT               — absolute path to project root
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _print_error(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _compute_proposal_name(
    phase_id: str,
    category_id: str,
    name_prefix: str,
    name_suffix: str,
    auto_name: bool,
) -> str:
    """Compute the base proposal name from naming env-vars.

    Backward compatible: with no new env-vars set this returns the legacy
    `from-roadmap-<phase>-<category>` name.
    """
    if auto_name:
        unique = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        name = f"{name_prefix}{phase_id}-{category_id}-{unique}{name_suffix}".replace("/", "-").strip("-")
        return name or f"from-roadmap-{phase_id}-{category_id}-{unique}".replace("/", "-")
    if name_prefix or name_suffix:
        return f"{name_prefix}{phase_id}-{category_id}{name_suffix}".replace("/", "-").strip("-")
    return f"from-roadmap-{phase_id}-{category_id}".replace("/", "-")


def _resolve_proposal_file(project_root: Path, proposal_name: str) -> Path:
    """Return the first non-existing <name>.md path.

    On name conflict, appends -2, -3, ... so an existing proposal is never
    overwritten (improve-from-roadmap-naming-flexibility behavior).
    """
    improvements = project_root / ".rddf" / "improvements"
    proposal_file = improvements / f"{proposal_name}.md"
    n = 2
    while proposal_file.exists():
        proposal_file = improvements / f"{proposal_name}-{n}.md"
        n += 1
    return proposal_file


def _build_content(
    proposal_name: str,
    theme: str,
    from_roadmap: str,
    phase_id: str,
    category_id: str,
    rationale: str,
) -> str:
    rationale_section = (
        rationale if rationale else "_待 brainstorm 填写: AI 起草的 rationale 起草待用户确认_"
    )
    return (
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
        f"_待 brainstorm 填写_\n"
        f"\n"
        f"## Why\n"
        f"\n"
        f"_待 brainstorm 填写_\n"
        f"\n"
        f"## What Changes\n"
        f"\n"
        f"_待 brainstorm 填写_\n"
        f"\n"
        f"## Capabilities\n"
        f"\n"
        f"- MUST _\n"
        f"\n"
        f"## Impact\n"
        f"\n"
        f"- MUST NOT _\n"
        f"\n"
        f"## Acceptance\n"
        f"\n"
        f"- [ ] _\n"
        f"- [ ] _\n"
        f"- [ ] _\n"
    )


def _write_proposal(project_root: Path, proposal_name: str, content: str) -> Path:
    proposal_file = _resolve_proposal_file(project_root, proposal_name)
    try:
        proposal_file.parent.mkdir(parents=True, exist_ok=True)
        proposal_file.write_text(content, encoding="utf-8")
    except OSError as e:
        _print_error(f"Failed to write proposal file: {e}")
        raise
    return proposal_file


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
    name_prefix = os.environ.get("ADD_IMPROVE_NAME_PREFIX", "").strip()
    name_suffix = os.environ.get("ADD_IMPROVE_NAME_SUFFIX", "").strip()
    auto_name = os.environ.get("ADD_IMPROVE_AUTO_NAME", "").strip().lower() in ("1", "yes", "true")
    multi = os.environ.get("ADD_IMPROVE_MULTI", "").strip()

    phase_id, category_id = from_roadmap.split("/", 1)
    base_name = _compute_proposal_name(phase_id, category_id, name_prefix, name_suffix, auto_name)

    try:
        if multi:
            count = int(multi)
            created = []
            for i in range(1, count + 1):
                sub_name = f"{base_name}-sub-{i}"
                content = _build_content(
                    sub_name, theme, from_roadmap, phase_id, category_id, rationale
                )
                created.append(_write_proposal(project_root, sub_name, content))
            for pf in created:
                print(f"✅ Scaffold created: {pf}")
            print(f"   **主题**: {theme} ({count} sub-proposals)")
            print("   Next: run rdd-workflow-brainstorm on each scaffold")
            print("   HARD-GATE: --from-roadmap mode does NOT bypass brainstorm section approval.")
        else:
            content = _build_content(
                base_name, theme, from_roadmap, phase_id, category_id, rationale
            )
            proposal_file = _write_proposal(project_root, base_name, content)
            print(f"✅ Scaffold created: {proposal_file}")
            print(f"   **主题**: {theme}")
            print("   Next: run rdd-workflow-brainstorm interactively to fill scaffold and approve")
            print("   HARD-GATE: --from-roadmap mode does NOT bypass brainstorm section approval.")
    except (OSError, ValueError) as e:
        _print_error(str(e))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())