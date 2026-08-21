#!/usr/bin/env python3
"""
populate-roadmap-from-arch: Python helpers (Step 1-3: catalog / classify / generate_body).

Sourceable module: provides AdrRecord, ArchDocRecord, PhaseRecord dataclasses
and three main functions:
  - catalog_sources(project_root, arch_handoff): catalog ADR + arch docs + main doc phase skeleton
  - classify_adrs_by_phase(adrs, main_doc_phases): map ADR → phase_id
  - generate_phase_body(phase_id, classified_adrs, arch_docs, main_doc_themes): markdown body

Per skill metadata: version 1.0, evolved-from "manually-composed phase fragments during
add-hierarchical-roadmap-structure" (commit 51ca983).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ---- Dataclasses ----

@dataclass
class AdrRecord:
    """One ADR file's extracted metadata."""
    id: str                       # e.g. "ADR-0017"
    path: Path                    # relative path under docs/adr/
    title: str                    # first line after frontmatter
    status: str                   # e.g. "已采纳", "待定", "已采纳（v3.0 候选）", "已替代"
    key_decision: str             # one-sentence summary
    implementation_version: Optional[str] = None  # e.g. "v2.0.1+" from README 状态段

    def is_implemented(self) -> bool:
        """Whether this ADR has been implemented in code (per ADR README 状态段)."""
        if self.implementation_version:
            return True
        return self.status in {"已采纳", "已替代"}

    def is_placeholder_or_design(self) -> bool:
        """ADR-0009/0011/0012/0014/0015: '占位' / '设计稿' 状态."""
        return (
            "占位" in self.status
            or "设计稿" in self.status
            or "v3.0 候选" in self.status
        )


@dataclass
class ArchDocRecord:
    """One architecture doc's extracted summary."""
    path: Path                    # relative path under docs/architecture/
    title: str                    # first heading
    summary: str                  # first paragraph (≤ 200 chars)


@dataclass
class PhaseRecord:
    """One row of main doc phase skeleton table."""
    phase_id: str                 # e.g. "phase-1"
    theme: str                    # theme text
    status: str = "active"        # from Status column


@dataclass
class AdrCodeVerification:
    """Result of cross-checking an ADR's claimed implementation against actual code (v1.1+).

    verification_status values:
      - 'confirmed'               ADR claims impl + ≥80% symbols found
      - 'self-claim-only'         ADR claims impl + <80% symbols found (discrepancy)
      - 'placeholder-as-claimed'  ADR placeholder + 0 symbols found (no discrepancy)
      - 'placeholder-but-exists'  ADR placeholder + ≥1 symbol found (discrepancy)
    """
    adr_id: str
    self_claim_version: Optional[str]
    code_symbols_found: List[str]
    code_symbols_expected: List[str]
    verification_status: str
    has_discrepancy: bool
    verified_at: str  # ISO 8601
    mcp_used: bool


# ---- Step 1: catalog_sources ----

def _read_first_heading_and_summary(path: Path) -> Tuple[str, str]:
    """Extract first H1 heading + first paragraph (≤ 200 chars).

    Skips blockquote lines (>) when looking for summary.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    title = ""
    summary = ""
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        # skip code fences
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not title and re.match(r"^#\s+", stripped):
            title = stripped.lstrip("#").strip()
            continue
        if title and not summary and stripped and not stripped.startswith("#") and not stripped.startswith("|"):
            # Skip blockquote lines and frontmatter-style > notes
            if stripped.startswith(">"):
                continue
            # Skip metadata lines like **v3.0.0 note**: ...
            if re.match(r"^\*\*[^*]+\*\*[:：]", stripped):
                continue
            summary = stripped[:200]
            if len(stripped) > 200:
                summary += "..."
    return title, summary


def _extract_adr_status_and_decision(path: Path) -> Tuple[str, str]:
    """Extract ADR status (已采纳/待定/...) + first sentence of ## 关键决策 段.

    Supports two patterns:
    1. Inline: `状态: xxx` or `状态:xxx` on a single line, with optional markdown bold (**)
    2. Header: `## 状态` followed by `xxx` on next non-empty line
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    status = ""
    decision = ""

    # Pattern 1: inline 状态: xxx — allow optional ** around 状态
    m = re.search(r"\*{0,2}状态\*{0,2}\s*[:：]\s*(.+)", text)
    if m:
        status = m.group(1).strip().strip("*").strip()
        # Strip emoji like ✅ / ❌ / 🚧 prefix
        status = re.sub(r"^[✅❌🚧⚠️\s]+", "", status)

    # Pattern 2: header `## 状态` followed by content
    if not status:
        m = re.search(r"##\s+状态\s*\n+([^\n#]+)", text)
        if m:
            status = m.group(1).strip()

    # Find first non-empty paragraph after "## Decision" / "## 决策" / "## 关键决策" / "## 决定"
    m = re.search(r"##\s+(关键决策|Decision|决策|决定|关键决策[ ::])[\s\S]+?\n+([^#\n][^\n]+)", text)
    if m:
        decision = m.group(2).strip()[:200]
    else:
        # Fallback: take first non-empty paragraph after the first H2 section
        m = re.search(r"^##\s+[^\n]+\n+([^#\n][^\n]+)", text, re.MULTILINE)
        if m:
            decision = m.group(1).strip()[:200]

    return status, decision


def _parse_implementation_version(adr_id: str, readme_text: str) -> Optional[str]:
    """Look up ADR in ADR README 状态段; return version string like 'v2.0.1+'."""
    # Pattern: "已实施（v2.0.X+） | ADR-ID | ..." or similar.
    # Read README lines containing the ADR id, extract version from context.
    for line in readme_text.splitlines():
        if adr_id in line and ("v2." in line or "v3." in line):
            m = re.search(r"(v[23]\.\d+\.[\dx]+(?:\+)?)", line)
            if m:
                return m.group(1)
    return None


def _parse_main_doc_phase_skeleton(main_doc_path: Path) -> List[PhaseRecord]:
    """Parse .rddf/roadmap.md ## Phase Skeleton table → List[PhaseRecord]."""
    text = main_doc_path.read_text(encoding="utf-8", errors="replace")
    records: List[PhaseRecord] = []
    in_skeleton = False
    for line in text.splitlines():
        if re.match(r"^##\s+Phase Skeleton", line):
            in_skeleton = True
            continue
        if in_skeleton:
            if line.startswith("##"):
                break
            # match "| phase-N | theme | status | ... |"
            m = re.match(r"\|\s*(phase-\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
            if m:
                records.append(
                    PhaseRecord(
                        phase_id=m.group(1).strip(),
                        theme=m.group(2).strip(),
                        status=m.group(3).strip() or "active",
                    )
                )
    return records


def _import_scan_adr_catalog():
    """Import scan_adr_catalog across repo / external-project / global-install layouts."""
    try:
        from skills._lib.adr_catalog import scan_adr_catalog
        return scan_adr_catalog
    except ModuleNotFoundError:
        pass
    import sys
    lib_parent = str(Path(__file__).resolve().parents[2])
    if lib_parent not in sys.path:
        sys.path.insert(0, lib_parent)
    try:
        from skills._lib.adr_catalog import scan_adr_catalog
        return scan_adr_catalog
    except ModuleNotFoundError:
        from _lib.adr_catalog import scan_adr_catalog  # global-install layout
        return scan_adr_catalog


def catalog_sources(
    project_root: Path,
    adr_dir_rel: str = "docs/adr",
    arch_dir_rel: str = "docs/architecture",
    main_doc_rel: str = ".rddf/roadmap.md",
    arch_handoff_override: Optional[Path] = None,
) -> Tuple[List[AdrRecord], List[ArchDocRecord], List[PhaseRecord]]:
    """Catalog all source files for fragment body generation.

    Returns (adrs, arch_docs, main_doc_phases).
    """
    project_root = Path(project_root)

    # ADR-0016 v2 handoff can override defaults
    if arch_handoff_override is None:
        arch_handoff_path: Path = project_root / ".rddf/state/.arch-handoff.json"
    else:
        arch_handoff_path = arch_handoff_override

    if arch_handoff_path.exists():
        import json
        handoff = json.loads(arch_handoff_path.read_text(encoding="utf-8"))
        adr_dir_rel = handoff.get("adr_dir", adr_dir_rel)
        arch_dir_rel = handoff.get("architecture_dir", arch_dir_rel)
        # roadmap_path is the main doc; but we use main_doc_rel default
        # since main doc is .rddf/roadmap.md after migrate

    adr_dir = project_root / adr_dir_rel
    arch_dir = project_root / arch_dir_rel
    main_doc = project_root / main_doc_rel

    # ADR README 状态段（用于 implementation_version lookup）
    adr_readme = adr_dir / "README.md"
    readme_text = adr_readme.read_text(encoding="utf-8", errors="replace") if adr_readme.exists() else ""

    # ADR file discovery via shared layer; extraction stays local (v1.1 AdrRecord contract)
    scan_adr_catalog = _import_scan_adr_catalog()

    adrs: List[AdrRecord] = []
    for adr_id, adr_meta in scan_adr_catalog(project_root, adr_dir=adr_dir_rel).items():
        adr_file = adr_meta.file_path
        title, _ = _read_first_heading_and_summary(adr_file)
        if not title:
            title = adr_file.stem
        # Strip leading "ADR-NNNN: " prefix to avoid duplication when formatted
        title = re.sub(rf"^{re.escape(adr_id)}\s*[:：]\s*", "", title)
        status, decision = _extract_adr_status_and_decision(adr_file)
        version = _parse_implementation_version(adr_id, readme_text)
        adrs.append(
            AdrRecord(
                id=adr_id,
                path=adr_file.relative_to(project_root),
                title=title,
                status=status or "未知",
                key_decision=decision or "(无关键决策段)",
                implementation_version=version,
            )
        )

    # Catalog arch docs
    arch_docs: List[ArchDocRecord] = []
    if arch_dir.exists():
        for arch_file in sorted(arch_dir.glob("*.md")):
            if arch_file.name.lower() == "readme.md":
                continue
            title, summary = _read_first_heading_and_summary(arch_file)
            if not title:
                title = arch_file.stem
            arch_docs.append(
                ArchDocRecord(
                    path=arch_file.relative_to(project_root),
                    title=title,
                    summary=summary or "(无摘要)",
                )
            )

    # Main doc phase skeleton
    main_doc_phases: List[PhaseRecord] = []
    if main_doc.exists():
        main_doc_phases = _parse_main_doc_phase_skeleton(main_doc)

    return adrs, arch_docs, main_doc_phases


# ---- Step 2: classify_adrs_by_phase ----

# Phase theme keyword mapping (per main doc table)
_PHASE_KEYWORDS: Dict[str, List[str]] = {
    "phase-1": [
        "多会话", "rddf-session", "跨仓", "跨仓库", "联邦", "Hub", "Spoke",
        "issue", "提案", "proposal", "触发", "trigger", "scheduler",
    ],
    "phase-2": [
        "审批", "RFC", "design", "plan", "编排", "orchestration",
        "步骤", "skeleton", "per-skill", "manual_deps", "deps",
        "execution mode", "quality gate", "alignment", "metadata",
        "artifact discovery", "discovery",
    ],
    "phase-3": [
        "定制", "演进", "evolution", "反馈", "闭环", "自动发",
        "流程", "流程定制", "触发器", "步骤引擎", "定制层",
        "持续演进", "持续", "improvement",
    ],
    "phase-4": [
        "多方", "回归", "回归测试", "P1-P3", "Hub-and-Spoke",
        "cross-repo", "Federation", "Federation Deepening",
    ],
}


def classify_adrs_by_phase(
    adrs: List[AdrRecord],
    main_doc_phases: List[PhaseRecord],
) -> Dict[str, List[AdrRecord]]:
    """Map each ADR to one or more phase_ids based on theme keyword matching.

    Returns Dict[phase_id, List[AdrRecord]].
    ADRs that match no phase keywords go to phase-1 as default fallback.
    """
    result: Dict[str, List[AdrRecord]] = {p.phase_id: [] for p in main_doc_phases}

    for adr in adrs:
        haystack = f"{adr.title} {adr.key_decision}".lower()
        matched_phases: Set[str] = set()

        # 1. Try matching against main doc theme text first (highest priority)
        main_doc_themes_for_adr = [
            ph for ph in main_doc_phases
            if any(kw.lower() in haystack for kw in _theme_to_keywords(ph.theme))
        ]
        for ph in main_doc_themes_for_adr:
            matched_phases.add(ph.phase_id)

        # 2. Fallback to phase-keyword table
        if not matched_phases:
            for phase_id, keywords in _PHASE_KEYWORDS.items():
                if phase_id not in result:
                    continue
                if any(kw.lower() in haystack for kw in keywords):
                    matched_phases.add(phase_id)

        # 3. Default fallback to phase-1 if still no match
        if not matched_phases and "phase-1" in result:
            matched_phases.add("phase-1")

        for pid in matched_phases:
            if pid in result:
                result[pid].append(adr)

    return result


def _longest_chinese_token(chinese_tokens: List[str]) -> Optional[str]:
    """Return the longest Chinese token, used for 2-char sliding window extraction."""
    if not chinese_tokens:
        return None
    return max(chinese_tokens, key=len)


def _theme_to_keywords(theme: str) -> List[str]:
    """Extract keywords from a main doc theme string for ADR matching.

    Strategy:
    1. Strip parenthetical (A1/A2/A3) / (B1/B3/D2)
    2. Split by punctuation/whitespace
    3. For Chinese tokens: include whole token AND 2-char sliding windows
       (only for the longest Chinese token, to avoid noise from short tokens)
    4. For English/numeric: include whole tokens
    """
    cleaned = re.sub(r"\([^)]*\)", "", theme)
    keywords: List[str] = []
    chinese_tokens: List[str] = []

    raw_tokens = re.split(r"[\s,，、:：—\-/／]+", cleaned)
    for tok in raw_tokens:
        tok = tok.strip()
        if len(tok) < 2:
            continue
        if re.search(r"[\u4e00-\u9fff]", tok):
            chinese_tokens.append(tok)
            keywords.append(tok)
        else:
            if tok.lower() not in [k.lower() for k in keywords]:
                keywords.append(tok)

    longest = _longest_chinese_token(chinese_tokens)
    if longest and len(longest) >= 4:
        for i in range(len(longest) - 1):
            pair = longest[i:i + 2]
            if pair not in keywords:
                keywords.append(pair)

    return keywords


# ---- Step 3: generate_phase_body ----

def _adr_url(adr: AdrRecord) -> str:
    """Return ADR relative path as plain URL (no markdown syntax).

    Used as the link target in caller-formatted markdown links.
    """
    return "../../" + str(adr.path)


def _adr_link(adr: AdrRecord) -> str:
    """Return ADR as markdown link: [ADR-NNNN](../../docs/adr/...)."""
    return f"[{adr.id}]({_adr_url(adr)})"


def _arch_doc_link(arch_doc: ArchDocRecord) -> str:
    """Format arch doc as markdown link (relative to fragment: ../../docs/architecture/...)."""
    rel_path = "../../" + str(arch_doc.path)
    return f"[{arch_doc.title}]({rel_path})"


def _format_adr_block(
    adr: AdrRecord,
    project_root: Path,
    phase_id: str,
    verification: Optional["AdrCodeVerification"] = None,
) -> str:
    """Format one ADR as a bullet section under '## 已实施能力'.

    When verification is None (default), uses v1.0 marker (3 types).
    When verification is provided (v1.1+ --code-verify flag), chooses 1 of 4 new badges.
    """
    link = _adr_link(adr)
    if verification is not None:
        # v1.1+ verification badges
        status = verification.verification_status
        if status == "confirmed":
            status_badge = " " + _format_badge_confirmed(verification.self_claim_version or "v?")
        elif status == "self-claim-only":
            status_badge = " " + _format_badge_self_claim_only(verification.self_claim_version or "v?")
        elif status == "placeholder-but-exists":
            status_badge = " " + _format_badge_placeholder_but_exists()
        elif status == "placeholder-as-claimed":
            status_badge = " " + _format_badge_placeholder_as_claimed()
        else:
            status_badge = ""
    else:
        # v1.0 marker (backward compatible)
        status_badge = ""
        if adr.implementation_version:
            status_badge = f" *（已实施 {adr.implementation_version}）*"
        elif adr.is_placeholder_or_design():
            status_badge = " *（占位 / 未实施）*"
        elif adr.status == "待定":
            status_badge = " *（待定）*"

    decision = adr.key_decision[:200]
    return f"- **{adr.id}** — [{adr.title}]({_adr_url(adr)}){status_badge}\n  - {decision}"


def _strip_adr_id_prefix(title: str, adr_id: str) -> str:
    """Remove leading 'ADR-NNNN: ' or 'ADR-NNNN ' prefix from title to avoid duplication."""
    return re.sub(rf"^{re.escape(adr_id)}\s*[:：]\s*", "", title)


def _format_arch_doc_row(arch_doc: ArchDocRecord, phase_id: str) -> str:
    """Format one arch doc as a row in '## 架构文档锚点' table."""
    link = _arch_doc_link(arch_doc)
    summary = arch_doc.summary[:120].replace("|", "\\|").replace("\n", " ")
    if len(arch_doc.summary) > 120:
        summary += "..."
    return f"| {link} | {summary} |"


def _format_placeholder_block(adr: AdrRecord, project_root: Path, phase_id: str) -> str:
    """Format one placeholder ADR as a section under '## 占位 / 未实施'."""
    link = _adr_link(adr)
    return f"### {adr.id} — {adr.title}\n\n- **状态**：{adr.status}\n- **关键决策**：{adr.key_decision[:200]}\n- **阻碍**：需 ADR 正文实质化（脱掉占位/设计稿状态）+ 设计前置依赖\n- **后续**：\n  1. 更新 ADR 正文，列出具体决策点\n  2. 在 `add-improve` 流程中创建对应 implementation change\n  3. 经 design-done gate 进入 plan-done 后归档"


def _map_arch_docs_to_phase(arch_docs: List[ArchDocRecord], adrs_for_phase: List[AdrRecord]) -> List[ArchDocRecord]:
    """Filter arch docs relevant to a phase (heuristic: arch doc filename mentions phase)."""
    # Naive heuristic: if arch doc filename contains the phase number, include it.
    # Otherwise include all arch docs in phase-1 (broad overview).
    return arch_docs  # always include all; user can edit later


def generate_phase_body(
    phase_id: str,
    classified_adrs: Dict[str, List[AdrRecord]],
    arch_docs: List[ArchDocRecord],
    main_doc_phases: List[PhaseRecord],
    project_root: Path,
    related_archived_changes: Optional[List[str]] = None,
    next_phase_id: Optional[str] = None,
    verifications: Optional[Dict[str, "AdrCodeVerification"]] = None,
) -> str:
    """Generate markdown body for one phase fragment.

    Returns the body content (without frontmatter, ready to append after the
    existing frontmatter `---` closing line + blank line).

    When verifications is provided (v1.1+ --code-verify=on|strict), each ADR
    block emits a verification badge instead of the v1.0 marker.
    """
    adrs_for_phase = classified_adrs.get(phase_id, [])
    themes_for_phase = [ph.theme for ph in main_doc_phases if ph.phase_id == phase_id]

    implemented_adrs = [a for a in adrs_for_phase if a.is_implemented() and not a.is_placeholder_or_design()]
    placeholder_adrs = [a for a in adrs_for_phase if a.is_placeholder_or_design() or a.status == "待定"]

    lines: List[str] = []

    # 1. Overview
    lines.append(f"## {phase_id} 概览\n")
    if themes_for_phase:
        lines.append(
            f"Phase {phase_id.replace('phase-', '')} 覆盖 "
            f"{len(implemented_adrs)} 个已实施 ADR / "
            f"{len(placeholder_adrs)} 个占位或待定 ADR / "
            f"{len(arch_docs)} 个架构文档锚点。"
            f"按主文档 `## Phase Skeleton` 表格，本阶段包含 "
            f"{len(themes_for_phase)} 个并列 theme：\n"
        )
        lines.append("| Theme | ADR 覆盖 | 状态 |")
        lines.append("|-------|----------|------|")
        for theme in themes_for_phase:
            theme_adrs = [a for a in adrs_for_phase if any(kw.lower() in f"{a.title} {a.key_decision}".lower() for kw in _theme_to_keywords(theme))]
            if theme_adrs:
                adr_links = ", ".join(_adr_link(a) for a in theme_adrs[:3])
                if len(theme_adrs) > 3:
                    adr_links += f" +{len(theme_adrs)-3}"
            else:
                adr_links = "—"
            status = "已实施" if implemented_adrs and theme_adrs else ("占位/未实施" if placeholder_adrs and theme_adrs else "—")
            lines.append(f"| {theme} | {adr_links} | {status} |")
        lines.append("")

    # 2. Implemented capabilities
    if implemented_adrs:
        lines.append("## 已实施能力\n")
        for adr in implemented_adrs:
            v = verifications.get(adr.id) if verifications else None
            lines.append(_format_adr_block(adr, project_root, phase_id, verification=v))
            lines.append("")
    else:
        lines.append("## 已实施能力\n")
        lines.append("（本 phase 暂无已实施 ADR — 所有 ADR 都属于占位或待定状态）\n")

    # 3. Architecture anchors
    lines.append("## 架构文档锚点\n")
    if arch_docs:
        lines.append("| 文档 | 与本 phase 关联 |")
        lines.append("|------|----------------|")
        for arch_doc in _map_arch_docs_to_phase(arch_docs, adrs_for_phase):
            lines.append(_format_arch_doc_row(arch_doc, phase_id))
        lines.append("")
    else:
        lines.append("（本仓库暂无 `docs/architecture/*.md` 文档）\n")

    # 4. Placeholders / unimplemented
    lines.append("## 占位 / 未实施\n")
    if placeholder_adrs:
        for adr in placeholder_adrs:
            lines.append(_format_placeholder_block(adr, project_root, phase_id))
            lines.append("")
    else:
        lines.append("（本 phase 无占位或待定 ADR）\n")

    # 5. Theme registry mapping
    lines.append("## 主题注册表映射\n")
    if themes_for_phase:
        lines.append("主文档 `## Phase Skeleton` 表格中 " + phase_id + " 共 "
                     f"{len(themes_for_phase)} 行（{len(themes_for_phase)} 个 theme）。"
                     "本 fragment 是这些 theme 的 **聚合根**，单 fragment 多 theme 模式：\n")
        for idx, theme in enumerate(themes_for_phase, 1):
            lines.append(f"- \"{theme}\" → 阅上文 主题相关 ADR 段（已实施或占位）")
        lines.append("")
    else:
        lines.append(f"（主文档 phase skeleton 表格中未找到 {phase_id} 的 theme）\n")

    # 6. Related archived changes
    lines.append("## 相关变更历史\n")
    if related_archived_changes:
        for change in related_archived_changes:
            lines.append(f"- `{change}`")
        lines.append("")
    else:
        lines.append("（本阶段暂无直接相关的归档 change）\n")

    # 7. Next step
    lines.append("## 下一步\n")
    if next_phase_id:
        lines.append(f"Phase {phase_id.replace('phase-', '')} → [{next_phase_id}](../phases/{next_phase_id}.md)\n")
    else:
        lines.append("（本阶段为最终 phase，无下一步）\n")

    return "\n".join(lines).rstrip() + "\n"


# ---- Public API summary ----

__all__ = [
    "AdrRecord",
    "AdrCodeVerification",
    "ArchDocRecord",
    "PhaseRecord",
    "catalog_sources",
    "classify_adrs_by_phase",
    "generate_phase_body",
    "parse_symbols_from_adr_text",
    "verify_adr_by_code",
    "verify_all_adrs",
    "load_supplementary_or_default",
    "save_supplementary",
    # v2: incremental update (move-populate-roadmap-into-guide-arch, Task C)
    "load_populate_state_or_default",
    "save_populate_state",
    "detect_adr_changes",
    "detect_code_changes",
    "decide_update_mode",
    "select_adrs_for_incremental_verify",
    "should_rewrite_phase_fragment",
]


# ---- v1.1+: Code Verification Helpers ----

def parse_symbols_from_adr_text(adr_text: str) -> List[str]:
    """Extract code symbols from ADR prose, filtering fenced code blocks.

    Patterns:
      - backtick-quoted: `func()` / `ClassName` / `module.py`
      - Python definitions: `def func` / `class Class`
      - CLI flags: `--flag`
    """
    text_no_code = re.sub(r"```[\s\S]*?```", "", adr_text)

    symbols: List[str] = []
    for m in re.finditer(r"`([^`]+)`", text_no_code):
        sym = m.group(1).strip()
        if sym:
            symbols.append(sym)

    for m in re.finditer(r"\b(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", text_no_code):
        symbols.append(m.group(1))

    for m in re.finditer(r"--([a-z][a-z0-9-]+)", text_no_code):
        symbols.append(f"--{m.group(1)}")

    seen = set()
    deduped: List[str] = []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def _try_mcp_search(symbol: str, project_root: Path) -> Optional[bool]:
    """Try codebase-memory-mcp if available; return None on unavailable (fallback to grep)."""
    try:
        if not (project_root / ".codebase-memory").exists():
            return None
        return None
    except Exception:
        return None


def _grep_symbol(symbol: str, project_root: Path) -> bool:
    """Grep for symbol in source files (skip .git, .venv, node_modules, .rddf).

    Uses ripgrep (rg) if available, falls back to grep.
    """
    import subprocess
    rg_cmd = ["rg", "-l", "--type", "py", "--type", "sh", "--type", "ts",
              "--glob", "!skills/_lib", "--glob", "!.rddf",
              "--glob", "!.git", "--glob", "!.venv", "--glob", "!node_modules",
              "-F", "--", symbol, str(project_root)]
    try:
        result = subprocess.run(rg_cmd, capture_output=True, timeout=5, text=True)
        return bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    grep_cmd = [
        "grep", "-r", "-l", "--include=*.py", "--include=*.sh", "--include=*.ts",
        "--exclude-dir=.git", "--exclude-dir=.venv", "--exclude-dir=node_modules",
        "--exclude-dir=.rddf", "--exclude-dir=skills/_lib",
        "-F", symbol, str(project_root),
    ]
    try:
        result = subprocess.run(grep_cmd, capture_output=True, timeout=10, text=True)
        return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _grep_symbols_batch(symbols: List[str], project_root: Path) -> set:
    """Grep many symbols in one ripgrep pass; return set of symbols found.

    Uses `rg -e pat1 -e pat2 ...` to match any pattern in a single process,
    then for each matched file, checks which symbols appear in its content.
    """
    import subprocess
    if not symbols:
        return set()
    cmd = ["rg", "-l", "--type", "py", "--type", "sh", "--type", "ts",
           "--glob", "!skills/_lib", "--glob", "!.rddf",
           "--glob", "!.git", "--glob", "!.venv", "--glob", "!node_modules",
           "-F"]
    for s in symbols:
        cmd += ["-e", s]
    cmd.append(str(project_root))
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=15, text=True)
        files_with_match = result.stdout.strip().splitlines()
        if not files_with_match:
            return set()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return set()

    found = set()
    remaining = set(symbols)
    for f in files_with_match:
        if not remaining:
            break
        try:
            content = Path(f).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for sym in list(remaining):
            if sym in content:
                found.add(sym)
                remaining.discard(sym)
    return found


def verify_adr_by_code(adr: AdrRecord, adr_text: str, project_root: Path) -> AdrCodeVerification:
    """Verify ADR's self-claim against actual code symbols via mcp→grep fallback.

    Logic:
      placeholder + ≥1 found → placeholder-but-exists (discrepancy)
      placeholder + 0 found  → placeholder-as-claimed (no discrepancy)
      impl      + ≥80% found  → confirmed (no discrepancy)
      impl      + <80% found  → self-claim-only (discrepancy)
    """
    from datetime import datetime, timezone

    symbols = parse_symbols_from_adr_text(adr_text)
    found: List[str] = []
    mcp_used = False

    if symbols:
        found_set = _grep_symbols_batch(symbols, project_root)
        found = [s for s in symbols if s in found_set]

    is_placeholder = adr.is_placeholder_or_design() or adr.implementation_version is None

    if is_placeholder:
        if found:
            status = "placeholder-but-exists"
            has_discrepancy = True
        else:
            status = "placeholder-as-claimed"
            has_discrepancy = False
    else:
        coverage = len(found) / len(symbols) if symbols else 1.0
        if coverage >= 0.80:
            status = "confirmed"
            has_discrepancy = False
        else:
            status = "self-claim-only"
            has_discrepancy = True

    return AdrCodeVerification(
        adr_id=adr.id,
        self_claim_version=adr.implementation_version,
        code_symbols_found=found,
        code_symbols_expected=symbols,
        verification_status=status,
        has_discrepancy=has_discrepancy,
        verified_at=datetime.now(timezone.utc).isoformat(),
        mcp_used=mcp_used,
    )


def verify_all_adrs(
    adr_inputs: List[Tuple["AdrRecord", str, Path]],
    max_workers: int = 4,
) -> List[AdrCodeVerification]:
    """Verify multiple ADRs in parallel using ThreadPoolExecutor."""
    from concurrent.futures import ThreadPoolExecutor

    if not adr_inputs:
        return []
    results: List[AdrCodeVerification] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(verify_adr_by_code, adr, text, root)
            for (adr, text, root) in adr_inputs
        ]
        for fut in futures:
            results.append(fut.result())
    return results


def load_supplementary_or_default(project_root: Path) -> Dict[str, Dict]:
    """Load supplementary verification records from disk; return {} if missing/invalid."""
    state_file = project_root / ".rddf" / "state" / ".populate-supplementary.json"
    if not state_file.exists():
        return {}
    try:
        import json as _json
        data = _json.loads(state_file.read_text(encoding="utf-8"))
        if data.get("version") != 1:
            return {}
        return {r["adr_id"]: r for r in data.get("records", [])}
    except (ValueError, KeyError, OSError):
        return {}


def save_supplementary(
    records: List[AdrCodeVerification],
    project_root: Path,
) -> Path:
    """Atomically write supplementary records to .rddf/state/.populate-supplementary.json (schema v1)."""
    import json as _json
    import os
    import tempfile
    from datetime import datetime, timezone

    state_dir = project_root / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    target = state_dir / ".populate-supplementary.json"

    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": [
            {
                "adr_id": r.adr_id,
                "self_claim_version": r.self_claim_version,
                "verification_status": r.verification_status,
                "code_symbols_found": r.code_symbols_found,
                "code_symbols_expected": r.code_symbols_expected,
                "has_discrepancy": r.has_discrepancy,
                "verified_at": r.verified_at,
                "mcp_used": r.mcp_used,
            }
            for r in records
        ],
    }

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "_lib" / "schemas" / "populate_supplementary_schema.json"
    )
    if schema_path.exists():
        try:
            import jsonschema as _js
            _js.validate(payload, _json.loads(schema_path.read_text(encoding="utf-8")))
        except ImportError:
            pass
        except Exception as e:
            if type(e).__name__ == "ValidationError":
                raise RuntimeError(
                    f"populate_supplementary payload failed schema v1 validation: {e}"
                )
            raise

    fd, tmp_path = tempfile.mkstemp(dir=state_dir, suffix=".tmp", prefix=".populate-supplementary.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            _json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, target)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return target


def _format_badge_confirmed(claim_version: str) -> str:
    return f"*（已实施 {claim_version} + 代码验证）*"


def _format_badge_self_claim_only(claim_version: str) -> str:
    return f"*（已实施 {claim_version} 仅自报）*"


def _format_badge_placeholder_but_exists() -> str:
    return "*（占位 + 代码已现 ⚠️）*"


def _format_badge_placeholder_as_claimed() -> str:
    return "*（占位 + 代码未现）*"


# ---- v2: Incremental Update (move-populate-roadmap-into-guide-arch, Task C) ----
#
# Four-mode incremental roadmap update backed by .rddf/state/.populate-state.json
# (schema v2). The codegraph signal is env-var injected (RDDF_CODEGRAPH_FINGERPRINT);
# Python NEVER calls MCP directly (subprocess has no MCP session).

_POPULATE_STATE_REL = Path(".rddf") / "state" / ".populate-state.json"
_POPULATE_STATE_SCHEMA_VERSION = 2


def _populate_state_schema_path() -> Path:
    """Locate populate_state_schema.json next to this module's skills/ tree."""
    return (
        Path(__file__).resolve().parents[2]
        / "_lib" / "schemas" / "populate_state_schema.json"
    )


def _validate_populate_state_payload(payload: Dict) -> Optional[str]:
    """Validate a state payload against schema v2; return error message or None.

    Uses jsonschema when available; otherwise falls back to a manual check of
    the required top-level keys + version const (stdlib-only path).
    """
    schema_path = _populate_state_schema_path()
    if schema_path.exists():
        try:
            import json as _json
            import jsonschema as _js
            _js.validate(payload, _json.loads(schema_path.read_text(encoding="utf-8")))
            return None
        except ImportError:
            pass  # fall through to manual check
        except Exception as e:
            if type(e).__name__ == "ValidationError":
                return str(e)
            raise
    required = {"version", "generated_at", "codebase_commit", "adrs", "reverse_index", "phases"}
    missing = required - set(payload.keys())
    if missing:
        return f"missing required keys: {sorted(missing)}"
    if payload.get("version") != _POPULATE_STATE_SCHEMA_VERSION:
        return f"version != {_POPULATE_STATE_SCHEMA_VERSION}"
    return None


def load_populate_state_or_default(project_root: Path) -> Optional[Dict]:
    """Load .rddf/state/.populate-state.json; return None on missing/invalid.

    Fail-loud on schema version mismatch: prints
    `schema version X unsupported, expected 2` to stderr and returns None so
    the caller falls back to full mode (T9).
    """
    import json
    import sys

    state_file = Path(project_root) / _POPULATE_STATE_REL
    if not state_file.exists():
        return None
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        print(f"populate-state unreadable ({e}); falling back to full mode", file=sys.stderr)
        return None

    version = data.get("version")
    if version != _POPULATE_STATE_SCHEMA_VERSION:
        print(
            f"schema version {version} unsupported, expected {_POPULATE_STATE_SCHEMA_VERSION}",
            file=sys.stderr,
        )
        return None

    error = _validate_populate_state_payload(data)
    if error is not None:
        print(f"populate-state failed schema validation: {error}", file=sys.stderr)
        return None
    return data


def save_populate_state(state: Dict, project_root: Path, codebase_commit: str) -> Path:
    """Atomically write state to .rddf/state/.populate-state.json (schema v2).

    Fills version/generated_at defaults, injects codebase_commit, validates
    against the schema before writing, and uses tempfile + os.replace so a
    crash never leaves a torn write.
    """
    import json
    import os
    import tempfile
    from datetime import datetime, timezone

    project_root = Path(project_root)
    state_dir = project_root / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    target = state_dir / ".populate-state.json"

    payload = dict(state)
    payload["version"] = _POPULATE_STATE_SCHEMA_VERSION
    payload["codebase_commit"] = codebase_commit
    payload.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    payload.setdefault("codegraph_fingerprint", None)
    payload.setdefault("adrs", {})
    payload.setdefault("reverse_index", {})
    payload.setdefault("phases", {})

    error = _validate_populate_state_payload(payload)
    if error is not None:
        raise RuntimeError(f"populate-state payload failed schema v2 validation: {error}")

    fd, tmp_path = tempfile.mkstemp(dir=state_dir, suffix=".tmp", prefix=".populate-state.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, target)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return target


def detect_adr_changes(
    state: Dict,
    project_root: Path,
    scan_adr_catalog_fn,
) -> Tuple[List[str], List[str], List[str]]:
    """Compare current ADR file_hashes vs state['adrs']; return (changed, new, deleted).

    scan_adr_catalog_fn is injected (shared layer `_lib/adr_catalog.scan_adr_catalog`)
    so tests can substitute fakes. Comparison is sha256 file_hash based.
    """
    prev = (state or {}).get("adrs", {})
    current = scan_adr_catalog_fn(Path(project_root))

    prev_ids = set(prev.keys())
    cur_ids = set(current.keys())
    new = sorted(cur_ids - prev_ids)
    deleted = sorted(prev_ids - cur_ids)
    changed = sorted(
        adr_id
        for adr_id in (prev_ids & cur_ids)
        if prev[adr_id].get("file_hash") != current[adr_id].file_hash
    )
    return changed, new, deleted


def _git_commit_exists(project_root: Path, commit: str) -> bool:
    import subprocess

    result = subprocess.run(
        ["git", "-C", str(project_root), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
    )
    return result.returncode == 0


def _git_diff_name_only(project_root: Path, base_commit: str) -> List[str]:
    import subprocess

    result = subprocess.run(
        ["git", "-C", str(project_root), "diff", f"{base_commit}..HEAD", "--name-only"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _extract_symbol_defs(file_path: Path) -> Set[str]:
    """Extract top-level symbol definitions (def/class/function) from a source file.

    Prefers ripgrep `^(def|class|function) `; falls back to a Python regex pass
    when rg is unavailable. Stdlib-only subprocess (never shell=True).
    """
    import subprocess

    pattern = r"^(def|class|function)\s+([A-Za-z_][A-Za-z0-9_]*)"
    lines: List[str] = []
    try:
        result = subprocess.run(
            ["rg", "--no-filename", "-e", r"^(def|class|function) ", str(file_path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            lines = result.stdout.splitlines()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    if not lines:
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return set()

    symbols: Set[str] = set()
    for line in lines:
        m = re.match(pattern, line.strip())
        if m:
            symbols.add(m.group(2))
    return symbols


def detect_code_changes(
    state: Dict,
    project_root: Path,
) -> Tuple[Set[str], List[str], str]:
    """Detect code changes since state['codebase_commit']; return (changed_adr_ids, changed_files, status).

    status values:
      - 'ok'             git baseline valid, diff computed
      - 'stale'          RDDF_CODEGRAPH_FINGERPRINT=stale (env-var injected signal;
                         Python never calls MCP — the agent side injects this)
      - 'commit-missing' state['codebase_commit'] not found in git history
                         (force-push / gc) — caller falls back to full mode (T13)

    changed_adr_ids is the intersection of changed symbol definitions with
    state['reverse_index'] (symbol -> [adr_id]).
    """
    import os
    import sys

    project_root = Path(project_root)
    fingerprint = os.environ.get("RDDF_CODEGRAPH_FINGERPRINT", "")
    status = "stale" if fingerprint == "stale" else "ok"

    commit = (state or {}).get("codebase_commit", "")
    if not commit or not _git_commit_exists(project_root, commit):
        print(
            f"warning: codebase_commit {commit!r} not found in git history; "
            "falling back to full mode",
            file=sys.stderr,
        )
        return set(), [], "commit-missing"

    changed_files = _git_diff_name_only(project_root, commit)

    changed_symbols: Set[str] = set()
    for rel in changed_files:
        if not rel.endswith(".py"):
            continue
        file_path = project_root / rel
        if not file_path.is_file():
            continue
        changed_symbols |= _extract_symbol_defs(file_path)

    reverse_index = (state or {}).get("reverse_index", {})
    changed_adr_ids: Set[str] = set()
    for symbol in changed_symbols:
        changed_adr_ids.update(reverse_index.get(symbol, []))

    return changed_adr_ids, changed_files, status


def decide_update_mode(
    adr_changes: Tuple[List[str], List[str], List[str]],
    code_changes: Tuple[Set[str], List[str], str],
) -> Tuple[str, str, Optional[object]]:
    """Map (adr_changes, code_changes) to (mode, reason, extra).

    mode ∈ {skip, adr_only, code_only, full}:
      (empty, empty)     -> skip      (extra=None)
      (some, empty)      -> adr_only  (extra=sorted changed+new+deleted adr ids)
      (empty, some)      -> code_only (extra=set of changed adr ids)
      (some, some)       -> full      (extra=None)
    Any code_changes status != 'ok' (stale codegraph / missing commit) -> full.
    """
    changed, new, deleted = adr_changes
    changed_adr_ids, changed_files, status = code_changes

    if status != "ok":
        reason = "codegraph stale" if status == "stale" else f"git baseline invalid ({status})"
        return "full", reason, None

    adr_changed = bool(changed or new or deleted)
    code_changed = bool(changed_adr_ids or changed_files)

    if not adr_changed and not code_changed:
        return "skip", "no changes", None
    if adr_changed and not code_changed:
        return "adr_only", "only ADR changed", sorted(set(changed) | set(new) | set(deleted))
    if code_changed and not adr_changed:
        return "code_only", "only code changed", set(changed_adr_ids)
    return "full", "both changed", None


def _normalize_adr_ids(adrs) -> List[str]:
    """Accept a list of adr ids, a dict keyed by adr id, or records with .id/.adr_id."""
    if isinstance(adrs, dict):
        return list(adrs.keys())
    ids: List[str] = []
    for item in adrs or []:
        if isinstance(item, str):
            ids.append(item)
        elif hasattr(item, "id"):
            ids.append(item.id)
        elif hasattr(item, "adr_id"):
            ids.append(item.adr_id)
    return ids


def select_adrs_for_incremental_verify(
    adrs,
    state: Dict,
    mode: str,
    extra,
) -> Tuple[List[str], Dict]:
    """Split ADRs into (to_verify, to_reuse) for the given update mode.

    skip:      verify nothing, reuse all previous state.adrs
    adr_only:  verify extra (changed/new/deleted adr ids), reuse the rest
    code_only: verify extra (adr ids, or symbols resolved via reverse_index), reuse the rest
    full:      verify all adrs, reuse nothing
    """
    all_ids = _normalize_adr_ids(adrs)
    prev = dict((state or {}).get("adrs", {}))

    if mode == "skip":
        return [], prev
    if mode == "full":
        return list(all_ids), {}

    reverse_index = (state or {}).get("reverse_index", {})
    known = set(all_ids) | set(prev.keys())
    to_verify: List[str] = []
    for item in (extra or []):
        if item in known:
            candidates = [item]
        else:
            candidates = list(reverse_index.get(item, []))
        for adr_id in candidates:
            if adr_id not in to_verify:
                to_verify.append(adr_id)
    to_verify.sort()

    to_reuse = {k: v for k, v in prev.items() if k not in set(to_verify)}
    return to_verify, to_reuse


def should_rewrite_phase_fragment(
    phase_id: str,
    prev_state: Optional[Dict],
    new_state: Optional[Dict],
    mode: str,
) -> bool:
    """Whether the phase fragment must be regenerated.

    full / adr_only -> True (fragment may reference new or changed ADRs).
    skip / code_only -> False (v1 simplification: code changes do not alter
    phase fragment content; fragments from the previous state are preserved).
    """
    return mode in ("full", "adr_only")
