"""Shared ADR catalog scanner.

Extracted from populate-roadmap-from-arch v1.1 (populate_lib.py::catalog_sources)
so that both the standalone skill and guide-arch Phase 6 (four-mode incremental
update, move-populate-roadmap-into-guide-arch) share one ADR discovery layer.

Public API:
  AdrMeta                                       -> dataclass
  scan_adr_catalog(project_root, adr_dir)       -> dict[str, AdrMeta]

Stdlib only (hashlib / pathlib / dataclasses / re).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ADR_PATTERN = re.compile(r"^ADR-(\d{4})-.*\.md$")


@dataclass
class AdrMeta:
    """One ADR file's catalog metadata."""
    adr_id: str                    # e.g. "ADR-0001"
    file_path: Path                # absolute path to the ADR file
    file_hash: str                 # sha256 hex digest of file content
    title: str                     # from YAML frontmatter ("" if absent)
    status: str                    # from YAML frontmatter ("未知" if absent)
    phase: Optional[str] = None    # from YAML frontmatter (optional)
    category: Optional[str] = None  # from YAML frontmatter (optional)


def _parse_frontmatter(text: str) -> dict:
    """Minimal YAML frontmatter parser for flat key: value fields."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out = {}
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def scan_adr_catalog(
    project_root: Path,
    adr_dir: str = "docs/adr",
    adr_pattern: Optional[str] = None,
) -> dict[str, AdrMeta]:
    """Scan {project_root}/{adr_dir}/ADR-*.md, return {adr_id: AdrMeta}.

    Files not matching the ADR pattern (e.g. README.md) are skipped.
    A missing directory yields an empty dict.

    Args:
        project_root: Project root path.
        adr_dir: ADR directory relative to project_root (default "docs/adr").
        adr_pattern: Optional regex pattern overriding the default 4-digit
            pattern (^ADR-(\\d{4})-.*\\.md$). Useful for projects with shorter
            or longer ADR numbering (e.g. ChipForge uses 3-digit: ^ADR-(\\d{3})).
    """
    root = Path(project_root) / adr_dir
    out: dict[str, AdrMeta] = {}
    if not root.is_dir():
        return out
    pattern = re.compile(adr_pattern) if adr_pattern else ADR_PATTERN
    for f in sorted(root.glob("ADR-*.md")):
        m = pattern.match(f.name)
        if not m:
            continue
        adr_id = f"ADR-{m.group(1)}"
        text = f.read_text(encoding="utf-8", errors="replace")
        meta = _parse_frontmatter(text)
        out[adr_id] = AdrMeta(
            adr_id=adr_id,
            file_path=f,
            file_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            title=meta.get("title", ""),
            status=meta.get("status", "未知"),
            phase=meta.get("phase") or None,
            category=meta.get("category") or None,
        )
    return out
