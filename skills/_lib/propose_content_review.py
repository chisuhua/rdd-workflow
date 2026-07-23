"""Proposal content review via single Oracle call.

Provides 4 quality checks on a proposal description:
  1. Scope clarity — is the In Scope / Out Scope boundary well-defined?
  2. ADR reference relevance — are the cited ADRs actually relevant?
  3. Acceptance criteria testability — can each criterion be objectively verified?
  4. Scope boundary reasonableness — are scope edges properly justified?

Output: structured JSON written to ``.rddf/state/propose-review.json``.

This module is optional (non-blocking, warning-level). Callers can skip
it via ``SKIP_CONTENT_REVIEW=yes``.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


REVIEW_DIMENSIONS = [
    "scope_clarity",
    "adr_relevance",
    "acceptance_criteria_testability",
    "scope_boundary_reasonableness",
]

DEFAULT_PATH = ".rddf/state/propose-review.json"


def build_oracle_prompt(proposal_description: str) -> str:
    """Build a single Oracle prompt requesting 4 structured checks.

    The prompt asks Oracle to evaluate each dimension on a 1-5 scale
    with evidence from the proposal text.
    """
    return f"""You are reviewing an OpenSpec proposal. Evaluate the following proposal description across 4 dimensions.

PROPOSAL DESCRIPTION:
---
{proposal_description}
---

For each dimension, respond with:
  - score (1-5, where 1=poor, 5=excellent)
  - evidence (quote from the description that supports this score)
  - suggestion (one concrete improvement if score < 4)

Dimensions:
1. scope_clarity: Is the "In Scope" / "Out Scope" boundary clearly defined?
2. adr_relevance: Are the cited ADR references actually relevant to this change?
3. acceptance_criteria_testability: Can each acceptance criterion be objectively verified?
4. scope_boundary_reasonableness: Are the scope edges properly justified?

Output format (JSON only, no preamble):
{{
  "scope_clarity": {{"score": int, "evidence": "...", "suggestion": "..."}},
  "adr_relevance": {{"score": int, "evidence": "...", "suggestion": "..."}},
  "acceptance_criteria_testability": {{"score": int, "evidence": "...", "suggestion": "..."}},
  "scope_boundary_reasonableness": {{"score": int, "evidence": "...", "suggestion": "..."}},
  "overall_rating": "pass|warning|fail",
  "summary": "2-3 sentence overall assessment"
}}"""


def parse_oracle_response(raw: str) -> Optional[Dict[str, Any]]:
    """Parse Oracle JSON response from raw string."""
    import json
    # Try to extract JSON block from response
    content = raw.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(line for line in lines if not line.startswith("```"))
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def write_review(
    review: Dict[str, Any],
    output_path: str = DEFAULT_PATH,
    change_name: str = "",
) -> None:
    """Write review results to output_path (creates dirs)."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "change_name": change_name,
        "dimensions": review,
        "overall_rating": review.get("overall_rating", "unknown"),
        "summary": review.get("summary", ""),
    }
    with path.open("w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def should_skip() -> bool:
    """Return True if SKIP_CONTENT_REVIEW=yes is set."""
    return os.environ.get("SKIP_CONTENT_REVIEW", "").lower() in ("yes", "1", "true")