#!/usr/bin/env python3
"""Markdown link / cross-reference / version-drift checker (stdlib only).

Why this exists: the 2026-11-17 doc review fixed 10 broken links with a throwaway
script under /tmp — the finding tool was not kept, so the next round had to
rediscover it by hand. This file is the tool, in the repo, with no dependencies.

Modes:
  --all           scan every root in SCAN_ROOTS (default)
  --versions      list version / count claims and classify where each comes from
  --adr-refs      check that ADR-NNNN references resolve
  <path> ...     scan only the given files/dirs

Exit codes:
  0 = clean
  1 = findings (broken links, unresolved ADR refs, undefined versions, stale counts)
  2 = usage error

Two kinds of truth are deliberately NOT enforced here:
  - history: files under HISTORY_FILES keep their old version strings and old
    skill names — "eliminating drift" must not become "rewriting history".
  - examples: fenced code blocks contain sample output (e.g. "41 ADRs"), which
    is not a claim about the current state.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Explicit scan roots — a hard-coded list, so "what is covered" is answerable
# without reading the implementation. Adding a root is a deliberate act.
SCAN_ROOTS = ("docs", "skills", "openspec/specs")
ROOT_MD_GLOB = "*.md"

# Files whose content is history: version strings and old skill names are the
# subject matter there, not drift.
HISTORY_FILES = ("historical-evolution.md", "CHANGELOG.md")

# Workflow-lineage versions that exist (each introduced by a specific ADR).
# These are NOT the package version in package.json — different concepts.
KNOWN_WORKFLOW_VERSIONS = ("4.0", "4.0.1")

# Hard floors: a checker that scanned nothing must not report success.
MIN_FILES = 20
MIN_LINKS = 50

_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_FENCE_RE = re.compile(r"^\s*(\x60\x60\x60|~~~)")
_ADR_REF_RE = re.compile(r"\bADR-(\d{4})\b")
_VERSION_RE = re.compile(r"(?<![\w.])(v?)(\d+\.\d+\.\d+)(?![\w.])")
_COUNT_RE = re.compile(r"(?<![\w-])(\d+)\s+(skills|ADRs?)(?![\w-])")
_GUIDE_NAME_RE = re.compile(r"guide-(?:arch|design|plan|ship)")


def _strip_code_blocks(text: str) -> str:
    """Blank out fenced code blocks (keep line count so line numbers stay true)."""
    out: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        m = _FENCE_RE.match(line)
        if fence is None and m:
            fence = m.group(1)
            out.append("")
            continue
        if fence is not None:
            if m and m.group(1) == fence:
                fence = None
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def _mask_inline_code(line: str) -> str:
    """Blank out inline code spans (keeping column positions).

    A markdown link inside an inline code span is illustrative, not a link —
    GitHub does not render it either. Placeholders like ``[name](improvements/name.md)``
    live there, and treating them as real links would make the checker cry wolf.
    """
    out = list(line)
    in_span = False
    for i, ch in enumerate(line):
        if ch == "`":
            in_span = not in_span
            out[i] = " "
            continue
        if in_span:
            out[i] = " "
    return "".join(out)


def _slugify(text: str) -> str:
    """GitHub-ish heading slug: lowercase, drop punctuation, spaces to dashes."""
    s = text.strip().lower()
    s = re.sub(r"[\u3000\s]+", "-", s)
    s = re.sub(r"[^\w\-\u4e00-\u9fff]", "", s)
    return s.strip("-")


def _anchors(text: str) -> set[str]:
    """Anchor slugs a file exposes (headings + explicit HTML anchors)."""
    anchors: set[str] = set()
    for line in text.splitlines():
        m = re.match(r"^#{1,6}\s+(.*?)\s*#*$", line)
        if m:
            anchors.add(_slugify(m.group(1)))
        for a in re.findall(r"<a\s+(?:id|name)=\"([^\"]+)\"", line):
            anchors.add(a.lower())
    return anchors


def _iter_files(targets: list[str]) -> list[Path]:
    """Resolve the scan targets into a sorted list of markdown files."""
    files: set[Path] = set()
    for target in targets:
        p = Path(target)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if p.is_dir():
            files.update(f for f in p.rglob("*.md") if f.is_file())
        elif p.is_file():
            files.add(p)
    return sorted(files)


def _default_files() -> list[Path]:
    files: set[Path] = set()
    for root in SCAN_ROOTS:
        d = REPO_ROOT / root
        if d.is_dir():
            files.update(f for f in d.rglob("*.md") if f.is_file())
    files.update(f for f in REPO_ROOT.glob(ROOT_MD_GLOB) if f.is_file())
    return sorted(files)


def _is_history(path: Path) -> bool:
    return path.name in HISTORY_FILES


def _rel(path: Path) -> str:
    """Repo-relative path when possible; absolute otherwise (targeted scans
    may point outside the repo — a crash there would be a useless error)."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)

def check_links(files: list[Path], floor: tuple[int, int] | None = None) -> tuple[list[str], int]:
    """Broken relative links and missing anchors."""
    findings: list[str] = []
    link_count = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        body = _strip_code_blocks(text)
        anchors = _anchors(text)
        for lineno, raw_line in enumerate(body.splitlines(), 1):
            line = _mask_inline_code(raw_line)
            for m in _LINK_RE.finditer(line):
                target = m.group(1).strip()
                if target.startswith(("http://", "https://", "mailto:", "tel:", "data:")):
                    continue
                link_count += 1
                if target.startswith("#"):
                    if target[1:] and target[1:].lower() not in anchors:
                        findings.append(
                            f"{_rel(path)}:{lineno}: anchor not found: {target}"
                        )
                    continue
                rel, _, anchor = target.partition("#")
                if not rel:
                    continue
                dest = (path.parent / rel).resolve()
                if not dest.exists():
                    findings.append(
                        f"{_rel(path)}:{lineno}: broken link: {target}"
                    )
                    continue
                if anchor and dest.suffix == ".md":
                    dest_anchors = _anchors(
                        dest.read_text(encoding="utf-8", errors="replace")
                    )
                    if anchor.lower() not in dest_anchors:
                        findings.append(
                            f"{_rel(path)}:{lineno}: anchor not found: {target}"
                        )
    min_files, min_links = floor if floor is not None else (MIN_FILES, MIN_LINKS)
    if len(files) < min_files or link_count < min_links:
        findings.append(
            f"scan floor not met: files={len(files)} (min {min_files}), "
            f"links={link_count} (min {min_links}) — a checker that scanned "
            "nothing must not report success"
        )
    return findings, link_count


def check_adr_refs(files: list[Path]) -> list[str]:
    """ADR-NNNN references in docs/architecture must resolve to a real ADR."""
    known: set[str] = set()
    for p in (REPO_ROOT / "docs" / "adr").glob("ADR-*.md"):
        m = re.match(r"ADR-(\d{4})", p.name)
        if m:
            known.add(m.group(1))
    findings: list[str] = []
    for path in files:
        if path.parent.name != "architecture":
            continue
        body = _strip_code_blocks(path.read_text(encoding="utf-8", errors="replace"))
        for lineno, line in enumerate(body.splitlines(), 1):
            for m in _ADR_REF_RE.finditer(line):
                if m.group(1) not in known:
                    findings.append(
                        f"{_rel(path)}:{lineno}: unknown ADR reference: ADR-{m.group(1)}"
                    )
    return findings

def _known_phase_versions() -> set[str]:
    """Phase versions that a SKILL.md actually declares (「阶段 0.0.z」)."""
    found: set[str] = set()
    for skill in (REPO_ROOT / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8", errors="replace")
        found.update(re.findall(r"(?<![\w.])0\.0\.\d+(?![\w.])", text))
    return found


# A guide-* mention is legitimate when the line says so (removed / former /
# history). "Eliminating drift" must not become "rewriting history" — and the
# old stage names ARE the subject matter of the history documents.
_HISTORY_MARKER = re.compile(
    r"已移除|已删除|原 |formerly|不再|历史|histor|迁移|used to|v3|removed|was |不再是"
)


def check_guide_names(files: list[Path]) -> list[str]:
    """guide-* stage names outside a history context are drift."""
    findings: list[str] = []
    for path in files:
        if _is_history(path):
            continue
        body = _strip_code_blocks(path.read_text(encoding="utf-8", errors="replace"))
        for lineno, line in enumerate(body.splitlines(), 1):
            masked = _mask_inline_code(line)
            if not _GUIDE_NAME_RE.search(masked):
                continue
            if _HISTORY_MARKER.search(line):
                continue
            findings.append(
                f"{_rel(path)}:{lineno}: old stage name outside a history context: "
                f"{_GUIDE_NAME_RE.search(masked).group(0)}"
            )
    return findings


def version_report(files: list[Path]) -> tuple[list[str], list[str]]:
    """Derive the CURRENT-state claims in docs/architecture and check them.

    Scope is deliberately narrow: only the live architecture snapshot declares
    the present. ADRs, audit reports, superpowers plans and the CHANGELOG state
    the past — counting their version strings as "stale" would be nonsense.

    Four rules, each with a reason:
      F1 workflow version labels (v4.x.y) must exist in KNOWN_WORKFLOW_VERSIONS
      F2 a bare 0.0.z token is always a typo (a version lost its "v" prefix)
      F3 the "last regenerated as of vX.Y.Z" claim must equal package.json
      F4 current-count claims (N skills / N ADRs) must equal the measured count
    """
    pkg = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    skill_count = len(list((REPO_ROOT / "skills").glob("*/SKILL.md")))
    adr_count = len([
        p for p in (REPO_ROOT / "docs" / "adr").glob("ADR-*.md")
        if not p.name.endswith("-0000-template.md")
    ])
    findings: list[str] = []
    report: list[str] = []
    for path in files:
        rel = _rel(path)
        if _is_history(path):
            continue
        body = _strip_code_blocks(path.read_text(encoding="utf-8", errors="replace"))
        for lineno, line in enumerate(body.splitlines(), 1):
            # F1 — workflow version labels must exist (planned ones are exempt:
            #      an unreleased version announced as planned is forward-looking, not drift)
            planned = bool(re.search(r"planned|计划|未发布|proposed", line, re.IGNORECASE))
            for m in re.finditer(r"\bv(\d+\.\d+\.\d+)\b", line):
                ver = m.group(1)
                if ver == pkg:
                    report.append(f"{rel}:{lineno}: v{ver} -> package")
                    continue
                if ver.startswith("4."):
                    if planned:
                        report.append(f"{rel}:{lineno}: v{ver} -> planned")
                        continue
                    if ver in KNOWN_WORKFLOW_VERSIONS:
                        report.append(f"{rel}:{lineno}: v{ver} -> workflow")
                    else:
                        findings.append(
                            f"{rel}:{lineno}: undefined workflow version: v{ver} "
                            f"(known: {list(KNOWN_WORKFLOW_VERSIONS)})"
                        )
            # F2 — a 0.0.z token is a PHASE version (skills/*/SKILL.md namespaces
            #      them as 「阶段 0.0.z」). It must exist in some SKILL.md —
            #      deriving it beats guessing that it is a typo: 0.0.5 is real.
            for m in re.finditer(r"(?<![\w.])0\.0\.\d+(?![\w.])", line):
                phase = m.group(0)
                if phase in _known_phase_versions():
                    report.append(f"{rel}:{lineno}: {phase} -> phase")
                else:
                    findings.append(
                        f"{rel}:{lineno}: unknown phase version: {phase} "
                        "(no SKILL.md declares it)"
                    )
            # F3 — the "as of vX.Y.Z" claim must equal the package version
            m = re.search(r"last regenerated from live code as of \*\*(v?\d+\.\d+\.\d+)\*\*", line)
            if m:
                claim = m.group(1).lstrip("v")
                if claim != pkg:
                    findings.append(
                        f"{rel}:{lineno}: package version claim is {claim}, "
                        f"package.json says {pkg}"
                    )
                else:
                    report.append(f"{rel}:{lineno}: {claim} -> package")
            # F4 — current-count claims must equal the measured count
            for m in _COUNT_RE.finditer(line):
                n = int(m.group(1))
                unit = m.group(2).lower()
                actual = skill_count if unit.startswith("skill") else adr_count
                if n != actual:
                    findings.append(
                        f"{rel}:{lineno}: stale count: {m.group(0)} (actual {actual})"
                    )
                else:
                    report.append(f"{rel}:{lineno}: {m.group(0)} -> actual {actual}")
    return findings, report

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="markdown drift checker")
    parser.add_argument("--all", action="store_true", help="scan every root in SCAN_ROOTS")
    parser.add_argument("--versions", action="store_true", help="list version / count claims")
    parser.add_argument("--adr-refs", action="store_true", help="check ADR references")
    parser.add_argument("--guide-names", action="store_true", help="check old guide-* stage names")
    parser.add_argument("paths", nargs="*", help="scan only these files/dirs")
    args = parser.parse_args(argv)

    if not args.all and not args.versions and not args.adr_refs and not args.guide_names and not args.paths:
        parser.error("nothing to do: pass --all / --versions / --adr-refs / paths")

    files = _iter_files(args.paths) if args.paths else _default_files()
    findings: list[str] = []
    if args.versions:
        v_findings, report = version_report(files)
        findings.extend(v_findings)
        for line in report:
            print(line)
    else:
        floor = (MIN_FILES, MIN_LINKS) if not args.paths else (1, 0)
        link_findings, _count = check_links(files, floor=floor)
        findings.extend(link_findings)
    if args.adr_refs:
        findings.extend(check_adr_refs(files))
    if args.guide_names:
        findings.extend(check_guide_names(files))

    for f in findings:
        print(f"❌ {f}")
    if findings:
        print(f"\n{len(findings)} finding(s)")
        return 1
    print(f"✓ markdown drift check passed ({len(files)} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
