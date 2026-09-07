"""`_lib.arch` — cross-stage shared analyzer data layer for rdd-arch.

Per ADR-0046 (arch-analyzer-protocol-subset) + `cross-stage-protocol-template.md`
Analyzer Subset: this package exposes pure functions consumed by the
`skills/rdd-arch/scripts/arch_gap_analysis.{sh,env.py}` Oracle C1 wrapper
per the template's §2 Data Layer convention.

Analyzer Subset declares:
  §1 SKILL.md § Protocol block       ADOPT
  §2 Data Layer (this file)          ADOPT
  §3 Staged Context File             SKIP (no agent consumer)
  §4 SHA-Bound Cache                 SKIP (no LLM verdict)
  §5 Output Contract Validation      ADOPT (structural=hard, completeness=advisory)

See ADR-0046 for the per-section justification.
"""
from __future__ import annotations

from .protocol import (
    REQUIRED_SECTIONS,
    PLACEHOLDER_PATTERNS,
    ValidationReport,
    build_skeleton,
    list_analyses,
    parse_slug,
    validate_document,
)

__all__ = [
    "REQUIRED_SECTIONS",
    "PLACEHOLDER_PATTERNS",
    "ValidationReport",
    "build_skeleton",
    "list_analyses",
    "parse_slug",
    "validate_document",
]