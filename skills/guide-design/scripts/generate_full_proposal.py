"""skills/guide-design/scripts/generate_full_proposal.py — D2 mapping.

Reads improvements/<name>.md (5 sections: 架构依据 / 范围 / 关键场景 / 技术约束 / 验收标准)
plus head fields (阶段 / 分类 / 类型), emits a complete openspec proposal.md draft.

D2 mapping:
  架构依据       -> ## Why
  范围 + 关键场景 -> ## What Changes (In Scope / Out of Scope)
  技术约束       -> ## Capabilities / ## Impact
  验收标准       -> ## Acceptance (markdown checkboxes preserved)

Output is a draft only; the caller (guide-design SKILL.md D1) must show it
to the user for confirmation before any disk write.
"""
import re


_HEAD_RE = re.compile(r"\*\*(阶段|分类|类型)\*\*:\s*([^|\n]+)")
_SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def validate_improvements_head(md: str) -> dict[str, str]:
    """Extract 阶段/分类/类型 from improvements head.

    Falls back to safe defaults when missing:
      阶段  -> default
      分类  -> general
      类型  -> feature

    Returns the dict with the three keys always present.
    """
    head: dict[str, str] = {}
    for key, val in _HEAD_RE.findall(md):
        head[key] = val.strip()
    head.setdefault("阶段", "default")
    head.setdefault("分类", "general")
    head.setdefault("类型", "feature")
    return head


def _extract_section(md: str, title: str) -> str:
    """Extract content under '## <title>' up to next '## '. Returns '' if missing."""
    pattern = re.compile(
        rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(md)
    return m.group(1).strip() if m else ""


def _extract_in_scope_items(scope_md: str) -> list[str]:
    """Pull `-` bullet items from the 范围 section. Drops 'In Scope' / 'Out Scope' sub-headers."""
    items: list[str] = []
    for line in scope_md.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
        elif stripped.startswith("**In Scope**") or stripped.startswith("**Out Scope**"):
            continue
        elif stripped.startswith("**In Scope:**") or stripped.startswith("**Out Scope:**"):
            continue
    return items


def generate_full_proposal(change_name: str, improvements_md: str) -> str:
    """Build a full proposal.md draft per D2 mapping.

    Args:
        change_name: The change name (e.g. 'move-proposal-creation-to-design').
        improvements_md: The full content of improvements/<name>.md.

    Returns:
        Complete markdown draft. The caller is expected to ask the user to
        confirm before writing to disk.
    """
    validate_improvements_head(improvements_md)
    why = _extract_section(improvements_md, "架构依据")
    scope = _extract_section(improvements_md, "范围")
    scenarios = _extract_section(improvements_md, "关键场景")
    acceptance = _extract_section(improvements_md, "验收标准")

    in_scope_items = _extract_in_scope_items(scope)
    in_scope_block = "\n".join(f"- {item}" for item in in_scope_items) if in_scope_items else "- (TBD)"
    if scenarios:
        in_scope_block += "\n\n### 关键场景\n\n" + scenarios

    out_of_scope_block = (
        "- design 阶段不生成 tasks.md / design.md / specs (留在 plan fill)\n"
        "- 不修改 ADR-0003 (另起 ADR 记录本次职责再分配)\n"
    )

    capabilities_block = (
        "- `design-proposal-creation`: design 审批批准即创建完整 openspec change\n"
        "- `design-content-review`: 两层内容审查 (improvements 5 段 + openspec validate), warning / strict 双模式\n"
    )

    impact_block = (
        "- **受影响文件**: `skills/guide-design/SKILL.md` + 4 个 scripts, `skills/guide-plan/scripts/plan_intake.sh`, `docs/adr/ADR-0025-*.md` (新增)\n"
        "- **兼容性**: `SKIP_DESIGN_HANDOFF=yes` 存量路径行为不变\n"
        "- **硬约束**: 批准动作幂等; env-var 传参 (Oracle C1)\n"
    )

    return (
        f"# {change_name}\n\n"
        f"## Why\n\n"
        f"{why or '(TBD — 架构依据 from improvements 头部未提供)'}\n\n"
        f"## What Changes\n\n"
        f"**In Scope**:\n\n"
        f"{in_scope_block}\n\n"
        f"**Out of Scope**:\n\n"
        f"{out_of_scope_block}\n\n"
        f"## Capabilities\n\n"
        f"{capabilities_block}\n\n"
        f"## Impact\n\n"
        f"{impact_block}\n\n"
        f"## Acceptance\n\n"
        f"{acceptance or '- [ ] (TBD — 验收标准 from improvements 头部未提供)'}\n"
    )


if __name__ == "__main__":
    import os
    import sys

    improvements_path = os.environ.get("IMPROVEMENTS_PATH", "")
    change_name = os.environ.get("CHANGE_NAME", "")
    if not improvements_path or not os.path.exists(improvements_path):
        print("ERROR: IMPROVEMENTS_PATH missing or file not found", file=sys.stderr)
        sys.exit(2)
    if not change_name:
        print("ERROR: CHANGE_NAME not set", file=sys.stderr)
        sys.exit(2)
    text = open(improvements_path, encoding="utf-8").read()
    print(generate_full_proposal(change_name, text))
