"""Pure-Python data layer for rdd-arch gap analysis (Analyzer Subset §2).

Per ADR-0046 + `cross-stage-protocol-template.md` Analyzer Subset, this
module exports 3 pure functions + 1 dataclass consumed by the
Oracle C1 wrapper at `skills/rdd-arch/scripts/arch_gap_analysis.{sh,env.py}`.

Output contract:
  - `build_skeleton` produces markdown **byte-identical** to the pre-refactor
    bash heredoc (Oracle risk #3: existing 8 bats lock the wrapper contract).
  - `validate_document` checks the 5-section structure (hard, deterministic)
    + detects placeholder content (advisory, never blocks).
  - `list_analyses` enumerates gap documents sorted by slug (kebab-case).
  - `parse_slug` enforces kebab-case (closes Oracle concern #3: slug
    validation gap that the refactor naturally fills).

No LLM call, no SHA-bound cache, no staged context file (Analyzer Subset
§3/§4 are explicitly SKIP per ADR-0046).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


REQUIRED_SECTIONS: tuple[str, ...] = (
    "## 1. 目标架构",
    "## 2. 当前架构",
    "## 3. 差距清单",
    "## 4. 补齐路径",
    "## 5. 参考资料",
)

# Regex anchors each section to the START of a line, preventing substring
# matches like "## 3. 差距清单" being found inside "### 3. 差距清单".
_REQUIRED_SECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"^{re.escape(s)}\s*$", re.MULTILINE) for s in REQUIRED_SECTIONS
)

# Patterns that indicate a section still has its template placeholder.
# Counted for advisory `completeness` classification only — never blocking.
PLACEHOLDER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\(待补充\)"),
    re.compile(r"\(描述[^)]*\)"),
    re.compile(r"^\| 1 \| \.\.\. \|", re.MULTILINE),
    re.compile(r"^- 相关 ADR\s*$", re.MULTILINE),
)

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

Completeness = Literal["draft", "partial", "complete"]


@dataclass
class ValidationReport:
    """Output contract validation result for a gap analysis document.

    Two-tier semantics (per ADR-0046 §5 REPURPOSE):
      - `structural_ok` is HARD: deterministic check that all 5 required
        sections are present at the expected heading levels. Failures here
        indicate generator drift and SHOULD block.
      - `completeness` is ADVISORY: how much of the skeleton the human
        curator has filled in (`draft` / `partial` / `complete`). Never
        blocks — humans curate asynchronously.

    Attributes:
      structural_ok: True iff all REQUIRED_SECTIONS are present.
      completeness: "draft" if all placeholders intact, "complete" if
        none remain, "partial" otherwise.
      issues: Human-readable list of structural problems (empty when ok).
    """

    structural_ok: bool
    completeness: Completeness
    issues: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        # Allow `if validate_document(path): ...` to test structural_ok.
        return self.structural_ok


def parse_slug(slug: str) -> str:
    """Validate and return the slug unchanged. Raises ValueError if not kebab-case.

    Per Oracle concern #3: closes the slug format validation gap that the
    pre-refactor bash wrapper left open (accepted any non-empty slug).
    """
    if not slug:
        raise ValueError("slug must be non-empty")
    if not _SLUG_RE.match(slug):
        raise ValueError(
            f"slug must be kebab-case (lowercase alphanumeric segments "
            f"joined by single hyphens): {slug!r}"
        )
    return slug


_SKELETON_TEMPLATE = """# 架构差距分析: {slug}

> **生成日期**: {today}
> **状态**: 草案
> **关联 ADR**: (待补充)

## 1. 目标架构

(描述 ADR 中定义的目标架构)

## 2. 当前架构

(描述项目当前实际架构)

## 3. 差距清单

| # | 差距项 | 严重程度 | 优先级 | 关联 change |
|---|--------|---------|--------|------------|
| 1 | ... | 高/中/低 | P0/P1/P2 | ... |

## 4. 补齐路径

(描述从当前架构迁移到目标架构的步骤、顺序、依赖)

## 5. 参考资料

- 相关 ADR
- 相关 change artifacts
"""


def build_skeleton(slug: str, today_iso: str = "") -> str:
    """Return the gap-analysis markdown skeleton for the given slug.

    Output is byte-identical to the pre-refactor bash heredoc at
    `git show HEAD:skills/rdd-arch/scripts/arch_gap_analysis.sh` lines 28-57
    (Oracle risk #3: existing bats tests lock the wrapper contract).

    Args:
      slug: kebab-case slug (validated via parse_slug).
      today_iso: ISO-8601 date string. Empty string → use placeholder.

    Raises:
      ValueError: if slug is not kebab-case.
    """
    parse_slug(slug)
    return _SKELETON_TEMPLATE.format(slug=slug, today=today_iso)


def validate_document(path: Path) -> ValidationReport:
    """Validate a gap analysis document against the 5-section output contract.

    Args:
      path: Absolute or project-relative path to the gap analysis file.

    Returns:
      ValidationReport with `structural_ok` (hard), `completeness`
      (advisory), and `issues` (structural problems list).
    """
    text = Path(path).read_text(encoding="utf-8")
    issues: list[str] = []

    for section, pattern in zip(REQUIRED_SECTIONS, _REQUIRED_SECTION_PATTERNS):
        if not pattern.search(text):
            issues.append(f"missing required section: {section}")

    placeholder_hits = sum(
        len(p.findall(text)) for p in PLACEHOLDER_PATTERNS
    )

    structural_ok = len(issues) == 0

    if placeholder_hits >= 4:
        completeness: Completeness = "draft"
    elif placeholder_hits == 0:
        completeness = "complete"
    else:
        completeness = "partial"

    return ValidationReport(
        structural_ok=structural_ok,
        completeness=completeness,
        issues=issues,
    )


def list_analyses(arch_dir: Path) -> list[Path]:
    """List existing gap analysis documents in `arch_dir`, sorted by slug.

    Only files matching `<slug>-gap-analysis.md` are returned. Non-matching
    files (e.g. README.md, historical-evolution.md) are excluded.

    Returns an empty list if `arch_dir` does not exist or contains no
    gap analyses.
    """
    arch_dir = Path(arch_dir)
    if not arch_dir.is_dir():
        return []
    return sorted(arch_dir.glob("*-gap-analysis.md"))