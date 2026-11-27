"""Deferral registration — the carrier for「另案立项」.

A deferral ("本次不做 / 另案立项") is a legitimate way to close work, but
without a **registration target** the deferred defect has no debt entry:
it can be deferred forever and nobody can see it coming back. Measured:
``fix-spec-v3-naming-sync.md:192`` recorded「另案立项」and the defect recurred
twice more (2026-11-26) with no improvement file to point at.

The convention (single source of truth for the wording):

    另案（已登记：<improvement-slug>）     ← the debt exists as an improvement
    另案（backlog：<topic>）               ← the debt exists as a backlog placeholder

Either form registers the deferral; a bare「另案」does **not** and is reported
by the ``deferral-registration`` doctor category.

The module owns both the wording list and the target grammar, so the
convention document, the scanner and the tests cannot drift apart.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

#: The deferral wordings this convention governs (grep-able anchors).
DEFERRAL_PHRASES: tuple[str, ...] = (
    "另案",
    "另立",
    "另行立项",
    "后续另案",
)

#: The two legal registration forms — a deferral MUST carry one of them.
REGISTERED_FORM = "另案（已登记：<improvement-slug>）"
BACKLOG_FORM = "另案（backlog：<topic>）"

#: A target marker on the same line as the deferral wording.
TARGET_MARKER_RE = re.compile(r"(?:已登记|backlog)\s*[:：]\s*[^）\n]+")

#: Where deferrals are scanned (documents only — never source comments).
SCAN_DIRS: tuple[str, ...] = (
    ".rddf/improvements",
    ".rddf/reviews",
)

#: The exemption list (existing noise, registered once — not silently ignored).
EXEMPTIONS_FILE = ".rddf/deferral-exemptions.txt"


@dataclass(frozen=True)
class DeferralFinding:
    """One unregistered deferral."""

    path: str
    line: int
    phrase: str
    excerpt: str

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "line": self.line,
            "phrase": self.phrase,
            "excerpt": self.excerpt,
        }


def _phrases_in(line: str) -> list[str]:
    """Deferral wordings present in a line (longest first, so「另立」wins)."""
    found = [phrase for phrase in DEFERRAL_PHRASES if phrase in line]
    return sorted(found, key=len, reverse=True)


def is_registered(line: str) -> bool:
    """True when the line carries a registration target."""
    return bool(TARGET_MARKER_RE.search(line))


def scan_text(text: str, path: str = "") -> list[DeferralFinding]:
    """Find unregistered deferrals in a document body."""
    findings: list[DeferralFinding] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        phrases = _phrases_in(line)
        if not phrases:
            continue
        if is_registered(line):
            continue
        findings.append(
            DeferralFinding(
                path=path,
                line=lineno,
                phrase=phrases[0],
                excerpt=line.strip()[:120],
            )
        )
    return findings


def load_exemptions(project_root: str | Path) -> list[str]:
    """Read the exemption list (one relative path per line, ``#`` comments ok).

    A missing file ⇒ no exemptions (the scanner then reports everything).
    """
    path = Path(project_root) / EXEMPTIONS_FILE
    if not path.is_file():
        return []
    out: list[str] = []
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def iter_scan_targets(project_root: str | Path) -> Iterable[Path]:
    """Every document the convention applies to (markdown under SCAN_DIRS)."""
    root = Path(project_root)
    for rel in SCAN_DIRS:
        base = root / rel
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            yield path


def scan_project(project_root: str | Path,
                 exemptions: list[str] | None = None) -> list[DeferralFinding]:
    """Scan the project's documents for unregistered deferrals.

    Exempted paths are skipped entirely (existing noise is registered once in
    the exemption list — never silently ignored).
    """
    root = Path(project_root)
    skip = set(exemptions if exemptions is not None else load_exemptions(root))
    findings: list[DeferralFinding] = []
    for path in iter_scan_targets(root):
        rel = os.path.relpath(path, root)
        if rel in skip:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        findings.extend(scan_text(text, rel))
    return findings


def stale_exemptions(project_root: str | Path,
                     exemptions: list[str] | None = None) -> list[str]:
    """Exempted paths that no longer contain an unregistered deferral.

    A stale exemption is silently rotting debt in the opposite direction ⇒
    the caller is expected to surface it as「可清理」.
    """
    root = Path(project_root)
    listed = exemptions if exemptions is not None else load_exemptions(root)
    stale: list[str] = []
    for rel in listed:
        path = root / rel
        if not path.is_file():
            stale.append(rel)
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not scan_text(text, rel):
            stale.append(rel)
    return stale


__all__ = [
    "BACKLOG_FORM",
    "DEFERRAL_PHRASES",
    "DeferralFinding",
    "EXEMPTIONS_FILE",
    "REGISTERED_FORM",
    "SCAN_DIRS",
    "TARGET_MARKER_RE",
    "is_registered",
    "iter_scan_targets",
    "load_exemptions",
    "scan_project",
    "scan_text",
    "stale_exemptions",
]
