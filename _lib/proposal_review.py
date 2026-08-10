"""skills/_lib/proposal_review.py — HOW-leakage warning detector (D4).

Implements the heuristic HOW-leakage detector from the
`add-proposal-how-leakage-warning` change. Returns warning records
when improvement/proposal text drifts from WHY/WHAT into HOW too
early, without ever modifying the source content.

Design contract (see openspec/changes/add-proposal-how-leakage-warning/design.md):
    - 4 interpretable heuristic signals (code-fence, function/method
      signatures, file/module change lists, implementation-step density).
    - Per-section weighting: WHY/WHAT sections weighted higher than
      `技术约束` which legitimately contains technical terms.
    - Multi-signal rule: warn when >=2 signals fire OR single signal
      exceeds hard cap. Single weak signal suppressed.
    - Default behavior: WARNING-ONLY. Never blocks create / approve /
      design-done / plan-done in default config.
    - Read-only: never edits, strips, crops, or rewrites source content.
    - Non-fatal parse failures: missing sections / empty file /
      non-standard Markdown return empty list, not raise.

Metric for threshold tuning (per ADR-0019 §3.1, ADR-0025 §D2):
    The user_confirmed_false_positive_rate recorded to
    `.rddf/state/.how-leakage-hits.json` should remain <=20%.
    Tune thresholds after empirical hit data, not preemptively.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from typing import Dict, List, TypedDict

# Threshold configuration is externalized per design decision
# (see Group 5 in .rddf/plans/add-proposal-how-leakage-warning.md).
# Import from sibling module so tuning is config-only.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
try:
    from proposal_review_config import THRESHOLDS  # type: ignore
except ImportError:
    # Fallback minimal thresholds if config module missing. Allows the
    # detector to remain importable even if the config file is absent
    # (e.g. partial checkout). Callers should still consult THRESHOLDS
    # via the explicit attribute path documented in design.md.
    THRESHOLDS = {
        "code_fence": {"high": 2, "hard_cap": 4},
        "function_signature": {"high": 2, "hard_cap": 5},
        "file_list": {"high": 3, "hard_cap": 6},
        "step_density": {"high": 3, "hard_cap": 6},
        "section_weights": {
            "架构依据": 1.0,
            "范围": 1.0,
            "关键场景": 0.8,
            "技术约束": 0.4,
            "验收标准": 0.6,
        },
        "multi_signal_threshold": 2,
        "weighted_score_block": 1.5,
    }


class WarningRecord(TypedDict):
    """One warning record emitted by the detector.

    Fields:
        signal: one of 'code_fence' | 'function_signature' |
                'file_list' | 'step_density'
        threshold: dict with the signal's high/hard_cap thresholds
        section: section name where the signal fired
        action: human-readable suggested action (advisory only)
        weighted_score: float, signal count * section weight
    """

    signal: str
    threshold: Dict[str, int]
    section: str
    action: str
    weighted_score: float


# Section header pattern: `## <section name>` followed by content until
# the next `## ` or end of file. The detector splits the document by
# sections before applying per-section weighting.
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

# Signal 1: code-fence density. Count fenced blocks per section.
# Matches triple-backtick fences (``` or ~~~) at line start. We do not
# try to count inside-fence content; the heuristic counts opening fences.
_CODE_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})", re.MULTILINE)

# Signal 2: function / method signatures.
# Matches `def name(`, `class Name`, `function name(`, and method-call
# patterns like `self.foo(`. Conservative: requires opening paren or
# `class` keyword to reduce false positives on prose like "the def".
_SIGNATURE_RE = re.compile(
    r"(?:^|\s)(?:def\s+\w+\s*\(|class\s+\w+|function\s+\w+\s*\(|self\.\w+\s*\(|@staticmethod)",
    re.MULTILINE,
)

# Signal 3: file / module change lists.
# Matches paths like `path/to/file.py`, `**/*.ts`, `package/submodule`.
# Conservative: requires either file extension or wildcards.
_FILE_LIST_RE = re.compile(
    r"(?:^|\s)(?:\*\*?/[^\s]+\.[a-zA-Z]{1,6}|"
    r"[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+){1,}/\S+\.[a-zA-Z]{1,6}|"
    r"`[A-Za-z0-9_./]+\.[a-zA-Z]{1,6}`)",
    re.MULTILINE,
)

# Signal 4: implementation-step density.
# Matches ordinal lists: `1.`, `2.`, or `Step 1`, `Step 2`. We look
# for 3+ consecutive lines matching the pattern (consecutive ordinals
# indicate implementation enumeration rather than a single example).
_STEP_RE = re.compile(
    r"^\s*(?:\d+\.\s+\S|Step\s+\d+\b)",
    re.MULTILINE,
)


def _split_sections(text: str) -> List[tuple[str, str]]:
    """Split markdown by `## ` section headers.

    Returns list of (section_name, section_body). Unscoped content
    before the first `## ` is labeled `_preamble` and given weight 0.5
    (preamble contains metadata, not implementation).
    """
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        return [("_preamble", text)]

    sections: List[tuple[str, str]] = []
    # Preamble content before first section header
    if matches[0].start() > 0:
        preamble = text[: matches[0].start()]
        if preamble.strip():
            sections.append(("_preamble", preamble))

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        sections.append((m.group(1).strip(), body))

    return sections


def _signal_count(signal_name: str, body: str) -> int:
    """Count raw hits of a signal in a section body."""
    if signal_name == "code_fence":
        return len(_CODE_FENCE_RE.findall(body))
    if signal_name == "function_signature":
        return len(_SIGNATURE_RE.findall(body))
    if signal_name == "file_list":
        return len(_FILE_LIST_RE.findall(body))
    if signal_name == "step_density":
        return len(_STEP_RE.findall(body))
    return 0


def _consecutive_step_count(body: str) -> int:
    """Count longest run of consecutive ordinal-step lines.

    A single `1. foo` example in a paragraph should not count as
    step density; only consecutive ordinals indicate enumeration.
    """
    lines = body.splitlines()
    longest = 0
    current = 0
    for line in lines:
        if _STEP_RE.match(line):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _section_weight(section_name: str) -> float:
    """Look up section weight from THRESHOLDS; default 0.5."""
    weights = THRESHOLDS.get("section_weights", {})
    if section_name in weights:
        return float(weights[section_name])
    return 0.5


def detect_how_leakage(
    text: str,
    *,
    config: Dict | None = None,
    _persist_hits: bool = True,
) -> List[WarningRecord]:
    """Detect HOW-leakage in improvement/proposal text.

    Args:
        text: full markdown body (improvement or proposal).
        config: optional threshold override (merged with THRESHOLDS).
        _persist_hits: internal flag; when True, append hit records to
            `.rddf/state/.how-leakage-hits.json` for empirical tuning
            per ADR-0019 §3.1. Defaults to True; tests may disable.

    Returns:
        List of WarningRecord. Empty list means no warning. NEVER
        modifies the source `text`.

    Non-fatal behavior:
        - Empty text returns [].
        - Sections we don't recognize get weight 0.5 (defensive).
        - Bad regex input (shouldn't happen — we compile at import)
          returns [] via the try/except in _split_sections fallback.
    """
    if not text or not text.strip():
        return []

    cfg = dict(THRESHOLDS)
    if config:
        cfg.update(config)

    sections = _split_sections(text)

    # Per-signal section-level fire records: signal_name -> list of
    # (section_name, weighted_score). Used for multi-signal rule.
    fires: Dict[str, List[tuple[str, float]]] = {
        "code_fence": [],
        "function_signature": [],
        "file_list": [],
        "step_density": [],
    }

    for section_name, body in sections:
        weight = _section_weight(section_name)
        # Signal 1, 2, 3: count-based
        for signal in ("code_fence", "function_signature", "file_list"):
            threshold = cfg[signal]
            count = _signal_count(signal, body)
            if count >= threshold["high"]:
                fires[signal].append(
                    (section_name, count * weight)
                )
        # Signal 4: consecutive-step density
        consec = _consecutive_step_count(body)
        if consec >= cfg["step_density"]["high"]:
            fires["step_density"].append(
                (section_name, float(consec) * weight)
            )

    # Build warning records:
    # Fire when >= multi_signal_threshold signals each have >=1 section,
    # OR any single signal has a section exceeding hard_cap.
    fired_signal_sections: List[tuple[str, str, float, Dict]] = []
    multi_threshold = cfg["multi_signal_threshold"]
    multi_count = 0
    for signal, section_list in fires.items():
        if section_list:
            multi_count += 1
        threshold = cfg[signal]
        for section_name, score in section_list:
            # Single-signal hard cap rule: any section's raw count
            # exceeds hard_cap triggers immediately. We approximate
            # raw count from score/weight.
            raw_count = (
                score / weight if (section_name in cfg.get("section_weights", {}) or section_name == "_preamble") else score
            )
            # Simpler: re-fetch raw count for hard-cap check.
            _, body = next(
                ((n, b) for n, b in sections if n == section_name),
                ("", ""),
            )
            if signal == "step_density":
                raw_count = float(_consecutive_step_count(body))
            else:
                raw_count = float(_signal_count(signal, body))

            if raw_count >= threshold["hard_cap"]:
                fired_signal_sections.append(
                    (signal, section_name, score, threshold)
                )

    # Multi-signal rule
    warnings: List[WarningRecord] = []
    if multi_count >= multi_threshold:
        for signal, section_list in fires.items():
            if not section_list:
                continue
            for section_name, score in section_list:
                warnings.append(
                    WarningRecord(
                        signal=signal,
                        threshold=cfg[signal],
                        section=section_name,
                        action="review manually (multi-signal fire)",
                        weighted_score=score,
                    )
                )

    # Single-signal hard-cap fires are also warnings
    for signal, section_name, score, threshold in fired_signal_sections:
        # Avoid duplicates already added by multi-signal rule
        if not any(
            w["signal"] == signal and w["section"] == section_name
            for w in warnings
        ):
            warnings.append(
                WarningRecord(
                    signal=signal,
                    threshold=threshold,
                    section=section_name,
                    action="review manually (single-signal hard-cap)",
                    weighted_score=score,
                )
            )

    # Persist hits for empirical tuning (ADR-0019 §3.1).
    # We always persist the document hash + per-signal raw counts, even
    # when no warning fires, so future iterations can analyze the
    # false-negative rate.
    if _persist_hits and warnings:
        _record_hits(text, sections, cfg, warnings)

    return warnings


def _record_hits(
    text: str,
    sections: List[tuple[str, str]],
    cfg: Dict,
    warnings: List[WarningRecord],
) -> None:
    """Append hit records to `.rddf/state/.how-leakage-hits.json`.

    Failures are silent: this is telemetry, not gate logic. Per design
    decision "no auto-rewrite / no fatal behavior", a write failure
    must not propagate to the caller.
    """
    try:
        project_root = os.environ.get("PROJECT_ROOT") or _find_project_root()
        if not project_root:
            return
        state_dir = os.path.join(project_root, ".rddf", "state")
        os.makedirs(state_dir, exist_ok=True)
        hit_path = os.path.join(state_dir, ".how-leakage-hits.json")
        doc_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

        record = {
            "doc_hash": doc_hash,
            "timestamp": _now_iso(),
            "warnings": [
                {k: v for k, v in w.items() if k != "threshold"}
                | {"threshold_high": w["threshold"].get("high")}
                for w in warnings
            ],
            "multi_signal_threshold": cfg["multi_signal_threshold"],
        }

        existing: List[Dict] = []
        if os.path.isfile(hit_path):
            try:
                with open(hit_path, encoding="utf-8") as f:
                    existing = json.load(f)
                if not isinstance(existing, list):
                    existing = []
            except (OSError, json.JSONDecodeError):
                existing = []
        existing.append(record)
        # Cap history at last 500 hits to avoid unbounded growth.
        existing = existing[-500:]
        with open(hit_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    except Exception:
        # Telemetry must never raise. See ADR-0019 §3.1 / design.md
        # decision "non-fatal parse failures".
        pass


def _find_project_root() -> str:
    """Best-effort project root discovery (looks for .git upward)."""
    cwd = os.getcwd()
    cur = cwd
    for _ in range(20):
        if os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return cwd


def _now_iso() -> str:
    """ISO-8601 timestamp; imported lazily so the detector module
    remains importable even if `datetime` is shadowed in unusual
    environments (defensive per design decision)."""
    try:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        return "unknown"


__all__ = [
    "WarningRecord",
    "detect_how_leakage",
    "THRESHOLDS",
]