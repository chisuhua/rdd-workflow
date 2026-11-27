"""Classify an improvement's lifecycle state (``状态``) for the dashboard.

Improvement files carry their lifecycle state as free-form prose in the
front-matter ``状态`` field, e.g.::

    状态: "✅ **已完成并归档**（2026-11-19 立项 #487 → 归档;delta 已合并进 …）"

The dashboard's Pending section needs two things from that field:

1. whether the item is **terminal** (delivered ⇒ must NOT be listed as
   pending), and
2. a **short display label** for the status column.

Both are derived from the **leading marker only** — the prose that follows
often mentions residual items ("唯一未达成项 = D-1 待裁") and must never flip
the classification of an item whose leading marker says it is delivered.

Why a separate module: the classification is pure and needs unit coverage
without spinning up a whole dashboard collect.
"""
from __future__ import annotations

import re

# Leading markers that mean "delivered" ⇒ terminal (must not be listed pending).
# Order matters: the more specific marker must come first.
#
#: **Single definition point** for the terminal vocabulary (AC5): the
#: ``rddf status --help`` text renders THIS table, so a second copy would be
#: a drift surface. Keep it in sync with the project registry's whitelist
#: (§6.8 完成态 token) — the registry writes 已落地 / 已拆分 / 已取代, and the
#: tool must judge them delivered too.
TERMINAL_MARKERS: tuple[tuple[str, str], ...] = (
    ("已完成并归档", "已归档"),
    ("已实施并验收", "已完成"),
    ("已归档", "已归档"),
    ("已完成", "已完成"),
    ("已实施", "已实施"),
    # Registry completion tokens (fix-rddf-status-terminal-markers):
    # a delivered proposal is not work to be done, whichever wording the
    # registry used for it.
    ("已落地", "已落地"),
    ("已拆分", "已作废"),
    ("已取代", "已作废"),
    # English markers. The 2026-11-17/18 batch writes `状态: implemented
    # (2026-11-17)`; without these the item was classified non-terminal and
    # rendered as pending with a truncated label ("implemented (202").
    ("implemented", "已实施"),
    ("completed", "已完成"),
    # Voided / superseded proposals are terminal too: they must NOT stay in
    # the Pending pool (a proposal whose plan was replaced by a more
    # thorough one is not work to be done).
    ("已作废", "已作废"),
    ("作废", "已作废"),
    ("superseded", "已作废"),
    ("archived", "已归档"),
)

# Leading markers that mean "still to be worked on" ⇒ pending.
_OPEN_MARKERS: tuple[tuple[str, str], ...] = (
    ("未立项", "未立项"),
    ("待立项", "待立项"),
    ("已立项", "已立项"),
    ("draft", "Draft"),
    ("规划输入", "规划输入"),
    ("backlog", "未立项"),
    # "待审查" (awaiting review), "待回填" (awaiting a backfill) and
    # "已推迟" (deferred) are distinct from "待讨论": the proposal has a
    # decision or a concrete pending action attached, it is just not the
    # next thing to do. Without them all three collapse into the
    # empty-status fallback label "待讨论".
    ("待审查", "待审查"),
    ("待回填", "待回填"),
    ("已推迟", "已推迟"),
)

# Partially closed ⇒ stays visible (a human decision is still owed).
_PARTIAL_MARKERS: tuple[tuple[str, str], ...] = (
    ("已闭合", "部分闭合"),
)

_MARKUP_RE = re.compile(r"[*`\"'\s]+")
_LEADING_SYMBOL_RE = re.compile(r"^[^\w一-鿿]+")


def _strip_markup(text: str) -> str:
    """Drop markdown emphasis / quotes / backticks and collapse whitespace."""
    return _MARKUP_RE.sub(" ", text).strip()


def _leading_marker(text: str) -> str:
    """Return the status text with markup and leading symbols removed."""
    stripped = _strip_markup(text)
    return _LEADING_SYMBOL_RE.sub("", stripped, count=1).lstrip()


def classify_improvement_status(raw: str) -> tuple[bool, str]:
    """Classify a raw ``状态`` value.

    Returns ``(is_terminal, label)``:

    - ``is_terminal`` — True when the leading marker says the item is
      delivered (archived / completed / implemented). Terminal items are
      excluded from the dashboard's Pending section.
    - ``label`` — a short display label for the status column.
    """
    if not raw or not raw.strip():
        # No status recorded ⇒ treat as "not yet discussed" (legacy behaviour).
        return False, "待讨论"

    marker = _leading_marker(raw)
    if not marker:
        return False, "待讨论"

    lowered = marker.lower()
    for needle, label in TERMINAL_MARKERS:
        if lowered.startswith(needle.lower()):
            return True, label
    for needle, label in _OPEN_MARKERS:
        if lowered.startswith(needle.lower()):
            return False, label
    for needle, label in _PARTIAL_MARKERS:
        if needle in marker:
            return False, label
    # Unknown shape ⇒ show the head of the text so the row stays recognisable.
    return False, marker[:16]
