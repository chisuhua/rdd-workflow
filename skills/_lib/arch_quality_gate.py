"""Architecture quality gate — qualitative checks for arch_done transition (ADR-0018).

Existing arch_done gate in `gate.py` only validates structural existence (ADR ≥ 1,
roadmap.md exists). This module adds four **qualitative** warning-level checks
that surface arch-level debt without blocking the transition:

  1. `arch_alignment`       — ADR/roadmap/gap-analysis cross-references resolve
  2. `arch_debt_recorded`   — gap-analysis has no unresolved high-priority rows
  3. `adr_no_placeholders`  — ADR files are not template stubs
  4. `arch_handoff_actionable` — .arch-handoff.json carries actionable fields

Severity model:
  - Default (local dev)         → warning (allows transition, records event)
  - `STRICT_ARCH_GATE=yes` (CI) → warning auto-upgrades to error (hard block)

This module is consumed by:
  - `skills/_lib/gate.py`    — registers checks in `_DEFAULT_CHECKS["arch_done"]`
  - `skills/guide-arch.md`   — Phase 5 hook invokes `ArchQualityReport.verify()`
  - `tests/unit/test_arch_quality_gate.py` — unit tests
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


# --- defaults mirrored from gate.py for fallback when handoff is missing ---

_DEFAULT_ADR_DIR = "docs/adr"
_DEFAULT_ROADMAP_PATH = "roadmap.md"
_DEFAULT_ARCHITECTURE_DIR = "docs/architecture"
_DEFAULT_ADR_PATTERN = "ADR-*.md"


# --- ADR reference regex: matches "ADR-1234" in markdown text ---

_ADR_REF_RE = re.compile(r"\bADR-(\d{4})\b")


# --- Placeholder patterns flagged as "template stub" ---

_PLACEHOLDER_PATTERNS = [
    re.compile(r"<待补(?:充|齐|完)?>"),
    re.compile(r"<TBD>"),
    re.compile(r"<TODO>"),
    re.compile(r"<kebab-slug>"),
    re.compile(r"<标题>"),
    re.compile(r"^>\s*\*\*编号\*\*:\s*NNNN\s*$", re.MULTILINE),
    re.compile(r"^#\s*ADR-NNNN:\s*<", re.MULTILINE),
]


# --- gap-analysis table row regex: captures `| 严重程度 | 优先级 | 关联 change |` ---

# Format: `| <num> | <gap> | <severity> | <priority> | <change ref> |`
_GAP_ROW_RE = re.compile(
    r"^\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
    re.MULTILINE,
)
_UNRESOLVED_TOKENS = ("(待补充)", "(待补)", "(TBD)", "<待补", "<TBD")


# ---------- helpers ----------


def _read_handoff(project_root: str) -> dict:
    """Load .arch-handoff.json with defaults fallback (mirrors gate.py behavior)."""
    handoff_path = Path(project_root) / ".rddf" / "state" / ".arch-handoff.json"
    if not handoff_path.is_file():
        return {
            "adr_dir": _DEFAULT_ADR_DIR,
            "roadmap_path": _DEFAULT_ROADMAP_PATH,
            "architecture_dir": _DEFAULT_ARCHITECTURE_DIR,
            "adr_pattern": _DEFAULT_ADR_PATTERN,
        }
    try:
        data = json.loads(handoff_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {
            "adr_dir": _DEFAULT_ADR_DIR,
            "roadmap_path": _DEFAULT_ROADMAP_PATH,
            "architecture_dir": _DEFAULT_ARCHITECTURE_DIR,
            "adr_pattern": _DEFAULT_ADR_PATTERN,
        }
    return {
        "adr_dir": data.get("adr_dir", _DEFAULT_ADR_DIR),
        "roadmap_path": data.get("roadmap_path", _DEFAULT_ROADMAP_PATH),
        "architecture_dir": data.get("architecture_dir", _DEFAULT_ARCHITECTURE_DIR),
        "adr_pattern": data.get("adr_pattern", _DEFAULT_ADR_PATTERN),
    }


def _discover_existing_adr_ids(project_root: str, paths: dict) -> set[str]:
    """Return set of 4-digit ADR ID strings that exist as files."""
    adr_dir = Path(project_root) / paths["adr_dir"]
    if not adr_dir.is_dir():
        return set()
    found = set()
    for f in adr_dir.glob(paths["adr_pattern"]):
        name = f.name
        if name.endswith("-0000-template.md"):
            continue
        m = _ADR_REF_RE.search(name)
        if m:
            found.add(m.group(1))
    return found


def _extract_adr_refs_in_file(path: Path) -> set[str]:
    """Find all ADR-NNNN references in a markdown file's text content."""
    if not path.is_file():
        return set()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return {m.group(1) for m in _ADR_REF_RE.finditer(text)}


def _is_unresolved_token(change_ref: str) -> bool:
    s = change_ref.strip()
    if not s:
        return True
    return any(tok in s for tok in _UNRESOLVED_TOKENS)


def _has_placeholder(text: str) -> bool:
    """Stub heuristic: ≥ 2 distinct placeholder patterns match.

    Real ADRs sometimes mention `<待补充>` in a table cell to mean
    "unresolved" — that's a single hit and is intentional. A template
    stub, by contrast, has many placeholders (title, status, author,
    sections, etc.) — typically ≥ 2 distinct patterns.
    """
    hits = sum(1 for p in _PLACEHOLDER_PATTERNS if p.search(text))
    return hits >= 2


# ---------- strict mode ----------


_STRICT_TRUE = {"yes", "true", "1", "on"}


def is_strict_mode(env_var: str = "STRICT_ARCH_GATE") -> bool:
    """Per-gate strict mode. Default env_var=STRICT_ARCH_GATE (ADR-0018 backward compat).

    ADR-0019: callers can pass `env_var="STRICT_CHANGE_GATE"` to control a
    different gate independently. Values: yes/true/1/on (case-insensitive).
    """
    val = os.environ.get(env_var, "").strip().lower()
    return val in _STRICT_TRUE


def strict_wrap(
    condition: Callable[[dict], tuple[bool, Optional[str]]],
    env_var: str = "STRICT_ARCH_GATE",
) -> Callable[[dict], tuple[bool, Optional[str]]]:
    """Wrap a check condition; under <env_var>=yes, warnings become errors.

    Default env_var=STRICT_ARCH_GATE preserves ADR-0018 behavior. ADR-0019
    passes env_var="STRICT_CHANGE_GATE" to control the plan_done gate
    independently. Errors pass through unchanged (already blocking). Passing
    checks remain passing.
    """

    def wrapped(ctx: dict) -> tuple[bool, Optional[str]]:
        passed, severity = condition(ctx)
        if not passed and severity == "warning" and is_strict_mode(env_var):
            return (False, "error")
        return (passed, severity)

    return wrapped


# ---------- the four checks (all return (passed, severity)) ----------


def _check_arch_alignment(ctx: dict) -> tuple[bool, Optional[str]]:
    """Pass if all ADR-NNNN references in roadmap.md and gap-analysis docs resolve.

    ADR-0018 §3.1. A "ghost" reference (ADR mentioned in text but no matching
    file in adr_dir) usually means the architect forgot to commit or the
    roadmap drifted from reality. We only warn; humans can override.
    """
    project_root = ctx.get("project_root", ".")
    paths = _read_handoff(project_root)
    existing = _discover_existing_adr_ids(project_root, paths)

    roadmap = Path(project_root) / paths["roadmap_path"]
    arch_dir = Path(project_root) / paths["architecture_dir"]

    referenced: set[str] = set()
    if roadmap.is_file():
        referenced.update(_extract_adr_refs_in_file(roadmap))
    if arch_dir.is_dir():
        for gap in arch_dir.glob("*-gap-analysis.md"):
            referenced.update(_extract_adr_refs_in_file(gap))

    ghosts = referenced - existing
    if ghosts:
        return (False, "warning")
    return (True, None)


def _check_arch_debt(ctx: dict) -> tuple[bool, Optional[str]]:
    """Pass if no gap-analysis row is high-severity + P0 + unresolved (ADR-0018 §3.2).

    An unresolved P0/high row in a gap-analysis table signals architecture
    debt that must be tracked. Detection: row's `严重程度` column contains
    `高`, `优先级` column contains `P0`, and `关联 change` is empty or contains
    a placeholder token like `(待补充)`.

    No gap-analysis docs → pass (debt detection is opt-in).
    """
    project_root = ctx.get("project_root", ".")
    paths = _read_handoff(project_root)
    arch_dir = Path(project_root) / paths["architecture_dir"]

    if not arch_dir.is_dir():
        return (True, None)

    for gap in arch_dir.glob("*-gap-analysis.md"):
        try:
            text = gap.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_match in _GAP_ROW_RE.finditer(text):
            severity_cell = line_match.group(2).strip()
            priority_cell = line_match.group(3).strip()
            change_ref = line_match.group(4)
            if "高" in severity_cell and "P0" in priority_cell and _is_unresolved_token(change_ref):
                return (False, "warning")

    return (True, None)


def _check_adr_clarity(ctx: dict) -> tuple[bool, Optional[str]]:
    """Pass if no ADR file (excluding template) contains placeholder text (ADR-0018 §3.3).

    Placeholder patterns: `<待补充>`, `<TBD>`, `<TODO>`, `<kebab-slug>`, `<标题>`,
    template header lines `> **编号**: NNNN` and `# ADR-NNNN: <`.

    The template file (ADR-0000-template.md) is excluded — its job is to be a
    template.
    """
    project_root = ctx.get("project_root", ".")
    paths = _read_handoff(project_root)
    adr_dir = Path(project_root) / paths["adr_dir"]

    if not adr_dir.is_dir():
        return (True, None)

    for f in adr_dir.glob(paths["adr_pattern"]):
        if f.name.endswith("-0000-template.md"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _has_placeholder(text):
            return (False, "warning")

    return (True, None)


def _check_handoff_actionable(ctx: dict) -> tuple[bool, Optional[str]]:
    """Pass if .arch-handoff.json carries actionable fields for guide-plan (ADR-0018 §3.4).

    Actionable means:
      - file exists and is valid JSON
      - `current_phase` is not `default` or empty (a real roadmap phase)
      - `discovered.adr_dir.found` is `true` (handoff is honest about artifacts)
      - `version` is 1 (consumer compatibility)
    """
    project_root = ctx.get("project_root", ".")
    handoff_path = Path(project_root) / ".rddf" / "state" / ".arch-handoff.json"
    if not handoff_path.is_file():
        return (False, "warning")
    try:
        data = json.loads(handoff_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return (False, "warning")

    current_phase = (data.get("current_phase") or "").strip()
    if not current_phase or current_phase == "default":
        return (False, "warning")

    discovered = data.get("discovered") or {}
    adr_disc = discovered.get("adr_dir") or {}
    if not adr_disc.get("found"):
        return (False, "warning")

    if data.get("version") != 1:
        return (False, "warning")

    return (True, None)


# ---------- aggregator ----------


@dataclass
class ArchQualityReport:
    """Aggregate result of all arch quality checks."""

    passed: bool = True
    warnings: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    detail: dict = field(default_factory=dict)
    strict_mode: bool = False

    @classmethod
    def verify(cls, project_root: str) -> "ArchQualityReport":
        """Run all 4 checks and aggregate at native severity.

        `STRICT_ARCH_GATE` is reported as a flag for observability but does NOT
        affect the warnings/failed split here — strict mode is the registration
        layer's responsibility (`strict_wrap()` in `gate.py`). This keeps the
        report deterministic regardless of env vars.
        """
        checks: list[tuple[str, Callable[[dict], tuple[bool, Optional[str]]]]] = [
            ("arch_alignment", _check_arch_alignment),
            ("arch_debt_recorded", _check_arch_debt),
            ("adr_no_placeholders", _check_adr_clarity),
            ("arch_handoff_actionable", _check_handoff_actionable),
        ]
        ctx = {"project_root": project_root}
        report = cls(strict_mode=is_strict_mode())
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