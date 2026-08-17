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


# Preamble constants (top of module, after imports)
_SYSTEM_PROMPT_TEMPLATE = """You are an AC verification agent for rdd-workflow. Given an OpenSpec change's
acceptance criteria (ACs) and access to code investigation tools, you must
determine whether each AC is genuinely satisfied in the committed code.

Available tools:
- codegraph_explore(query): structural code search via knowledge graph
- grep_app_searchGitHub(query, path?, language?): pattern matching
- codebase-memory-mcp: function/class/import lookup (via MCP)
- git log / git diff (subprocess via your driver): commit history

For each AC, you MUST:
1. Make at least one tool call to gather evidence
2. Cross-reference AC text against actual implementation
3. Issue verdict: "pass" (genuinely satisfied) | "fail" (not satisfied) |
   "partial" (partially satisfied with caveats)
4. Provide 0.0-1.0 confidence score
5. Cite evidence in 1-2 sentences

Output format (strict JSON array, no other text):
[
  {{
    "ac_id": "AC-1",
    "description": "<verbatim AC text>",
    "status": "pass" | "fail" | "partial",
    "confidence": 0.0-1.0,
    "evidence": [
      {{"tool": "codegraph", "query": "...", "result_summary": "..."}}
    ],
    "reasoning": "1-2 sentences justifying verdict"
  }}
]

Array length MUST equal AC count. Omitting any AC invalidates response.
"""


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


def build_agent_prompt(acs: list[dict], change_name: str) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) pair for LLM.

    System prompt declares tools + JSON schema; user prompt lists ACs.
    """
    user_lines = [
        f"Change: {change_name}",
        "",
        f"Number of ACs to verify: {len(acs)}",
        "",
        "Acceptance Criteria:",
    ]
    for ac in acs:
        user_lines.append(f"\n{ac['ac_id']}: {ac['description']}")
    user_lines.append(
        "\nFor each AC above, investigate using the declared tools and emit "
        "your verdict as a strict JSON array (one entry per AC)."
    )
    user_prompt = "\n".join(user_lines)
    return _SYSTEM_PROMPT_TEMPLATE, user_prompt