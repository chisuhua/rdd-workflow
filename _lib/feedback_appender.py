"""Append-only feedback writer for .rddf/improvements/*.md files.

This is the SINGLE WRITER for the ## Feedback section per ADR-0037.
All downstream skills (guide-design, guide-plan, guide-ship, rdd-verifier)
MUST route through this module via the `rddf feedback add` CLI.

Writes are atomic via `_lib.core.atomic_write` and serialized via
`_lib.core.lock.FileLock` to prevent the corruption mode seen in
`.rddf/state/iteration.corrupt.*` (multi-writer race).
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Optional

import yaml

from _lib.core.atomic_write import atomic_write_text
from _lib.core.lock import FileLock, LockTimeout

__all__ = [
    "append_feedback",
    "FeedbackError",
    "LoopExceededError",
    "generate_feedback_id",
    "VALID_SOURCES",
    "VALID_KINDS",
    "COUNTERS_FILE",
]

VALID_SOURCES = {"guide-design", "guide-plan", "guide-ship", "rdd-verifier", "human"}
VALID_KINDS = {"needs-revision", "ac-fail", "rejected", "blocked", "noted"}
REVISION_KINDS = {"needs-revision", "ac-fail"}  # kinds that bump revision_count
COUNTERS_FILE = ".rddf/state/.feedback-counters.json"


class FeedbackError(Exception):
    """Base error for feedback_appender."""


class LoopExceededError(FeedbackError):
    """revision_count > max_revisions. Per ADR-0037 §3.6, force human escalation."""


def generate_feedback_id(*, seq: int) -> str:
    """Return feedback-YYYYMMDD-NNN (UTC date + zero-padded seq)."""
    date_part = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    return f"feedback-{date_part}-{seq:03d}"


def _split_frontmatter(text: str) -> tuple[dict, str, str]:
    """Return (frontmatter_dict, fm_block_with_delimiters, body_after).

    Raises FeedbackError if malformed.
    """
    if not text.startswith("---"):
        return {}, "", text
    try:
        end = text.index("\n---", 3)
        fm_inner = text[3:end].lstrip("\n")
        rest = text[end + 4:].lstrip("\n")
        fm = yaml.safe_load(fm_inner) or {}
        return fm, text[: end + 4], rest
    except (ValueError, yaml.YAMLError) as exc:
        raise FeedbackError(f"Malformed frontmatter: {exc}") from exc


def _join_frontmatter(fm: dict) -> str:
    """Serialize frontmatter dict back to ---\\n...\\n--- block."""
    yaml_text = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{yaml_text}\n---\n"


def _read_counter(target: Path) -> int:
    """Read the per-file feedback seq counter (default 0)."""
    cf = target.parent / ".feedback-counters.json"
    if not cf.exists():
        return 0
    data = json.loads(cf.read_text())
    return int(data.get(str(target.name), 0))


def _write_counter(target: Path, seq: int) -> None:
    """Persist the per-file feedback seq counter."""
    cf = target.parent / ".feedback-counters.json"
    cf.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if cf.exists():
        data = json.loads(cf.read_text())
    data[str(target.name)] = seq
    atomic_write_text(cf, json.dumps(data, indent=2, ensure_ascii=False))


def _check_loop_guard(fm: dict, kind: str) -> None:
    """Raise LoopExceededError if kind is revision-counting and over cap."""
    if kind not in REVISION_KINDS:
        return
    rc = int(fm.get("revision_count", 0))
    mr = int(fm.get("max_revisions", 3))
    if rc >= mr:
        raise LoopExceededError(
            f"Loop exceeded: revision_count={rc} >= max_revisions={mr}. "
            f"Escalate to human decision: defer, split, or reject. "
            f"Reference: ADR-0037 §3.6."
        )


def _render_entry(
    *,
    feedback_id: str,
    source: str,
    kind: str,
    body: str,
    created_at: str,
    ref_change: Optional[str],
) -> str:
    """Render one ## Feedback subsection block."""
    lines = [f"### {feedback_id}", ""]
    lines.append(f"- **source**: {source}")
    lines.append(f"- **kind**: {kind}")
    lines.append(f"- **created_at**: {created_at}")
    if ref_change:
        lines.append(f"- **ref_change**: {ref_change}")
    lines.append(f"- **resolution**: open")
    lines.append("")
    lines.append("#### Body")
    lines.append("")
    lines.append(body)
    lines.append("")
    return "\n".join(lines)


def append_feedback(
    *,
    target_path: str,
    source: str,
    kind: str,
    body: str,
    ref_change: Optional[str] = None,
) -> str:
    """Append a feedback entry to the target file's ## Feedback section.

    Args:
        target_path: Absolute path to .rddf/improvements/<name>.md.
        source: One of VALID_SOURCES.
        kind: One of VALID_KINDS.
        body: Feedback body text (1-10000 chars).
        ref_change: Optional OpenSpec change name to cross-reference.

    Returns:
        The generated feedback_id.

    Raises:
        FeedbackError: validation failure.
        LoopExceededError: revision_count exceeded max_revisions.
    """
    if source not in VALID_SOURCES:
        raise FeedbackError(f"Invalid source: {source!r}. Valid: {sorted(VALID_SOURCES)}")
    if kind not in VALID_KINDS:
        raise FeedbackError(f"Invalid kind: {kind!r}. Valid: {sorted(VALID_KINDS)}")
    if not (1 <= len(body) <= 10000):
        raise FeedbackError(f"Body length {len(body)} out of range [1, 10000]")

    target = Path(target_path)
    lock_path = target.with_suffix(target.suffix + ".lock")

    with FileLock(str(lock_path), timeout=10.0):
        text = target.read_text(encoding="utf-8") if target.exists() else ""
        fm, fm_block, body_text = _split_frontmatter(text)

        _check_loop_guard(fm, kind)

        seq = _read_counter(target) + 1
        feedback_id = generate_feedback_id(seq=seq)
        created_at = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")

        entry = _render_entry(
            feedback_id=feedback_id,
            source=source,
            kind=kind,
            body=body,
            created_at=created_at,
            ref_change=ref_change,
        )

        # Ensure ## Feedback section
        if "## Feedback" not in body_text:
            new_body = body_text.rstrip() + "\n\n## Feedback\n\n" + entry
        else:
            # Append at the end of the file (after existing feedback)
            new_body = body_text.rstrip() + "\n\n" + entry

        # Update frontmatter
        if kind in REVISION_KINDS:
            fm["revision_count"] = int(fm.get("revision_count", 0)) + 1
        fm["last_feedback_id"] = feedback_id
        fm["last_feedback_at"] = created_at
        fm["feedback_status"] = "needs-revision" if kind in REVISION_KINDS else "noted"

        new_text = _join_frontmatter(fm) + "\n" + new_body
        atomic_write_text(target, new_text)
        _write_counter(target, seq)

    return feedback_id