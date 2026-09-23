"""LLM Verification Protocol data layer for rdd-verifier v2.0.

Per ADR-0045 (inline-ac-verifier-into-rdd-verifier) + change verifier-v2-hardening
(oracle follow-up, ses_f8610cbf6ffeVLcEjlRw3s2COt):
- AC extraction rules migrated from skills/ac-verifier/scripts/ac_verifier.py
  (parse_acs) so the protocol lives in the verifier data layer, not in the
  deprecated ac-verifier skill.
- build_verification_context() stages a JSON context file that the executing
  AI agent reads before performing verification per
  skills/rdd-verifier/SKILL.md § "LLM Verification Protocol".
- validate_verdict_completeness() enforces verdict-length-equals-AC-count
  (P1 fix per oracle risk #1; without this, agent writing [AC-1 pass] for a
  5-AC proposal silently passes archive_gate_check).

The executing AI agent IS the LLM (v2.0 core design decision). This module
only prepares structured inputs; it never invokes an LLM.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Section header (Chinese + English variants) — identical to ac_verifier.py
# so caches and fixtures remain interoperable during the shim window.
_AC_SECTION_HEADERS = re.compile(
    r"^##\s+(?:验收标准|Acceptance Criteria|Acceptance)\s*$", re.MULTILINE
)
_SECTION_END = re.compile(r"^##\s+", re.MULTILINE)
_BULLET_LINE = re.compile(r"^- (?:\[([ x])\]\s+)?(.+)$")

# Reasoning keywords the agent MUST embed in verdict reasoning so that
# _lib/verifier/classify.py::classify_failure continues to work unchanged.
DRIFT_KEYWORDS = ("exists but", "discrepan", "mismatch", "differs from ac")
GAP_KEYWORDS = ("not implement", "missing", "absent", "todo: implement")

# Verdict item schema (verifier-v2-hardening Phase 2: strict per oracle risk #2).
# Per ADR-0045 + SKILL.md § LLM Verification Protocol Step 3:
# - evidence non-empty (≥1 tool-call record per AC)
# - reasoning non-empty (mandatory explanation)
# - status enum unchanged
VERDICT_ITEM_SCHEMA = {
    "type": "object",
    "required": ["ac_id", "status", "confidence", "reasoning"],
    "properties": {
        "ac_id": {"type": "string", "pattern": r"^AC-\d+$"},
        "description": {"type": "string"},
        "status": {"enum": ["pass", "fail", "partial"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "evidence": {"type": "array", "minItems": 1},
        "reasoning": {"type": "string", "minLength": 1},
    },
}
VERDICT_SCHEMA = {"type": "array", "items": VERDICT_ITEM_SCHEMA}

CONTEXT_SCHEMA_VERSION = 1


def parse_acs(proposal_path: Path) -> list[dict]:
    """Extract AC bullets from `## 验收标准` / `## Acceptance Criteria` section.

    Returns list of {ac_id: 'AC-N', description: str, has_checkbox: bool}.
    Empty list if section missing or has no bullets.

    Behavior-identical to skills/ac-verifier/scripts/ac_verifier.py::parse_acs
    (kept in sync during the ac-verifier shim window; ac-verifier is the copy
    scheduled for removal, this module is canonical).
    """
    proposal_path = Path(proposal_path)
    if not proposal_path.is_file():
        return []
    text = proposal_path.read_text(encoding="utf-8")

    section_match = _AC_SECTION_HEADERS.search(text)
    if not section_match:
        return []

    section_start = section_match.end()
    section_end_match = _SECTION_END.search(text, pos=section_start)
    section_end = section_end_match.start() if section_end_match else len(text)
    section_text = text[section_start:section_end]

    acs: list[dict] = []
    for line in section_text.splitlines():
        m = _BULLET_LINE.match(line.strip())
        if not m:
            continue
        marker = m.group(1)
        description = m.group(2).strip()
        has_checkbox = marker in (" ", "x")
        acs.append({
            "ac_id": f"AC-{len(acs) + 1}",
            "description": description,
            "has_checkbox": has_checkbox,
        })
    return acs


def _current_commit(project_root: Path) -> Optional[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None


def build_verification_context(
    change_name: str,
    project_root: Path,
    *,
    codebase_commit: Optional[str] = None,
) -> Optional[dict]:
    """Build the agent verification context doc for one change.

    Returns None when proposal.md is missing (caller maps to exit 2/skip
    semantics at the CLI layer).
    """
    project_root = Path(project_root)
    proposal_path = project_root / "openspec" / "changes" / change_name / "proposal.md"
    if not proposal_path.is_file():
        return None
    acs = parse_acs(proposal_path)
    if codebase_commit is None:
        codebase_commit = _current_commit(project_root)
    return {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "change": change_name,
        "proposal_path": str(proposal_path),
        "codebase_commit": codebase_commit,
        "ac_count": len(acs),
        "acs": acs,
        "cache_path": str(project_root / ".rddf" / "state" / f".ac-verdict-{change_name}.json"),
        "audit_log_path": str(project_root / ".rddf" / "state" / ".ac-verification.jsonl"),
        "expected_verdict_schema": VERDICT_SCHEMA,
        "reasoning_keywords": {
            "drift": list(DRIFT_KEYWORDS),
            "gap": list(GAP_KEYWORDS),
            "note": ("Embed at least one drift/gap keyword in the reasoning field "
                     "of failed ACs so classify_failure routes correctly. "
                     "Ambiguous failures default to implementation_gap."),
        },
        "instruction": (
            "Perform verification per skills/rdd-verifier/SKILL.md § "
            "'LLM Verification Protocol'. For each AC: collect at least one "
            "tool-call evidence, cross-reference against implementation, emit "
            "verdict JSON array (length == ac_count), write cache_path (schema "
            "v2) and append audit_log_path (JSONL)."
        ),
        "staged_at": datetime.now(timezone.utc).isoformat(),
        "staged_by": "rdd-verifier-v2",
    }


def stage_verification_context(
    change_name: str,
    project_root: Path,
    *,
    codebase_commit: Optional[str] = None,
) -> Optional[Path]:
    """Write the context doc to .rddf/state/rdd-verify-context-<change>.json.

    Returns the written path, or None when proposal.md is missing.

    Atomic write (verifier-v2-hardening Phase 5 / oracle risk #5): temp file +
    rename prevents interleaving when two processes stage the same change
    concurrently. POSIX `Path.replace` is atomic on the same filesystem.
    """
    doc = build_verification_context(
        change_name, project_root, codebase_commit=codebase_commit,
    )
    if doc is None:
        return None
    out = Path(project_root) / ".rddf" / "state" / f"rdd-verify-context-{change_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    # Atomic: write to temp, then rename. Concurrent stagings can race on the
    # write but only one rename will land as the final file content.
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    tmp.replace(out)
    return out


def validate_verdict_items(items: list) -> tuple[list, list]:
    """Best-effort schema check of a verdict array.

    Returns (valid_items, problems) where problems is a list of
    "<ac_id>: <reason>" strings. Never raises — invalid entries are
    treated as fail by the caller (SKILL.md § Step 3 hard constraints).

    Per oracle risk #2 (verifier-v2-hardening Phase 2): enforces evidence
    non-empty (≥1 tool-call record per AC) and, for fail/partial status,
    reasoning MUST contain at least one drift/gap keyword so that
    _lib/verifier/classify.py::classify_failure routes correctly.
    Pass status does not require keyword (passes don't route).
    """
    problems: list[str] = []
    valid: list = []
    if not isinstance(items, list):
        return [], ["verdict: not a JSON array"]
    structural_only = False
    try:
        import jsonschema
        from jsonschema.exceptions import ValidationError as _JsonschemaError

        for idx, item in enumerate(items):
            try:
                jsonschema.validate(item, VERDICT_ITEM_SCHEMA)
                valid.append(item)
            except _JsonschemaError as e:
                ac_id = item.get("ac_id", f"index-{idx}") if isinstance(item, dict) else f"index-{idx}"
                problems.append(f"{ac_id}: {e.message}")
                # keep the item; caller downgrades to fail
                valid.append(item)
    except ImportError:
        structural_only = True
        # jsonschema not installed — structural checks only (oracle risk #5:
        # never silently accept; the warning is appended at the end so the
        # caller is informed the strict schema was bypassed).
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                problems.append(f"index-{idx}: not an object")
                continue
            if not re.match(r"^AC-\d+$", str(item.get("ac_id", ""))):
                problems.append(f"{item.get('ac_id', f'index-{idx}')}: bad ac_id")
            if item.get("status") not in ("pass", "fail", "partial"):
                problems.append(f"{item.get('ac_id', f'index-{idx}')}: invalid status")
            valid.append(item)

    # Enforce semantic constraints beyond schema: pass/partial need ≥1 evidence;
    # fail/partial need reasoning with at least one drift/gap keyword.
    # (pass does not require keyword; partial and fail do for routing.)
    for item in valid:
        if not isinstance(item, dict):
            continue
        ac_id = item.get("ac_id", "?")
        status = item.get("status")
        evidence = item.get("evidence") or []
        reasoning = (item.get("reasoning") or "").lower()
        if not isinstance(evidence, list) or len(evidence) < 1:
            problems.append(f"{ac_id}: evidence empty (requires ≥1 tool-call record)")
        if status in ("fail", "partial"):
            kw_match = any(kw in reasoning for kw in DRIFT_KEYWORDS) or \
                       any(kw in reasoning for kw in GAP_KEYWORDS)
            if not kw_match:
                problems.append(
                    f"{ac_id}: {status} reasoning must contain a drift/gap keyword"
                )

    if structural_only:
        problems.append(
            "schema validator unavailable; structural-only check applied"
        )
    return valid, problems


def validate_verdict_completeness(
    verdict: list, acs: list
) -> tuple[list, list]:
    """Enforce verdict array covers exactly the proposal's AC set (P1 oracle risk #1).

    Returns (valid_items, problems). Empty problems list means the verdict is
    complete: length matches len(acs), every AC is covered exactly once with
    no missing/unknown/duplicate ac_id entries.

    Without this guard, an agent that emits [AC-1 pass] for a 5-AC proposal
    silently passes is_cache_fresh and is consumed by archive_gate_check. This
    function closes that silent-corruption gap.
    """
    problems: list[str] = []
    if not isinstance(verdict, list):
        return [], ["verdict: not a JSON array"]
    expected_ids = [ac["ac_id"] for ac in acs if isinstance(ac, dict)]
    expected_set = set(expected_ids)
    seen_ids: list[str] = []
    for item in verdict:
        if not isinstance(item, dict):
            continue
        ac_id = item.get("ac_id")
        if not isinstance(ac_id, str) or not re.match(r"^AC-\d+$", ac_id):
            continue
        seen_ids.append(ac_id)
    seen_set = set(seen_ids)
    missing = expected_set - seen_set
    for ac_id in sorted(missing):
        problems.append(f"missing {ac_id}")
    unknown = seen_set - expected_set
    for ac_id in sorted(unknown):
        problems.append(f"{ac_id}: unknown ac_id")
    seen_counts: dict[str, int] = {}
    for ac_id in seen_ids:
        seen_counts[ac_id] = seen_counts.get(ac_id, 0) + 1
    for ac_id, count in sorted(seen_counts.items()):
        if count > 1:
            problems.append(f"{ac_id}: duplicate ac_id ({count}x)")
    return verdict, problems
