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


def _extract_scope_items(scope_md: str) -> tuple[list[str], list[str]]:
    """Split the 范围 section into (in_scope_items, out_scope_items).

    Handles both sub-header styles:
      - "**In Scope**:" / "- **In Scope**:" (optional leading dash)
      - items are "- " bullets following each header.
    Bullets appearing before any header default to in-scope.
    """
    in_items: list[str] = []
    out_items: list[str] = []
    current: str | None = None  # "in" | "out" | None
    for line in scope_md.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        header = stripped[2:].strip() if stripped.startswith("- ") else stripped
        if header.startswith("**In Scope**"):
            current = "in"
            continue
        if header.startswith("**Out Scope**"):
            current = "out"
            continue
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if current == "out":
                out_items.append(item)
            else:
                in_items.append(item)
    return in_items, out_items


def _extract_bullet_items(section_md: str) -> list[str]:
    """Pull "- " bullet items from a section body."""
    items: list[str] = []
    for line in section_md.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
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
    constraints = _extract_section(improvements_md, "技术约束")
    acceptance = _extract_section(improvements_md, "验收标准")

    in_scope_items, out_scope_items = _extract_scope_items(scope)
    in_scope_block = "\n".join(f"- {item}" for item in in_scope_items) if in_scope_items else "- (TBD)"
    if scenarios:
        in_scope_block += "\n\n### 关键场景\n\n" + scenarios

    out_of_scope_block = "\n".join(f"- {item}" for item in out_scope_items) if out_scope_items else "- (TBD)"

    constraint_items = _extract_bullet_items(constraints)
    capabilities_block = "\n".join(f"- {item}" for item in constraint_items) if constraint_items else "- (TBD)"
    impact_block = "\n".join(f"- {item}" for item in constraint_items) if constraint_items else "- (TBD)"

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
