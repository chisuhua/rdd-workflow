"""Spec residue scan — retired-stage names in adopted capability specs.

Companion to :mod:`checks.v4_residue_check` (rules R1–R3 scan ``_lib/`` and
``skills/``).  This module adds the **spec surface**: ``openspec/specs/*/spec.md``
is where an adopted capability tells readers what to build, so a retired stage
name there is a *live contract defect* — someone following the spec will
implement a flow that no longer exists, and no check would say a word.

Docs: ``openspec/specs/**`` is gitignored in rdd-workflow itself (only local
copies exist), so this scanner must degrade gracefully when the directory is
absent (see :attr:`ScanResult.files_scanned`).

## Scan roots (locked)

Exactly ``<project_root>/openspec/specs/*/spec.md`` — one level, no recursion.
``openspec/changes/**`` is **never** scanned: unarchived change directories
quote retired names freely (archaeology), so scanning them fails en masse.

## Normative scope (locked — see CALIBRATION below)

Included:

* ``### Requirement:`` title line + its body up to the next heading;
* ``#### Scenario:`` title line + its body;
* fenced code blocks that live inside either of the above.

Excluded: ``## Purpose``, ``# Title``, and any prose outside a Requirement.

Fenced code blocks count because a route/enum listing inside a fence is exactly
the text a reader copies.  Saying "don't use the old name" in prose while a
fence keeps it is the worst form of this drift.

## CALIBRATION — 4 boolean combos, measured 2026-11-20 on rdd-workflow

``code_block_in`` × ``title_in`` → (occurrences, specs):

===============  ==============  ======  =====
code_block_in    title_in        occ.    specs
===============  ==============  ======  =====
True (chosen)    True (chosen)   350     46
True             False           320     46
False            True            348     45
False            False           318     45
===============  ==============  ======  =====

Both switches default to ``True`` and are **frozen constants** at the call sites
(the doctor check and the census generator pass nothing).  Locking them is what
makes the numbers reproducible: "cleanup complete" means *this* baseline went to
zero, and the census ledger header records the values.

## Word boundary

``(?<![\\w-])(...)(?![\\w-])`` — a token followed by ``-`` is a *different* name
(``guide-plan-quick-finish`` is a proposal name, ``guide-arch-x`` is not a
stage), so it must not be matched as a prefix.  Calibrated by hand against the
corpus: naive ``\\bguide-plan\\b`` over-counts by 47 occurrences.

## Exemptions — inline annotation only (no file-level allowlist)

A retired name in a normative block may be legitimate.  Five categories:
``enum`` / ``proposal-name`` / ``guard`` / ``history`` / ``rename-history``.
Declare it with a **standalone line immediately after** the hit line::

    The route enum SHALL accept `guide-ship` for legacy state files.
    <!-- v4-residue:allow=enum -->

An annotation exempts **every retired token on the preceding line**.  Granularity
is therefore *line*, not *file* — a spec may mix legitimate and real residue as
long as they sit on different lines.  (Measured 2026-11-20: 46 of 259 hit lines
carry ≥2 distinct tokens, but zero lines need *different* dispositions, so the
line granularity loses nothing on the current corpus.  If that ever changes,
split the line.)

An annotation on the **same line** as the hit is ignored — it would be invisible
when the hit line is long, and a trailing comment is too easy to leave behind
after the token is deleted.  The hit is still reported, and the fix hint says so.

**Stale allow**: an annotation whose preceding line has no retired token is
reported.  Without that, exemption lists only ever grow and eventually become a
second false pass.

**Heuristics never exempt.** A hit line that says "the existing `guide-arch`"
is stale-but-not-false: it describes a retired name as a live thing.  That
downgrades the hit to a *warning about wording* — it does not exempt it.  The
only exemption is the explicit annotation above.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

#: Retired stage names (ADR-0043 / ADR-0044 / ADR-0048) + the removed verifier.
RETIRED_TOKENS: Tuple[str, ...] = (
    "guide-arch",
    "guide-design",
    "guide-plan",
    "guide-ship",
    "guide-spec",
    "ac-verifier",
)

#: token 后不得再跟 '-' 或词字符：`guide-plan-quick-finish` 是**提案名**，不是 stage。
#: 左边界只排除词字符（**不排除** '-'）：`fill-phase-in-guide-plan` 以退役 stage 名
#: 作**尾部构件**，读者会据此去找 `guide-plan` ⇒ 必须抓（实测全仓仅此 1 处差异）。
TOKEN_RE = re.compile(
    r"(?<!\w)(" + "|".join(RETIRED_TOKENS) + r")(?![\w-])"
)

#: 五类合法引用（豁免 code 的取值集合）。
ALLOW_CODES = frozenset({
    "enum",            # ① 退役 stage 的历史枚举值（该值今天仍存在于 schema）
    "proposal-name",   # ② 提案名
    "guard",           # ③ 反漂移守卫自身（断言 / 示例数据）
    "history",         # ④ 归档历史（RETIRED 注记保留的原文）
    "rename-history",  # ⑤ 重命名说明
})

ALLOW_RE = re.compile(r"<!--\s*v4-residue:allow=([a-z-]+)\s*-->")

#: 「把旧名说成现存物」的措辞 ⇒ 降级提示（**不豁免**）。
WEAK_WORDING = ("the existing", "现存的")

_SPECS_REL = ("openspec", "specs")
_FENCE = "```"
_REQ_PREFIX = "### Requirement:"
_SCEN_PREFIX = "#### Scenario:"


@dataclass(frozen=True)
class Hit:
    """One retired-token occurrence inside a normative block."""

    file: str                # posix path relative to project root
    line: int                # 1-based line the token sits on
    block_line: int          # 1-based line the enclosing block starts on
    requirement_title: str   # enclosing Requirement title ('' when unowned)
    block_kind: str          # 'requirement' | 'scenario' | 'code'
    matched_token: str
    category: str            # allow code, or '' when unannotated
    weak_wording: bool       # downgrade hint (never an exemption)


@dataclass(frozen=True)
class StaleAllow:
    """An ``allow`` annotation whose exempted line carries no retired token."""

    file: str
    line: int
    code: str


@dataclass
class ScanResult:
    files_scanned: int
    hits: List[Hit] = field(default_factory=list)
    stale_allows: List[StaleAllow] = field(default_factory=list)
    #: ``(file, line)`` pairs whose annotation sits on the hit line itself.
    #: Such annotations are ignored (they exempt nothing) — reported so the
    #: fix hint can say why the hit was not suppressed.
    ignored_inline: List[Tuple[str, int]] = field(default_factory=list)
    #: ``(file, line, bad_code)`` for annotations with a code outside
    #: :data:`ALLOW_CODES`.  A typo must **not** silently exempt.
    invalid_annotations: List[Tuple[str, int, str]] = field(default_factory=list)

    @property
    def checked_anything(self) -> bool:
        """False on a clone without ``openspec/specs`` — NOT the same as clean."""
        return self.files_scanned > 0

    def blocks(self) -> List[Tuple[str, int]]:
        """Distinct ``(file, block_line)`` pairs — the finding unit."""
        return sorted({(h.file, h.block_line) for h in self.hits})


@dataclass
class _Block:
    kind: str        # 'requirement' | 'scenario'
    start: int       # 1-based line of the block's heading
    title: str
    lines: List[Tuple[int, str]]   # (lineno, text) for body lines (heading excluded)
    in_code: frozenset[int]        # lineno set that lives inside a fenced block


def _iter_spec_files(specs_root: Path):
    """``openspec/specs/*/spec.md`` — exactly this level, non-recursive."""
    if not specs_root.is_dir():
        return
    for entry in sorted(specs_root.iterdir()):
        if not entry.is_dir():
            continue
        spec = entry / "spec.md"
        if spec.is_file():
            yield spec


def _split_blocks(text: str) -> List[_Block]:
    """Group a spec into Requirement / Scenario blocks (normative scope only).

    ``## Purpose`` / ``# Title`` / prose outside a Requirement terminate the
    current block — they are deliberately *not* normative.
    """
    blocks: List[_Block] = []
    cur: Optional[_Block] = None
    in_fence = False
    fence_buf: List[Tuple[int, str]] = []

    def flush() -> None:
        nonlocal cur
        if cur is not None:
            blocks.append(cur)   # a heading-only block still matches its title
        cur = None

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()

        if stripped.startswith(_FENCE):
            if not in_fence:
                in_fence = True
                fence_buf = []
            else:
                in_fence = False
                if cur is not None:
                    # The fence belongs to the enclosing block.  Record every
                    # line so `code_block_in=False` can filter them out later.
                    cur.lines.extend(fence_buf)
                    cur.in_code = cur.in_code | {n for n, _ in fence_buf}
                fence_buf = []
            continue
        if in_fence:
            fence_buf.append((lineno, line))
            continue

        if stripped.startswith("#"):
            if stripped.startswith(_REQ_PREFIX) or stripped.startswith(_SCEN_PREFIX):
                flush()
                is_req = stripped.startswith(_REQ_PREFIX)
                title = stripped.split(":", 1)[1].strip() if ":" in stripped else stripped
                cur = _Block(
                    kind="requirement" if is_req else "scenario",
                    start=lineno,
                    title=title,
                    lines=[],
                    in_code=frozenset(),
                )
            else:
                flush()
            continue

        if cur is not None:
            cur.lines.append((lineno, line))

    flush()
    return blocks


def _allow_annotations(lines: List[str]) -> List[Tuple[int, str]]:
    """``(lineno, code)`` for every **valid** standalone annotation line."""
    out: List[Tuple[int, str]] = []
    for lineno, code in _raw_annotations(lines):
        if code in ALLOW_CODES:
            out.append((lineno, code))
    return out


def _raw_annotations(lines: List[str]) -> List[Tuple[int, str]]:
    """``(lineno, code)`` for every standalone annotation, valid or not."""
    out: List[Tuple[int, str]] = []
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not (stripped.startswith("<!--") and stripped.endswith("-->")):
            continue
        m = ALLOW_RE.search(line)
        if m:
            out.append((lineno, m.group(1)))
    return out


def _inline_annotations(lines: List[str]) -> List[int]:
    """Line numbers whose annotation is NOT standalone (ignored, not an exemption)."""
    standalone = {n for n, _ in _raw_annotations(lines)}
    return [
        lineno for lineno, line in enumerate(lines, 1)
        if ALLOW_RE.search(line) and lineno not in standalone
    ]


def _title_stack(blocks: List[_Block]) -> dict:
    """Map a Scenario block's start line to the Requirement title enclosing it."""
    out: dict = {}
    current_req = ""
    for blk in sorted(blocks, key=lambda b: b.start):
        if blk.kind == "requirement":
            current_req = blk.title
        out[blk.start] = current_req
    return out


def scan_specs(
    project_root: Path,
    *,
    code_block_in: bool = True,
    title_in: bool = True,
) -> ScanResult:
    """Scan ``openspec/specs/*/spec.md`` for retired-stage names.

    Args:
        project_root: project root (the directory holding ``openspec/``).
        code_block_in: whether fenced code blocks are normative (frozen True).
        title_in: whether ``### Requirement:`` / ``#### Scenario:`` lines are
            themselves matched (frozen True).

    Returns:
        :class:`ScanResult`.  ``files_scanned == 0`` means *nothing was
        checked* — callers must not render that as "clean".
    """
    root = Path(project_root)
    specs_root = root.joinpath(*_SPECS_REL)
    hits: List[Hit] = []
    stale: List[StaleAllow] = []
    ignored: List[Tuple[str, int]] = []
    invalid: List[Tuple[str, int, str]] = []
    scanned = 0

    for spec in _iter_spec_files(specs_root):
        scanned += 1
        text = spec.read_text(encoding="utf-8", errors="replace")
        raw_lines = text.splitlines()
        rel = spec.relative_to(root).as_posix()

        annotations = dict(_allow_annotations(raw_lines))
        inline_only = set(_inline_annotations(raw_lines))
        ignored.extend((rel, ln) for ln in sorted(inline_only))
        invalid.extend(
            (rel, ln, code) for ln, code in _raw_annotations(raw_lines)
            if code not in ALLOW_CODES
        )

        # Exemption table: hit line -> allow code (annotation on the NEXT line)
        exempted: dict = {}
        for ann_line, code in annotations.items():
            target = ann_line - 1
            if 1 <= target <= len(raw_lines):
                exempted.setdefault(target, code)

        blocks = _split_blocks(text)
        req_title = _title_stack(blocks)

        hit_lines: set = set()
        for blk in blocks:
            owner = req_title.get(blk.start, "")
            candidates: List[Tuple[int, str, bool]] = []
            if title_in:
                candidates.append((blk.start, raw_lines[blk.start - 1], False))
            for lineno, body in blk.lines:
                is_code = lineno in blk.in_code
                if is_code and not code_block_in:
                    continue
                candidates.append((lineno, body, is_code))

            for lineno, body, is_code in candidates:
                for m in TOKEN_RE.finditer(body):
                    hit_lines.add(lineno)
                    code = exempted.get(lineno, "")
                    hits.append(Hit(
                        file=rel,
                        line=lineno,
                        block_line=blk.start,
                        requirement_title=owner,
                        block_kind="code" if is_code else blk.kind,
                        matched_token=m.group(1),
                        category=code,
                        weak_wording=(
                            not code
                            and blk.kind == "requirement"
                            and any(w in body.lower() for w in WEAK_WORDING)
                        ),
                    ))

        # `annotations` keys were computed before we knew the hit lines; a line
        # may legitimately carry a token excluded by `title_in`/`code_block_in`,
        # so recompute "does the exempted line have any token at all".
        for ann_line, code in annotations.items():
            target = ann_line - 1
            has_token = (
                1 <= target <= len(raw_lines)
                and TOKEN_RE.search(raw_lines[target - 1]) is not None
            )
            if not has_token:
                stale.append(StaleAllow(file=rel, line=ann_line, code=code))

    hits.sort(key=lambda h: (h.file, h.line, h.matched_token))
    stale.sort(key=lambda s: (s.file, s.line))
    ignored.sort()
    invalid.sort()
    return ScanResult(
        files_scanned=scanned,
        hits=hits,
        stale_allows=stale,
        ignored_inline=ignored,
        invalid_annotations=invalid,
    )


__all__ = [
    "ALLOW_CODES",
    "Hit",
    "RETIRED_TOKENS",
    "ScanResult",
    "StaleAllow",
    "TOKEN_RE",
    "scan_specs",
]
