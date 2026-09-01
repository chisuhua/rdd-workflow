"""skills/guide-design/scripts/generate_full_proposal.py — D2 mapping.

Reads .rddf/improvements/<name>.md (5 sections: 架构依据 / 范围 / 关键场景 / 技术约束 / 验收标准)
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
    """Extract 阶段/分类/类型 from .rddf/improvements head.

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


def _extract_section(md: str, title: str | list[str]) -> str:
    """Extract content under '## <title>' up to next '## '. Returns '' if missing.

    `title` may be a single string or a list of candidates. When a list is
    given, the first matching title wins (priority order). This handles
    `## 验收` vs `## 验收标准` style variants in `.rddf/improvements/*.md`.
    """
    titles = [title] if isinstance(title, str) else list(title)
    for t in titles:
        pattern = re.compile(
            rf"^## {re.escape(t)}\s*$(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        m = pattern.search(md)
        if m:
            return m.group(1).strip()
    return ""


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
        if header.startswith("**In Scope**") or header.lstrip("# ").strip().startswith("In Scope"):
            current = "in"
            continue
        if header.startswith("**Out of Scope**") or header.lstrip("# ").strip().startswith("Out of Scope"):
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
    """Pull bullet or numbered list items from a section body.
    
    Supports bullets ("- "), numbered ("1. " / "1) "), and sub-items.
    """
    items: list[str] = []
    # Define list item prefixes: bullets and numbered (1-9 with dot or paren)
    prefixes = ["- "] + [f"{n}. " for n in range(1, 10)] + [f"{n}) " for n in range(1, 10)]
    current_item = None
    for line in section_md.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Attach indented sub-items before checking top-level prefixes.
        if current_item is not None and line.startswith("   - "):
            sub_text = line.strip()[2:]
            current_item += f"\n   - {sub_text}"
            continue
        # Check if line is a top-level list item (bullet or numbered).
        for prefix in prefixes:
            if stripped.startswith(prefix):
                if current_item is not None:
                    items.append(current_item)
                current_item = stripped[len(prefix):]
                break
    # Append final item
    if current_item is not None:
        items.append(current_item)
    return items


def _split_capabilities_impact(constraint_items: list[str]) -> tuple[list[str], list[str]]:
    """Split constraint items into Capabilities (MUST) and Impact (MUST NOT)."""
    capabilities = []
    impact = []
    for item in constraint_items:
        stripped = item.strip()
        if stripped.startswith("MUST NOT"):
            impact.append(item)
        else:
            capabilities.append(item)
    return capabilities, impact


def generate_full_proposal(change_name: str, improvements_md: str) -> str:
    """Build a full proposal.md draft per D2 mapping.

    Args:
        change_name: The change name (e.g. 'move-proposal-creation-to-design').
        improvements_md: The full content of .rddf/improvements/<name>.md.

    Returns:
        Complete markdown draft. The caller is expected to ask the user to
        confirm before writing to disk.
    """
    validate_improvements_head(improvements_md)
    why = _extract_section(improvements_md, "架构依据")
    scope = _extract_section(improvements_md, "范围")
    scenarios = _extract_section(improvements_md, "关键场景")
    constraints = _extract_section(improvements_md, "技术约束")
    acceptance = _extract_section(improvements_md, ["验收", "验收标准"])

    in_scope_items, out_scope_items = _extract_scope_items(scope)
    in_scope_block = "\n".join(f"- {item}" for item in in_scope_items) if in_scope_items else "- (no items specified)"
    if scenarios:
        in_scope_block += "\n\n### 关键场景\n\n" + scenarios

    out_of_scope_block = "\n".join(f"- {item}" for item in out_scope_items) if out_scope_items else "- (no items specified)"

    constraint_items = _extract_bullet_items(constraints)
    # Split constraints by MUST vs MUST NOT
    capabilities, impact = _split_capabilities_impact(constraint_items)
    capabilities_block = "\n".join(f"- {item}" for item in capabilities) if capabilities else "- (no items specified)"
    impact_block = "\n".join(f"- {item}" for item in impact) if impact else "- (no items specified)"

    return (
        f"# {change_name}\n\n"
        f"## Why\n\n"
        f"{why or '(TBD — 架构依据 from .rddf/improvements 头部未提供)'}\n\n"
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
        f"{acceptance or '- [ ] (TBD — 验收标准 from .rddf/improvements 头部未提供)'}\n"
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


def generate_spec_delta(source_md: str, sub: str) -> str:
    """D3 mapping: 从源 .rddf/improvements markdown 生成 openspec v1.4 spec.md。

    映射规则 (D2 → D3):
    - ## Acceptance 每个 - [ ] checkbox → ### Requirement + #### Scenario
    - ## Capabilities 每条 MUST/MUST NOT → ### Requirement
    - 顶部统一加 ## ADDED Requirements 段头 (openspec v1.4 强制)
    - 默认 <sub> 名由调用方传入
    """
    lines = ["## ADDED Requirements", ""]
    req_idx = 0

    # 1. 提取 ## Acceptance checkboxes
    acc_match = re.search(r"## Acceptance\s*\n(.*?)(?=\n## |\Z)", source_md, re.DOTALL | re.IGNORECASE)
    if acc_match:
        for m in re.finditer(r"^\s*-\s*\[[ xX]?\]\s*(.+?)$", acc_match.group(1), re.MULTILINE):
            req_idx += 1
            text = m.group(1).strip()
            req_name = f"acceptance-{req_idx}"
            lines.append(f"### Requirement: {req_name}")
            lines.append("")
            lines.append(f"The system SHALL {text}.")
            lines.append("")
            lines.append(f"#### Scenario: {text[:60]}")
            lines.append("")
            lines.append("- **WHEN** the change is applied")
            lines.append(f"- **THEN** {text}")
            lines.append("")

    # 2. 提取 ## Capabilities MUST/MUST NOT
    # 注: openspec v1.4 要求每个 Requirement 至少含 1 个 #### Scenario:
    cap_match = re.search(r"## Capabilities\s*\n(.*?)(?=\n## |\Z)", source_md, re.DOTALL | re.IGNORECASE)
    if cap_match:
        for m in re.finditer(r"^\s*-\s*\*\*(MUST(?:\s+NOT)?)\*\*:\s*(.+?)$", cap_match.group(1), re.MULTILINE):
            req_idx += 1
            kind = m.group(1).strip()
            text = m.group(2).strip()
            req_name = f"capability-{req_idx}"
            lines.append(f"### Requirement: {req_name}")
            lines.append("")
            lines.append(f"The system {kind} {text}.")
            lines.append("")
            lines.append(f"#### Scenario: enforces {text[:50]}")
            lines.append("")
            lines.append("- **WHEN** the change is applied")
            lines.append(f"- **THEN** {text} is enforced")
            lines.append("")

    return "\n".join(lines) + "\n"
