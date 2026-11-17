"""Architecture quality gate — qualitative checks for arch_done transition (ADR-0018).

Existing arch_done gate in `gate.py` only validates structural existence (ADR ≥ 1,
roadmap.md exists). This module adds four **qualitative** warning-level checks
that surface arch-level debt without blocking the transition:

  1. `arch_alignment`       — ADR cross-references in roadmap.md + theme docs resolve
  2. `adr_no_placeholders`  — ADR files are not template stubs
  3. `arch_handoff_actionable` — .arch-handoff.json carries actionable fields
  4. `file_size_limit`      — _lib/*.py files do not exceed line cap
  5. `adr_shape`            — ADRs stay within the decision-document shape
                              budget (opt-in via `ARCH_SHAPE_CHECK=yes`)

Severity model:
  - Default (local dev)         → warning (allows transition, records event)
  - `STRICT_ARCH_GATE=yes` (CI) → warning auto-upgrades to error (hard block)

This module is consumed by:
  - `skills/_lib/gate.py`    — registers checks in `_DEFAULT_CHECKS["arch_done"]`
  - `skills/rdd-arch/SKILL.md` — arch-done hook invokes `ArchQualityReport.verify()`
  - `tests/unit/test_arch_quality_gate.py` — unit tests

CHANGED 2026-09-30 (per ADR-0057):
  - Removed `arch_debt_recorded` check (gap-analysis artifact type deleted)
  - `arch_alignment` now scans all theme docs in `docs/architecture/*.md`,
    not just `*-gap-analysis.md` (theme docs are rdd-arch's composition artifacts)
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


# --- ADR shape budget (env-tunable) ---

# A decision record that stops answering "what / why / at what cost" and starts
# answering "how exactly" is no longer a decision record. These budgets encode
# that boundary. Measured 2026-10-27: recent ADRs reached 435-620 lines with
# decision statements down to 22% of the body.
#
# CHANGED 2026-11-17 (per the ADR-0060 amendment): the budget was 300; it is
# now 250 so the mechanical check matches the prose contract — the ADR template
# ("正文目标 ≤ 250 行") and the opencode build-agent architect shape contract
# ("正文 = 决策本身，目标 ≤ 250 行"). The count is the **whole-file physical line
# count** (headings, table separator rows and blank lines included); the
# template's "正文" wording excludes derivation/evidence, so the two numbers are
# comparable only in the conservative direction.
#
# NOTE: `ARCH_FILE_SIZE_LIMIT` (see `_check_file_size`) is a *different* budget
# whose default happens to be similar — do not conflate them.
_DEFAULT_ADR_LINE_LIMIT = 250
_DEFAULT_ADR_STATUS_MAX = 200

# Section presence — bilingual, tolerant of numbered headings ("## 2. 决策").
_SHAPE_REQUIRED_SECTIONS = {
    "Context": re.compile(r"^#{2,4}\s*(?:\d+[.)]\s*)?(?:context|背景)\b", re.MULTILINE | re.IGNORECASE),
    "Decision": re.compile(r"^#{2,4}\s*(?:\d+[.)]\s*)?(?:decision|决策)\b", re.MULTILINE | re.IGNORECASE),
    "Consequences": re.compile(r"^#{2,4}\s*(?:\d+[.)]\s*)?(?:consequences|后果)\b", re.MULTILINE | re.IGNORECASE),
    "Alternatives": re.compile(r"^#{2,4}\s*(?:\d+[.)]\s*)?(?:备选方案|替代方案|alternatives)\b", re.MULTILINE | re.IGNORECASE),
}

# Verification chapter — h2 only, line-anchored, tolerant of a trailing note.
#
# An h3 like `### 验证 ADR-0048 + ADR-0049 零 regression` is a prose
# sub-heading, NOT a verification chapter: counting it would let an ADR with no
# forward-looking acceptance criteria pass (假阴性放行).
_SHAPE_VERIFICATION_SECTION = re.compile(
    r"^##\s*(?:\d+[.)]\s*)?(?:verification|验证)(?:[（(][^)）]*[)）])?\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Process-log markers — governance ledger / review history that must not live
# inside a decision document.
#
# The free-text family is kept verbatim: ADR-0060 explicitly accepted that
# "a body mentioning BLOCKER counts as a process-log marker" as a known
# heuristic limitation (warning level, opt-in).
_PROCESS_LOG_PATTERNS = [
    re.compile(r"第\s*\d+\s*轮\s*(?:critic|对抗审稿|审稿|复审)"),
    re.compile(r"\b(?:BLOCKER|SHOULD_FIX|NITS?)\b"),
    re.compile(r"队列\s*#\d+|台账\s*Entry\s*#\d+"),
]

# Heading-anchored markers — the two shapes this repo actually drifts into.
# Anchored to the heading line so prose mentions are not double-counted.
#   (a) process_log_heading  — process / version history
#   (b) shape_sprawl_heading — the ADR grew into a how-to / test plan
_SHAPE_PROCESS_LOG_HEADINGS = [
    re.compile(r"^#{2,4}\s.*(?:修订日志|修订记录|变更日志|修订要点|changelog|revision log)", re.IGNORECASE),
    re.compile(r"^#{2,4}\s.*(?:实施记录|实施状态|implementation status|post-hoc fix record|事后修复记录)", re.IGNORECASE),
]
_SHAPE_SPANGLY_HEADINGS = [
    re.compile(r"^#{2,4}\s.*\b(?:implementation|test strategy|rollout)\b", re.IGNORECASE),
    re.compile(r"^#{2,4}\s.*(?:测试策略|测试改动|实施步骤|实施计划|验收记录)", re.IGNORECASE),
    # a change id in a heading is a change ledger, not a decision
    re.compile(r"^#{2,4}\s.*\bfix-[a-z0-9][a-z0-9-]*", re.IGNORECASE),
]

# Column headers that carry the *reason*, not the *conclusion*. The
# alternatives table must have at least one column that is neither the subject
# column nor a reason column — otherwise the conclusion only lives in prose and
# cannot be read mechanically.
_ALTERNATIVES_REASON_COLUMNS = {
    "理由", "原因", "说明", "备注", "优点", "缺点",
    "reason", "rationale", "pros", "cons", "explanation",
}


@dataclass(frozen=True)
class ShapeFinding:
    """One shape-budget violation, in one ADR."""

    signal: str
    file: str
    detail: str


def _split_table_row(line: str) -> list[str]:
    """Split a markdown table row on unescaped pipes."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    return cells


def _is_table_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c) for c in cells)


def _section_body(text: str, heading_re: re.Pattern) -> Optional[str]:
    """Body of the first heading matching `heading_re`, up to the next heading of
    the same or a higher level.

    Reuses the *same* regex as the presence check, so the two cannot drift.
    """
    m = heading_re.search(text)
    if not m:
        return None
    head = text[m.start():m.start() + 8]
    level = max(2, len(head) - len(head.lstrip("#")))
    start = m.end()
    nxt = None
    for m2 in re.finditer(r"^(#{2,4})\s", text[start:], re.MULTILINE):
        if len(m2.group(1)) <= level:
            nxt = start + m2.start()
            break
    return text[start:nxt] if nxt is not None else text[start:]


def _verification_findings(text: str, name: str) -> list[ShapeFinding]:
    """Verification chapter must exist AND carry at least one checkable criterion."""
    body = _section_body(text, _SHAPE_VERIFICATION_SECTION)
    if body is None:
        return [ShapeFinding("missing_verification", name, "缺 Verification（前瞻验收判据）章节")]
    if not re.search(r"^\s*[-*]\s*\[[ xX]\]", body, re.MULTILINE):
        return [ShapeFinding("verification_section_empty", name, "Verification 章内无可勾选判据")]
    return []


def _alternatives_findings(text: str, name: str) -> list[ShapeFinding]:
    """The alternatives table must exist, carry ≥3 rows, and expose a conclusion."""
    body = _section_body(text, _SHAPE_REQUIRED_SECTIONS["Alternatives"])
    if body is None:
        return []  # a missing Alternatives chapter is reported by the section check
    table: list[list[str]] = []
    for line in body.splitlines():
        if "|" in line:
            cells = _split_table_row(line)
            if len(cells) >= 2:
                table.append(cells)
                continue
        if table:
            break
    if len(table) < 2:
        return [ShapeFinding("alternatives_table_missing", name, "备选方案章内未找到对比表")]
    header = table[0]
    data = [row for row in table[1:] if not _is_table_separator(row)]
    findings: list[ShapeFinding] = []
    if len(data) < 3:
        findings.append(ShapeFinding(
            "alternatives_table_too_few_rows", name,
            f"备选方案表只有 {len(data)} 行数据（要求 ≥3 行）",
        ))
    rest = [c.strip() for c in header[1:] if c.strip()]
    if not any(c.lower() not in _ALTERNATIVES_REASON_COLUMNS for c in rest):
        findings.append(ShapeFinding(
            "alternatives_table_no_conclusion_column", name,
            f"备选方案表缺『结论』列（表头: {' | '.join(header)}）",
        ))
    return findings


def _iter_adr_files(project_root: str, paths: dict):
    """Yield ADR files (excluding the reserved template) under the ADR dir."""
    adr_dir = Path(project_root) / paths["adr_dir"]
    if not adr_dir.is_dir():
        return
    for f in sorted(adr_dir.glob(paths["adr_pattern"])):
        if f.name.endswith("-0000-template.md"):
            continue
        yield f


def adr_shape_findings(ctx: dict) -> list[ShapeFinding]:
    """Structured shape-budget findings for the ADRs selected by `ctx`.

    This is the **single source of truth** for shape checking: the gate
    (`_check_adr_shape`) and the standalone CLI
    (`skills/rdd-arch/scripts/adr_shape_check.sh`) both consume it, so the two
    cannot drift apart.

    Scope: `ctx["adr_files"]` (an explicit list) restricts the scan; otherwise
    every ADR in the ADR dir is scanned. An empty scan is reported as a finding
    rather than silently passing.
    """
    project_root = ctx.get("project_root", ".")
    paths = _read_handoff(project_root)

    line_limit = int(os.environ.get("ARCH_ADR_LINE_LIMIT", str(_DEFAULT_ADR_LINE_LIMIT)))
    status_max = int(os.environ.get("ARCH_ADR_STATUS_MAX", str(_DEFAULT_ADR_STATUS_MAX)))

    explicit = ctx.get("adr_files")
    if explicit:
        files = [Path(f) for f in explicit]
    else:
        files = list(_iter_adr_files(project_root, paths))

    findings: list[ShapeFinding] = []
    if not files:
        findings.append(ShapeFinding(
            "no_adr_files_scanned", "",
            f"未扫描到任何 ADR（adr_dir={paths.get('adr_dir', '?')}）",
        ))
        return findings

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        name = f.name

        if len(lines) > line_limit:
            findings.append(ShapeFinding(
                "line_budget", name, f"{len(lines)} 行 > {line_limit} 行"))

        missing = [
            sec for sec, pat in _SHAPE_REQUIRED_SECTIONS.items()
            if not pat.search(text)
        ]
        if missing:
            findings.append(ShapeFinding(
                "missing_section", name, f"缺章节 {', '.join(missing)}"))

        findings.extend(_verification_findings(text, name))
        findings.extend(_alternatives_findings(text, name))

        log_hits = sum(len(pat.findall(text)) for pat in _PROCESS_LOG_PATTERNS)
        if log_hits:
            findings.append(ShapeFinding(
                "process_log", name, f"{log_hits} 处过程日志标记"))

        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue
            if any(p.search(stripped) for p in _SHAPE_PROCESS_LOG_HEADINGS):
                findings.append(ShapeFinding(
                    "process_log_heading", name, f"标题含过程/版本史: {stripped[:60]}"))
            elif any(p.search(stripped) for p in _SHAPE_SPANGLY_HEADINGS):
                findings.append(ShapeFinding(
                    "shape_sprawl_heading", name, f"标题越界成实施细节: {stripped[:60]}"))

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(">") and re.search(r"状态|status", stripped, re.IGNORECASE):
                if len(stripped) > status_max:
                    findings.append(ShapeFinding(
                        "status_line_too_long", name,
                        f"Status 行 {len(stripped)} 字符 > {status_max}"))
                break

    return findings


def _check_adr_shape(ctx: dict) -> tuple[bool, Optional[str]]:
    """Pass if ADRs stay within the decision-document shape budget.

    Signals per file (all warning level, opt-in via `ARCH_SHAPE_CHECK=yes`):

      1. body longer than the line budget (default 250, `ARCH_ADR_LINE_LIMIT`)
      2. a missing required section (Context / Decision / Consequences / Alternatives)
      3. a missing or empty Verification chapter
      4. an alternatives table that is absent / under-populated / has no conclusion column
      5. review-process log markers (审稿轮次 / BLOCKER 清单 / 队列号 / 台账 Entry)
      6. heading-level process-log or how-to sprawl markers
      7. a Status line carrying a long version history (`ARCH_ADR_STATUS_MAX`)

    Scope: `ctx["adr_files"]` (explicit list of paths) restricts the check to
    those files; otherwise every ADR in the ADR dir is scanned. An empty scan
    is reported as a finding rather than silently passing.

    Warning level only. Opt-in for the aggregate report via
    `ARCH_SHAPE_CHECK=yes` — existing ADRs are pre-existing debt and are not
    retroactively blocked.
    """
    findings = adr_shape_findings(ctx)
    ctx["shape_findings"] = findings
    if findings:
        return (False, "warning")
    return (True, None)


# ---------- the four checks (all return (passed, severity)) ----------


def _check_arch_alignment(ctx: dict) -> tuple[bool, Optional[str]]:
    """Pass if all ADR-NNNN references in roadmap.md and theme docs resolve.

    ADR-0018 §3.1. A "ghost" reference (ADR mentioned in text but no matching
    file in adr_dir) usually means the architect forgot to commit or the
    roadmap drifted from reality. We only warn; humans can override.

    CHANGED 2026-09-30 (per ADR-0057): scans all theme docs (*.md in
    architecture_dir) instead of *-gap-analysis.md. Theme docs are rdd-arch's
    primary composition artifacts and contain the same ADR cross-references.
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
        for theme_doc in arch_dir.glob("*.md"):
            if theme_doc.name.endswith("-0000-template.md"):
                continue
            referenced.update(_extract_adr_refs_in_file(theme_doc))

    ghosts = referenced - existing
    if ghosts:
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


def _check_file_size(ctx: dict) -> tuple[bool, Optional[str]]:
    """Check if any Python file in _lib exceeds size limit (warning-level).

    Rationale: Large files often indicate god classes or mixed responsibilities.
    This check surfaces potential refactoring candidates without blocking.

    Environment:
        ARCH_FILE_SIZE_LIMIT: max lines before warning (default 300)
        ARCH_FILE_SIZE_SCAN_PATHS: colon-separated paths to scan (default _lib)
    """
    project_root = ctx.get("project_root", ".")
    max_lines = int(os.environ.get("ARCH_FILE_SIZE_LIMIT", "300"))
    scan_paths = os.environ.get(
        "ARCH_FILE_SIZE_SCAN_PATHS", "_lib"
    ).split(":")

    oversized_files = []
    for scan_path in scan_paths:
        scan_dir = Path(project_root) / scan_path
        if not scan_dir.exists():
            continue

        for py_file in scan_dir.glob("**/*.py"):
            try:
                line_count = len(py_file.read_text().splitlines())
                if line_count > max_lines:
                    relative = py_file.relative_to(project_root)
                    oversized_files.append(f"{relative} ({line_count} lines)")
            except Exception:
                continue  # Skip files we can't read

    if oversized_files:
        msg = f"Files exceeding {max_lines} lines: " + ", ".join(oversized_files[:5])
        if len(oversized_files) > 5:
            msg += f" ... and {len(oversized_files) - 5} more"
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
            ("adr_no_placeholders", _check_adr_clarity),
            ("arch_handoff_actionable", _check_handoff_actionable),
            ("file_size_limit", _check_file_size),
        ]
        # adr_shape is opt-in: it flags ADRs that outgrew the decision-document
        # shape. Existing ADRs are pre-existing debt — enabling this must not
        # retroactively fail an unrelated project's arch_done gate.
        if os.environ.get("ARCH_SHAPE_CHECK", "").strip().lower() in _STRICT_TRUE:
            checks.append(("adr_shape", _check_adr_shape))
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
            if name == "adr_shape":
                findings = ctx.get("shape_findings") or []
                if findings:
                    report.detail[name]["findings"] = [
                        {"signal": f.signal, "file": f.file, "detail": f.detail}
                        for f in findings
                    ]
            if not passed:
                if severity == "warning":
                    report.warnings.append(name)
                else:
                    report.failed_checks.append(name)
                    report.passed = False
        return report