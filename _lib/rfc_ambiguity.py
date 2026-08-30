"""Static ambiguity detection for RFC proposals (no LLM, fast, deterministic).

Detects 5 ambiguity kinds per phase-2-general-20260829063814 acceptance.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path

ACCEPTANCE_HDR_RE = re.compile(r"^## Acceptance\b", re.MULTILINE)
ACCEPTANCE_CHECKBOX_RE = re.compile(r"^\s*-\s*\[\s*\]", re.MULTILINE)
IN_SCOPE_HDR_RE = re.compile(r"^In Scope\s*:?\s*$", re.MULTILINE)
OUT_SCOPE_HDR_RE = re.compile(r"^Out\s*of\s*Scope\s*:?\s*$", re.MULTILINE | re.IGNORECASE)
LIST_ITEM_RE = re.compile(r"^\s*-\s+(.+?)\s*$", re.MULTILINE)
CROSS_REPO_HINT_RE = re.compile(r"\b(cross[- ]?repo|Hub|api-|cross-)\b", re.IGNORECASE)
HEDGE_WORDS_RE = re.compile(r"\b(maybe|probably|should\s+(probably|maybe)|might\s+be)\b", re.IGNORECASE)
ANY_HEADER_RE = re.compile(r"^##\s", re.MULTILINE)

SCOPE_THRESHOLD = 5


@dataclass
class Ambiguity:
    kind: str
    severity: str
    suggestion: str


def _extract_block(text, header_re):
    m = header_re.search(text)
    if not m:
        return ""
    start = m.end()
    rest = text[start:]
    stop = ANY_HEADER_RE.search(rest)
    return rest[: stop.start()] if stop else rest


def _list_items(block):
    return [m.group(1).strip() for m in LIST_ITEM_RE.finditer(block)]


def _first_n_words(text, n=100):
    words = re.findall(r"\b\w+\b", text)
    return " ".join(words[:n]).lower()


def detect_ambiguity(proposal_path):
    path = Path(proposal_path)
    if not path.exists():
        return [Ambiguity("missing_proposal", "block", f"proposal.md not found: {proposal_path}")]
    text = path.read_text(encoding="utf-8")

    out = []
    has_acc = bool(ACCEPTANCE_HDR_RE.search(text))
    has_checkbox = bool(ACCEPTANCE_CHECKBOX_RE.search(text))
    if not has_acc or not has_checkbox:
        out.append(Ambiguity(
            "missing_acceptance", "warn",
            "Add ## Acceptance section with >=3 `- [ ]` items.",
        ))

    in_scope_block = _extract_block(text, IN_SCOPE_HDR_RE)
    in_scope_items = _list_items(in_scope_block)

    if len(in_scope_items) > SCOPE_THRESHOLD:
        out.append(Ambiguity(
            "scope_overflow", "warn",
            f"In Scope has {len(in_scope_items)} items (>5). Consider splitting into sub-proposals.",
        ))

    out_scope_block = _extract_block(text, OUT_SCOPE_HDR_RE)
    out_scope_items = set(_list_items(out_scope_block))
    both = set(in_scope_items) & out_scope_items
    if both:
        out.append(Ambiguity(
            "contradiction", "block",
            f"Items appear in both In Scope and Out of Scope: {sorted(both)}.",
        ))

    if CROSS_REPO_HINT_RE.search(text) and ("api-" in text or "cross-" in text):
        out.append(Ambiguity(
            "multi_stakeholder", "info",
            "Detected cross-repo keywords; Hub RFC may be required (per ADR-0031).",
        ))

    head = _first_n_words(text, 100)
    if HEDGE_WORDS_RE.search(head) and not has_checkbox:
        out.append(Ambiguity(
            "vague", "warn",
            "Hedge words ('maybe', 'probably') combined with missing acceptance items.",
        ))

    return out