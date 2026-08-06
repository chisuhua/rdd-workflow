"""Change alignment gate — qualitative checks for plan_done transition (ADR-0019).

ADR-0018 introduced arch-document-level checks at `arch_done`. ADR-0019 adds
3 change-proposal-level checks at `plan_done`:

  1. `change_adr_refs_valid`   — design.md ADR references resolve + status=accepted
  2. `change_no_contradiction` — design.md anti-pattern keywords are ADR-justified
  3. `change_task_traceability` — ≥80% of tasks.md items trace to ≥1 ADR

All checks default to warning; `STRICT_CHANGE_GATE=yes` upgrades to error
(CI mode). `strict_wrap(condition, env_var="STRICT_CHANGE_GATE")` is reused
from `arch_quality_gate.py`.

This module is consumed by:
  - `skills/_lib/gate.py` — registers checks in `_DEFAULT_CHECKS["plan_done"]`
  - `tests/unit/test_change_alignment.py` — unit tests
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


# --- Defaults ---

_DEFAULT_ADR_DIR = "docs/adr"
_DEFAULT_ADR_PATTERN = "ADR-*.md"


# --- Regex patterns ---

# ADR-NNN §N.M references in markdown text (numeric id only)
_ADR_REF_RE = re.compile(r"\bADR-(\d{4})\b")

# Task item: `- [ ]` or `- [x]` checkbox (real format in tasks.md)
_TASK_ITEM_RE = re.compile(r"^\s*-\s*\[[ xX]\]\s+(.+)$", re.MULTILINE)

# Status line in ADR: `> **状态**: ...`
_ADR_STATUS_RE = re.compile(r"^>\s*\*\*状态\*\*:\s*(.+?)\s*$", re.MULTILINE)


# --- Anti-patterns (Oracle 2026-07-10: keep v1 conservative at 3 patterns) ---

@dataclass(frozen=True)
class AntiPattern:
    pattern: str
    severity: str
    compiled: re.Pattern = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "compiled", re.compile(self.pattern, re.IGNORECASE))


_ANTI_PATTERNS: tuple[AntiPattern, ...] = (
    AntiPattern(
        pattern=r"单阶段|单体架构|hard.?code|hard.?coded|硬编码",
        severity="info",
    ),
    AntiPattern(
        pattern=r"跳过.{0,5}(架构|arch|adr|ADR)",
        severity="warn",
    ),
    AntiPattern(
        pattern=r"不写测试|跳过测试|skip.{0,5}test",
        severity="warn",
    ),
)


# --- ADR status enum (Oracle A2) ---


class ADRStatus(str, Enum):
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    REPLACED = "replaced"
    REJECTED = "rejected"
    PENDING = "pending"
    UNKNOWN = "unknown"


_ACCEPTED_TOKENS = ("已采纳",)
_DEPRECATED_TOKENS = ("已弃用",)
_REPLACED_TOKENS = ("已替代为", "已替代", "被替代")
_REJECTED_TOKENS = ("已拒绝",)
_PENDING_TOKENS = ("待定",)


def _classify_status_line(status_text: str) -> ADRStatus:
    """Map ADR status-line text to enum. Tolerates emoji and verbose variants."""
    text = status_text.strip()
    if any(tok in text for tok in _REPLACED_TOKENS):
        return ADRStatus.REPLACED
    if any(tok in text for tok in _DEPRECATED_TOKENS):
        return ADRStatus.DEPRECATED
    if any(tok in text for tok in _REJECTED_TOKENS):
        return ADRStatus.REJECTED
    if any(tok in text for tok in _ACCEPTED_TOKENS):
        return ADRStatus.ACCEPTED
    if any(tok in text for tok in _PENDING_TOKENS):
        return ADRStatus.PENDING
    return ADRStatus.UNKNOWN


# --- Helpers ---


def _resolve_active_change(ctx: dict) -> Optional[str]:
    """Resolve active change name from ctx.

    Resolution order:
      1. Explicit `ctx["change_name"]` (used by direct callers / report aggregator)
      2. State vector `plan_side.active_change` (plan semantics)
      3. State vector `arch_side.current_change` (legacy fallback)
      4. None (no active change)
    """
    explicit = ctx.get("change_name")
    if explicit:
        return explicit
    sv = ctx.get("state_vector")
    if sv is None:
        return None
    name = sv.get_field("plan_side.active_change")
    if name:
        return name
    return sv.get_field("arch_side.current_change")


def _read_adr_status(project_root: str, adr_id: str, adr_dir: str, adr_pattern: str) -> ADRStatus:
    """Read ADR-<id> file's status line and classify. Returns UNKNOWN on any I/O failure."""
    base = Path(project_root) / adr_dir
    if not base.is_dir():
        return ADRStatus.UNKNOWN
    for f in base.glob(adr_pattern):
        m = _ADR_REF_RE.search(f.name)
        if m and m.group(1) == adr_id:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ADRStatus.UNKNOWN
            status_match = _ADR_STATUS_RE.search(text)
            if not status_match:
                return ADRStatus.UNKNOWN
            return _classify_status_line(status_match.group(1))
    return ADRStatus.UNKNOWN


def _extract_adr_ids_in_change(project_root: str, change_name: str) -> set[str]:
    """Extract ADR-NNNN ids referenced in `openspec/changes/<name>/design.md`.

    Defensive: returns empty set if design.md missing (Oracle A5).
    """
    path = Path(project_root) / "openspec" / "changes" / change_name / "design.md"
    if not path.is_file():
        return set()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return {m.group(1) for m in _ADR_REF_RE.finditer(text)}


def _read_change_file(project_root: str, change_name: str, filename: str) -> Optional[str]:
    """Read `openspec/changes/<name>/<filename>`; return None if missing or I/O error."""
    path = Path(project_root) / "openspec" / "changes" / change_name / filename
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ---------- The 3 checks ----------


def _check_change_adr_refs_valid(ctx: dict) -> tuple[bool, Optional[str]]:
    """design.md ADR refs all exist + status=accepted (ADR-0019 §3.1, Oracle A1+A2+A5).

    Defensive: no design.md → pass (artifacts_complete check covers existence).
    """
    project_root = ctx.get("project_root", ".")
    change_name = _resolve_active_change(ctx)
    if not change_name:
        return (True, None)

    refs = _extract_adr_ids_in_change(project_root, change_name)
    if not refs:
        return (True, None)

    adr_dir = os.environ.get("SPEC_WORKFLOW_ADR_DIR", _DEFAULT_ADR_DIR)
    adr_pattern = os.environ.get("SPEC_WORKFLOW_ADR_PATTERN", _DEFAULT_ADR_PATTERN)

    invalid = []
    for adr_id in sorted(refs):
        status = _read_adr_status(project_root, adr_id, adr_dir, adr_pattern)
        if status != ADRStatus.ACCEPTED:
            invalid.append((adr_id, status.value))

    return (len(invalid) == 0, "warning" if invalid else None)


def _check_change_no_contradiction(ctx: dict) -> tuple[bool, Optional[str]]:
    """design.md anti-pattern keywords must be ADR-justified (ADR-0019 §3.2, Oracle A3+A5).

    Only `severity="warn"` anti-patterns without an ADR ref trigger warning.
    `severity="info"` patterns are recorded but do not block.
    Defensive: no design.md → pass.
    """
    project_root = ctx.get("project_root", ".")
    change_name = _resolve_active_change(ctx)
    if not change_name:
        return (True, None)

    text = _read_change_file(project_root, change_name, "design.md")
    if text is None:
        return (True, None)

    has_adr_ref = bool(_ADR_REF_RE.search(text))
    for ap in _ANTI_PATTERNS:
        if ap.compiled.search(text):
            if ap.severity == "warn" and not has_adr_ref:
                return (False, "warning")

    return (True, None)


def _check_change_task_traceability(ctx: dict) -> tuple[bool, Optional[str]]:
    """≥80% of tasks.md checkbox items reference ≥1 ADR (ADR-0019 §3.3, Oracle A4+A5).

    Defensive: missing tasks.md, empty tasks.md, or no checkboxes → pass.
    """
    project_root = ctx.get("project_root", ".")
    change_name = _resolve_active_change(ctx)
    if not change_name:
        return (True, None)

    text = _read_change_file(project_root, change_name, "tasks.md")
    if text is None:
        return (True, None)

    items = _TASK_ITEM_RE.findall(text)
    if not items:
        return (True, None)

    traced = sum(1 for item in items if _ADR_REF_RE.search(item))
    coverage = traced / len(items)
    return (coverage >= 0.8, "warning" if coverage < 0.8 else None)


# ---------- Aggregator ----------


@dataclass
class ChangeAlignmentReport:
    """Aggregate result of all change alignment checks."""

    passed: bool = True
    warnings: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    detail: dict = field(default_factory=dict)
    strict_mode: bool = False

    @classmethod
    def verify(cls, project_root: str, change_name: Optional[str] = None) -> "ChangeAlignmentReport":
        """Run all 3 checks at native severity (registration layer handles strict upgrade)."""
        from skills._lib.arch_quality_gate import is_strict_mode

        checks: list[tuple[str, Callable[[dict], tuple[bool, Optional[str]]]]] = [
            ("change_adr_refs_valid", _check_change_adr_refs_valid),
            ("change_no_contradiction", _check_change_no_contradiction),
            ("change_task_traceability", _check_change_task_traceability),
        ]

        ctx: dict = {"project_root": project_root}
        if change_name:
            ctx["change_name"] = change_name

        report = cls(strict_mode=is_strict_mode("STRICT_CHANGE_GATE"))
        for name, fn in checks:
            try:
                passed, severity = fn(ctx)
            except Exception as e:  # pragma: no cover — defensive
                report.detail[name] = f"check raised: {e}"
                report.failed_checks.append(name)
                report.passed = False
                continue
            report.detail[name] = {"passed": passed, "severity": severity}
            if not passed:
                if severity == "warning":
                    report.warnings.append(name)
                else:
                    report.failed_checks.append(name)
                    report.passed = False
        return report