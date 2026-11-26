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
import os
import re
import sys
from pathlib import Path

# 形态判据的**单一真源**（2026-11-27）：生成器与仓库的形态守卫必须引用同一份判据，
# 否则「守卫改 A、生成器仍按 B 判」⇒ 退化形态持续流入归档期（AC10）。
# ⚠ 仓库根 = 本脚本上溯 3 层（skills/rdd-builder/scripts → 仓库根）；全局安装布局同理。
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from _lib.openspec_version import native_scenario_conservation_available  # noqa: E402
from _lib.spec_requirement_form import describe_degradation  # noqa: E402


_HEAD_RE = re.compile(r"\*\*(阶段|分类|类型)\*\*:\s*([^|\n]+)")
_SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)
# A list item inside the 范围 section: bullet ("- x") or ordered ("1. x" / "1) x").
# The ordered form matters because the repo's improvements write In Scope that way —
# without it a numbered list parses to zero items and the caller's fallback swallows
# the whole section (Out of Scope included).
_SCOPE_ITEM_RE = re.compile(r"^(?:-\s+|\d+[.)]\s+)(.*)$")
# A scope block header, in every spelling that occurs in .rddf/improvements:
# `**In Scope**:`, `- **Out Scope**:`, `### In Scope`, `### Out of Scope`,
# `## Out Scope`. Decorations (bullet / heading marks / bold / colon) optional.
#: ⚠ **尾部注解容忍**（2026-11-27）：本仓的 improvement 写成 `**In Scope（6 项 · contract 面）**`
#: ⇒ 旧正则（尾部只允许空白/冒号）**认不出它是标题** ⇒ 其后的条目无处归属（表格范围节会解析成 0 条）。
#: 注解形态：圆括号 / 方括号 / 圆括号中文式，可含任意非换行文本；其后允许残留的 `**` 与冒号。
_SCOPE_HEADER_RE = re.compile(
    r"^[\s#*\-]*((?:out\s+of|out|in)\s+scope)"
    r"(?:[\s（(\[【][^\n]*?)?"
    r"[\s*]*[\s*:：]*$",
    re.IGNORECASE,
)

#: markdown 表格行（以 `|` 开头且以 `|` 结尾）。
_TABLE_ROW_RE = re.compile(r"^\|.*\|$")
#: markdown 表格的**对齐行**（`|---|---|` / `|:--:|---|`）—— 不是数据行。
_TABLE_ALIGN_RE = re.compile(r"^\|[\s:|-]+\|$")


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


def _extract_section(
    md: str, title: str | list[str], *, warn_ambiguous: bool = False
) -> str:
    """Extract content under '## <title>' up to next '## '. Returns '' if missing.

    `title` may be a single string or a list of candidates. When a list is
    given, the first matching title wins (priority order). This handles
    `## 验收` vs `## 验收标准` style variants in `.rddf/improvements/*.md`.

    `warn_ambiguous=True` ⇒ 多个候选**同时命中**时写一行 stderr（点名歧义 + 取了谁）。
    ⚠ 只对**范围节**开启：`架构依据` + `Why` 的双命中是**有意的合并**（见
    `generate_full_proposal()` 的 why_head/why_legacy 合并），不是歧义。
    """
    titles = [title] if isinstance(title, str) else list(title)
    if warn_ambiguous:
        hits = [c for c in titles if re.search(rf"^## {re.escape(c)}\s*$", md, re.M)]
        if len(hits) > 1:
            print(
                f"⚠️  proposal: 范围节候选歧义（{hits}）⇒ 取候选序靠前者（{titles[0]}）",
                file=sys.stderr,
            )
    for t in titles:
        pattern = re.compile(
            rf"^## {re.escape(t)}\s*$(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        m = pattern.search(md)
        if m:
            return m.group(1).strip()
    return ""


def _is_table_data_row(stripped: str) -> bool:
    """是否为 markdown 表格的**数据行**（排除对齐行）。"""
    if not _TABLE_ROW_RE.match(stripped):
        return False
    return not _TABLE_ALIGN_RE.match(stripped)


def _table_row_to_item(stripped: str) -> str:
    """表格数据行 → 单条 item（**去掉 `|`**，各列以 ` — ` 连接，不折行）。

    为什么不保留 `|`：条目会被再拼进 proposal 的 bullet 列表，保留 `|` 会让下游把这一行
    误读成新的表格行（并再次触发逗号/表格切分类缺陷）。为什么不丢列：逐列丢弃会丢信息
    （如「改动 | 落点」两列都需要）。
    """
    cells = [c.strip() for c in stripped.strip().strip("|").split("|")]
    return " — ".join(c for c in cells if c)


def _extract_scope_items(scope_md: str) -> tuple[list[str], list[str]]:
    """Split the 范围 section into (in_scope_items, out_scope_items).

    Recognizes every scope-header spelling found in .rddf/improvements:
    "**In Scope**:", "- **Out Scope**:", "### In Scope", "### Out of Scope".
    Items may be bullets ("- x") or ordered ("1. x" / "1) x"); items appearing
    before any header default to in-scope.

    Nesting: the indent of the first item after a header is that header's base
    level — items at that indent are siblings, deeper ones are attached to the
    item above (openSpec spec `generator-scope-extraction`
    § numbered-item-subitems-attached). Without the base level, one of the two
    shapes in this repo collapses: `- **In Scope**:` + 2-space children would
    fold every child into the header instead of emitting them as items.

    Continuation lines that belong to a bullet (markdown tables, indented
    sub-items, wrapped paragraphs) stay with that bullet instead of being
    dropped. A table under a bullet is part of the item, not a separate
    item — dropping it silently loses spec content (e.g. the field-definition
    table and the judgement table of a layout-manifest improvement).
    """
    in_items: list[str] = []
    out_items: list[str] = []
    current: str | None = None  # "in" | "out" | None
    pending: str | None = None  # bullet text, flushed when the next bullet starts
    pending_scope: str | None = None
    # Indent of the FIRST item after a header. Items at that indent are
    # siblings; deeper items attach to the item above them (openSpec spec
    # `generator-scope-extraction` § numbered-item-subitems-attached). Both
    # shapes occur in .rddf/improvements: `1. item` + `   - sub` (sub-items),
    # and `- **In Scope**:` + `  - child` (the children ARE the items).
    # Using a per-header base indent is what tells the two apart.
    base_indent: int | None = None

    def flush() -> None:
        nonlocal pending, pending_scope
        if pending is not None:
            (out_items if pending_scope == "out" else in_items).append(pending)
        pending = None
        pending_scope = None

    # 纯表格节（该节至今**没有任何** bullet/编号条目）⇒ 表格行**各自成条目**；
    # 一旦本节出现过 bullet/编号条目 ⇒ 其后的表格**归该条目**（沿既有 spec
    # `generator-scope-extraction`「bullet 下的表格归该 bullet」的语义，不改）。
    seen_item_in_section = False
    table_rows: list[str] = []  # 当前表格块缓冲（纯表格模式）

    def flush_table_block() -> None:
        """把缓冲的表格行转成条目（每行一条）。"""
        nonlocal table_rows
        for row in table_rows:
            text = _table_row_to_item(row)
            if not text:
                continue
            (out_items if current == "out" else in_items).append(text)
        table_rows = []

    for raw in scope_md.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        header = stripped[2:].strip() if stripped.startswith("- ") else stripped
        header_match = _SCOPE_HEADER_RE.match(header)
        if header_match:
            flush()
            flush_table_block()
            # "Out Scope" (no "of") is the spelling most .rddf/improvements use;
            # only recognizing "Out of Scope" sent every out-of-scope item into
            # the in-scope block (measured: many files parsed to out=0).
            current = "out" if header_match.group(1).lower().startswith("out") else "in"
            base_indent = None
            seen_item_in_section = False
            continue
        if _is_table_data_row(stripped) and not seen_item_in_section:
            # 纯表格节 ⇒ 数据行各自成条目（表格头行紧跟的对齐行 ⇒ 头行不是数据行）
            if _TABLE_ALIGN_RE.match(stripped):
                continue
            table_rows.append(stripped)
            continue
        if _TABLE_ALIGN_RE.match(stripped) and table_rows:
            # 对齐行 ⇒ 它的上一行是**表头** ⇒ 丢弃表头（不是数据行）
            table_rows.pop(0)
            continue
        item = _SCOPE_ITEM_RE.match(stripped)
        if item:
            expanded = raw.expandtabs(4)
            indent = len(expanded) - len(expanded.lstrip(" "))
            if base_indent is None:
                base_indent = indent
            if indent <= base_indent:
                base_indent = indent  # dedent back to a shallower level: sibling
                flush()
                flush_table_block()
                pending = item.group(1).strip()
                pending_scope = current
                seen_item_in_section = True
                continue
            # deeper than the base level ⇒ sub-item, handled as a continuation
        if pending is None:
            flush_table_block()
            continue  # prose before the first bullet — not an item (unchanged)
        if stripped.startswith("|"):
            # Markdown table belonging to the current bullet. A table needs a
            # blank line before it, otherwise it is parsed as paragraph text.
            if not pending.endswith("\n\n"):
                pending = pending.rstrip("\n") + "\n\n"
            pending += raw.rstrip() + "\n"
            continue
        pending += "\n" + (raw.rstrip() if raw[:1] in (" ", "\t") else stripped)
    flush()
    flush_table_block()
    return in_items, out_items


def shape_labels(text: str) -> dict[str, int]:
    """按**行首形态**统计行数（table_row / bullet / numbered / other）。

    为什么按「行首形态」而不是按文件名：语料回归的差异必须能被**机判**归类
    （「本次修复改变了哪一类形态」），否则「差异白名单」只能靠人眼分类
    ⇒ 白名单可被同 PR 修改 ⇒ 判别力为零。

    - ``table_row``：markdown 表格数据行（排除对齐行）
    - ``bullet``：``- `` 开头的条目
    - ``numbered``：``1. `` / ``1) `` 开头的条目
    - ``other``：其余非空行
    """
    counts = {"table_row": 0, "bullet": 0, "numbered": 0, "other": 0}
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if _is_table_data_row(s):
            counts["table_row"] += 1
        elif re.match(r"^-\s+", s):
            counts["bullet"] += 1
        elif re.match(r"^\d+[.)]\s+", s):
            counts["numbered"] += 1
        else:
            counts["other"] += 1
    return counts


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

    Section title candidates (priority order — first match wins):
      why         -> ["架构依据", "Why"] (+ "Why" merged in when both exist)
      scope       -> ["范围", "What Changes", "Scope"]
      scenarios   -> ["关键场景", "Scenarios"]
      constraints -> ["技术约束", "Capabilities", "Constraints"]
      acceptance  -> ["验收", "验收标准", "Acceptance"]

    Per fix-v4-rdd-planner-scope-over-assignment (B1): v4 improvements may
    use either 中文 section names (legacy guide-design era) or English names
    (current convention). We accept both, with Chinese taking priority to
    preserve the original ADR-0025 D2 mapping contract.

    Per fix-proposal-generator-section-merge: when an improvement carries
    BOTH "## Why" (5-段 convention) and "## 架构依据" (legacy convention),
    neither is dropped — "## Why" comes first and "## 架构依据" follows as
    the supporting evidence.
    """
    validate_improvements_head(improvements_md)
    why_head = _extract_section(improvements_md, ["Why"])
    why_legacy = _extract_section(improvements_md, ["架构依据"])
    if why_head and why_legacy and why_head != why_legacy:
        why = f"{why_head}\n\n{why_legacy}"
    else:
        why = why_head or why_legacy
    scope = _extract_section(
        improvements_md, ["范围", "What Changes", "Scope"], warn_ambiguous=True
    )
    scenarios = _extract_section(improvements_md, ["关键场景", "Scenarios"])
    constraints = _extract_section(improvements_md, ["技术约束", "Capabilities", "Constraints"])
    acceptance = _extract_section(improvements_md, ["验收", "验收标准", "Acceptance"])

    in_scope_items, out_scope_items = _extract_scope_items(scope)
    if not in_scope_items and scope:
        # ⚠ **不再按逗号切分**（2026-11-27）：逗号兜底会把**多行文本**（含 markdown 表格）
        # 切碎 —— 实测（2026-11-26 CppTLM）：表格第 2 行的 `x.hh:43-53,56,79-89,106-113`
        # 被切成 4 个条目、**Out of Scope 整段重复两遍**。
        # ⇒ 解析不出条目时**保留原文** + 一行 stderr 诊断（不猜）。
        in_scope_items = [scope.strip()]
        print(
            "⚠️  proposal: 范围节未解析出条目 ⇒ 保留原文（不再按逗号切分）",
            file=sys.stderr,
        )
    in_scope_block = "\n".join(f"- {item}" for item in in_scope_items) if in_scope_items else "- (no items specified)"
    if scenarios:
        in_scope_block += "\n\n### 关键场景\n\n" + scenarios

    out_of_scope_block = "\n".join(f"- {item}" for item in out_scope_items) if out_scope_items else "- (no items specified)"

    constraint_items = _extract_bullet_items(constraints)
    capabilities, impact = _split_capabilities_impact(constraint_items)
    capabilities_block = "\n".join(f"- {item}" for item in capabilities) if capabilities else "- (no items specified)"

    impact_section_text = _extract_section(improvements_md, ["影响", "Impact"])
    if impact:
        impact_block = "\n".join(f"- {item}" for item in impact)
    elif impact_section_text:
        # Emit the section as-is: it is already a bullet list, so prefixing a
        # single "- " would produce "- - item" (double dash).
        impact_block = impact_section_text.strip()
    else:
        impact_block = "- (no items specified)"

    references = _extract_section(improvements_md, ["参考", "Reference", "References"])
    references_block = ""
    if references:
        references_block = f"\n## References\n\n{references}\n"

    priority_match = re.search(r"\*\*优先级\*\*\s*:\s*(P[012])", improvements_md)
    priority_line = ""
    if priority_match:
        priority_line = f"\n**优先级**: {priority_match.group(1)}\n"

    return (
        f"# {change_name}{priority_line}\n\n"
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
        f"{references_block}"
    )


# ── 载体（design D-1：粗体头行，与 ADR-0025 D6 的「头部」一致）────────────
#: 粗体头行：`**<键>**: <值>`（与 `_HEAD_RE` 同一形态族，但键不限枚举）。
_HEAD_FIELD_ANY_RE = re.compile(
    r"^\*\*(?P<key>[^*]+)\*\*\s*[:：]\s*(?P<value>.+?)\s*$", re.MULTILINE
)
#: 多条语义要求之间的分隔符（`;;` —— 避免逗号歧义：逗号切分正是本 change 修掉的缺陷）。
_SEMANTIC_SEP = ";;"


def _project_root() -> Path:
    """项目根：优先 `PROJECT_ROOT` 环境变量（`phase0_approval.sh` 传入）⇒ 回退 cwd。"""
    env = os.environ.get("PROJECT_ROOT")
    return Path(env) if env else Path.cwd()


def _head_field(text: str, key: str) -> str | None:
    """读粗体头行（`**delta**: ...` / `**语义要求**: ...`）；找不到 ⇒ None。"""
    for m in _HEAD_FIELD_ANY_RE.finditer(text):
        if m.group("key").strip() == key:
            return m.group("value").strip()
    return None


def delta_target_capability(text: str) -> str | None:
    """`**delta**: modified <capability>` ⇒ `<capability>`；未声明 ⇒ None。

    调用方（`phase0_approval.sh`）用它决定 delta 的落点目录（`specs/<capability>/`）。
    """
    raw = _head_field(text, "delta")
    if not raw:
        return None
    m = re.match(r"^(?:modified|added)\s+(.+)$", raw.strip(), re.IGNORECASE)
    return m.group(1).strip() if m else None


def _semantic_requirements(text: str) -> list[dict[str, str]]:
    """解析 `**语义要求**` 头行 ⇒ `[{requirement, body, scenario, when, then}]`。

    形态：`<requirement> | <body> | <scenario> | <WHEN> | <THEN>`，多条以 `;;` 分隔。
    解析不出（缺载体 / 字段不足）⇒ [] ⇒ 调用方**拒绝生成**并指名缺什么（不猜、不退化）。
    """
    raw = _head_field(text, "语义要求")
    if not raw:
        return []
    out: list[dict[str, str]] = []
    for chunk in raw.split(_SEMANTIC_SEP):
        parts = [p.strip() for p in chunk.split("|")]
        if len(parts) < 5 or not all(parts[:5]):
            continue
        out.append(
            dict(
                zip(
                    ("requirement", "body", "scenario", "when", "then"),
                    parts[:5],
                )
            )
        )
    return out


def _main_spec_block(capability: str, requirement: str) -> str | None:
    """从 main spec 复制 requirement 块（**含全部既有 Scenario**）；找不到 ⇒ None。"""
    path = _project_root() / "openspec" / "specs" / capability / "spec.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    m = re.search(
        rf"^### Requirement: {re.escape(requirement)}\s*$(.*?)(?=^### Requirement:|^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return m.group(0).strip() if m else None


def _compose_modified(main_block: str, req: dict[str, str]) -> str:
    """MODIFIED 块 = **作者的新正文** + **既有全部 Scenario** + **新增 Scenario**。

    ⚠ 既有 Scenario **一个都不能丢**：openspec 的 `specs-apply.js` 在归档时会比较
    「main spec 的场景名集合」与「delta 块的场景名集合」，缺一个就 abort
    （1.7.0+ 自带该检查；<1.7.0 由本仓的本地预检兜底）。
    """
    lines = main_block.split("\n")
    header = lines[0]
    rest = lines[1:]
    scen_idx = next(
        (i for i, line in enumerate(rest) if line.startswith("#### Scenario:")), len(rest)
    )
    scenarios = [line for line in rest[scen_idx:] if line.strip()]
    out = [header, "", req["body"], ""]
    if scenarios:
        out += scenarios
        out += [""]
    out += [
        f"#### Scenario: {req['scenario']}",
        "",
        f"- **WHEN** {req['when']}",
        f"- **THEN** {req['then']}",
        "",
    ]
    return "\n".join(out).rstrip()


def generate_spec_delta(source_md: str, sub: str) -> str:
    """生成 change-local spec delta（形态守卫 + 载体 + MODIFIED 语义）。

    载体（design D-1，**粗体头行**，与 ADR-0025 D6 的「头部」一致）::

        **delta**: modified <capability>
        **语义要求**: <requirement> | <body> | <scenario> | <WHEN> | <THEN>

    - **缺 `**语义要求**`** ⇒ 拒绝生成（指名缺什么）—— 绝不回退到 `acceptance-N` + 恒真 WHEN；
    - `**delta**: modified <cap>` ⇒ 输出 `## MODIFIED Requirements`，块内**逐字保留** main spec
      的既有 Scenario，并追加作者的新场景；
    - 否则 ⇒ `## ADDED Requirements`；
    - 产出后过**形态守卫**（与仓库守卫同一份判据）⇒ 命中退化形态即拒绝生成。
    """
    reqs = _semantic_requirements(source_md)
    if not reqs:
        raise ValueError(
            "缺少 **语义要求** 载体"
            "（`**语义要求**: <requirement> | <body> | <scenario> | <WHEN> | <THEN>`，"
            "多条以 ;; 分隔）⇒ 无法生成非退化 delta ⇒ 拒绝生成"
            "（不会产出 acceptance-N / capability-N / 恒真 WHEN）"
        )

    delta_field = _head_field(source_md, "delta")
    target = delta_target_capability(source_md)
    is_modified = bool(delta_field and target and delta_field.strip().lower().startswith("modified"))

    lines: list[str] = []
    if is_modified:
        assert target is not None  # for type-checkers
        lines += ["## MODIFIED Requirements", ""]
        for req in reqs:
            block = _main_spec_block(target, req["requirement"])
            if block is None:
                raise ValueError(
                    f"MODIFIED 目标 requirement 不存在：{target} :: {req['requirement']}"
                    " ⇒ 拒绝生成（MODIFIED 必须逐字保留既有 Scenario）"
                )
            lines.append(_compose_modified(block, req))
            lines.append("")
    else:
        lines += ["## ADDED Requirements", ""]
        for req in reqs:
            lines += [
                f"### Requirement: {req['requirement']}",
                "",
                req["body"],
                "",
                f"#### Scenario: {req['scenario']}",
                "",
                f"- **WHEN** {req['when']}",
                f"- **THEN** {req['then']}",
                "",
            ]

    out = "\n".join(lines).rstrip() + "\n"

    problems = describe_degradation(out)
    if problems:
        raise ValueError("delta 形态退化 ⇒ 拒绝生成：" + "；".join(problems))

    if not native_scenario_conservation_available():
        print(
            "⚠️  delta: 本机 openspec < 1.7.0（无原生「MODIFIED 须含既有 Scenario」检查）"
            " ⇒ 本地预检是唯一守卫",
            file=sys.stderr,
        )
    return out


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
    if os.environ.get("OUTPUT_MODE") == "spec-delta":
        # D3 delta output: openspec v1.4 change-local spec delta
        # (## MODIFIED / ## ADDED Requirements + Requirement + Scenario).
        print(generate_spec_delta(text, change_name))
    elif os.environ.get("OUTPUT_MODE") == "target-capability":
        # 只打印 delta 的目标 capability（`specs/<capability>/` 的落点决策用；空 = 未声明）。
        print(delta_target_capability(text) or "")
    else:
        print(generate_full_proposal(change_name, text))
