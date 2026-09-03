"""Read-only resolution of proposal name → OpenSpec change name.

Resolution priority (highest first):
  1. explicit_ref (from CLI --ref-change)
  2. improvement frontmatter 'change:' field
  3. basename equality (proposal name == change name)

This module does NOT mutate any file. Pure read.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml


class ResolutionError(Exception):
    """Raised when resolution cannot proceed (e.g. file unreadable)."""


def resolve_change_id(
    *,
    proposal: str,
    improvement_path: str,
    explicit_ref: Optional[str] = None,
) -> str:
    """Resolve proposal name to OpenSpec change name.

    Args:
        proposal: The proposal name (used as fallback).
        improvement_path: Absolute path to .rddf/improvements/<name>.md.
        explicit_ref: Optional explicit --ref-change value (highest priority).

    Returns:
        The resolved OpenSpec change name.

    Raises:
        ResolutionError: If improvement file is unreadable or frontmatter malformed.
    """
    if explicit_ref:
        return explicit_ref

    p = Path(improvement_path)
    if not p.exists():
        return proposal  # basename fallback even if file missing

    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return proposal

    # Extract frontmatter block
    try:
        end = text.index("\n---", 3)
        fm_block = text[3:end].lstrip("\n")
    except ValueError as exc:
        raise ResolutionError(
            f"Malformed frontmatter in {improvement_path}: no closing ---"
        ) from exc

    try:
        fm = yaml.safe_load(fm_block) or {}
    except yaml.YAMLError as exc:
        raise ResolutionError(
            f"YAML parse error in {improvement_path}: {exc}"
        ) from exc

    change = fm.get("change")
    if isinstance(change, str) and change:
        return change

    return proposal