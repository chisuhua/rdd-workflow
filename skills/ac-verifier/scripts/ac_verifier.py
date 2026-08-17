"""AC verifier main module."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Section header (Chinese + English variants per brainstorming Q6)
_AC_SECTION_HEADERS = re.compile(
    r"^##\s+(?:验收标准|Acceptance Criteria)\s*$", re.MULTILINE
)
# Section-end pattern: next `## ` header or end-of-file
_SECTION_END = re.compile(r"^##\s+", re.MULTILINE)
# Bullet line: `- ...` or `- [ ] ...` or `- [x] ...`
_BULLET_LINE = re.compile(r"^- (?:\[([ x])\]\s+)?(.+)$")


class AcVerifierError(Exception):
    """Base error for ac_verifier operations."""


def parse_acs(proposal_path: Path) -> list[dict]:
    """Extract AC bullets from `## 验收标准` (or `## Acceptance Criteria`) section.

    Returns list of {ac_id: 'AC-N', description: str, has_checkbox: bool}.
    Empty list if section missing or has no bullets.
    """
    if not proposal_path.is_file():
        return []
    text = proposal_path.read_text(encoding="utf-8")

    # Find AC section start
    section_match = _AC_SECTION_HEADERS.search(text)
    if not section_match:
        return []

    # Find section end (next ## header)
    section_start = section_match.end()
    section_end_match = _SECTION_END.search(text, pos=section_start)
    section_end = section_end_match.start() if section_end_match else len(text)
    section_text = text[section_start:section_end]

    # Extract bullets
    acs: list[dict] = []
    for line in section_text.splitlines():
        m = _BULLET_LINE.match(line.strip())
        if not m:
            continue
        marker = m.group(1)  # " ", "x", or None (None for prose bullets)
        description = m.group(2).strip()
        has_checkbox = marker in (" ", "x")
        acs.append({
            "ac_id": f"AC-{len(acs) + 1}",
            "description": description,
            "has_checkbox": has_checkbox,
        })
    return acs