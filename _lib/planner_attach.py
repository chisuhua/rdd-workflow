"""Validated, single-file proposal attach.

Per ADR-0038 (Stage 2.5 P0-3): this is the only writer (besides
`rddf feedback add`) that touches `.rddf/improvements/*.md`. Operates on
exactly one file, preserves unrelated frontmatter, validates project_id
and phase against the canonical roadmap sources, and is idempotent for
identical mappings.

project_id: must match a Theme value from `.rddf/roadmap.md
            ## Phase Skeleton`.
phase:      must match a Phase value from `## Phase Skeleton` or a
            phase fragment id (`.rddf/roadmap/phases/*.md`
            frontmatter `id`).
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from _lib.core.atomic_write import atomic_write_text
from _lib.core.lock import FileLock

__all__ = ["AttachError", "attach_proposal", "list_valid_projects", "list_valid_phases"]


class AttachError(Exception):
    """Attach validation failure (no write performed)."""


_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _as_list(value):
    """Coerce a frontmatter scalar or list to a list (handles scalar 主题)."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _roadmap_path(project_root: Path) -> Path:
    return project_root / ".rddf" / "roadmap.md"


def _improvements_root(project_root: Path) -> Path:
    return (project_root / ".rddf" / "improvements").resolve()


def _improvement_path(project_root: Path, proposal: str) -> Path:
    if not _SAFE_NAME.match(proposal):
        raise AttachError(f"invalid proposal name: {proposal!r}")
    target = project_root / ".rddf" / "improvements" / f"{proposal}.md"
    target_resolved = target.resolve()
    if target_resolved.parent != _improvements_root(project_root):
        raise AttachError(f"path traversal rejected for {proposal!r}")
    if not target.exists():
        raise AttachError(f"improvement file not found: {target}")
    return target


def _parse_skeleton(roadmap_text: str) -> tuple[set[str], set[str]]:
    themes: set[str] = set()
    phases: set[str] = set()
    in_section = False
    for line in roadmap_text.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == "## Phase Skeleton"
            continue
        if not in_section or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0].startswith("---") or cells[0].lower() == "phase":
            continue
        phases.add(cells[0])
        themes.add(cells[1])
    return themes, phases


def _phase_fragment_ids(project_root: Path) -> set[str]:
    ids: set[str] = set()
    phases_dir = project_root / ".rddf" / "roadmap" / "phases"
    if not phases_dir.is_dir():
        return ids
    for f in phases_dir.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        try:
            end = text.index("\n---", 3)
            fm = yaml.safe_load(text[3:end]) or {}
        except (ValueError, yaml.YAMLError):
            continue
        pid = fm.get("id")
        if isinstance(pid, str) and pid:
            ids.add(pid)
    return ids


def _fragment_themes(project_root: Path) -> set[str]:
    """Return set of `主题` field values from `.rddf/roadmap/phases/*.md` frontmatter.

    The fragment 主题 field is a backup source for project_id validation
    when the Theme column in Phase Skeleton does not include a candidate
    proposal's match (per Stage 2.5 P0-3 plan contract).
    """
    themes: set[str] = set()
    phases_dir = project_root / ".rddf" / "roadmap" / "phases"
    if not phases_dir.is_dir():
        return themes
    for f in phases_dir.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        try:
            end = text.index("\n---", 3)
            fm = yaml.safe_load(text[3:end]) or {}
        except (ValueError, yaml.YAMLError):
            continue
        for raw in _as_list(fm.get("主题")):
            if isinstance(raw, str) and raw:
                themes.add(raw)
    return themes


def list_valid_projects(project_root: Path) -> set[str]:
    """Return set of valid project_ids (Phase Skeleton Theme + fragment 主题)."""
    rm = _roadmap_path(project_root)
    projects: set[str] = set()
    if rm.exists():
        themes, _ = _parse_skeleton(rm.read_text(encoding="utf-8"))
        projects |= {t for t in themes if t and t != "Theme"}
    projects |= _fragment_themes(project_root)
    return projects


def list_valid_phases(project_root: Path) -> set[str]:
    """Return set of valid phases (skeleton Phase column + fragment ids)."""
    rm = _roadmap_path(project_root)
    phases: set[str] = set()
    if rm.exists():
        _, skel_phases = _parse_skeleton(rm.read_text(encoding="utf-8"))
        phases |= {p for p in skel_phases if p and p.lower() != "phase"}
    phases |= _phase_fragment_ids(project_root)
    return phases


def _parse_frontmatter_block(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise AttachError("missing frontmatter delimiters")
    try:
        end = text.index("\n---", 3)
    except ValueError:
        raise AttachError("malformed frontmatter: no closing ---")
    fm_inner = text[3:end].lstrip("\n")
    try:
        fm = yaml.safe_load(fm_inner) or {}
        if not isinstance(fm, dict):
            raise AttachError("frontmatter is not a mapping")
    except yaml.YAMLError as exc:
        raise AttachError(f"YAML parse error: {exc}")
    body = text[end + 4:].lstrip("\n")
    return fm, body


def _serialize_frontmatter(fm: dict) -> str:
    yaml_text = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{yaml_text}\n---\n"


def attach_proposal(
    *, project_root: Path, proposal: str, project_id: str, phase: str,
    theme: str | None = None, overwrite: bool = False,
) -> Path:
    """Validate and update one improvement's `roadmap_ref`.

    Idempotent for identical {project_id, phase} (theme mismatch on the
    second call is treated as a no-op when existing has theme and new
    call omits theme; explicit theme replacement requires overwrite).
    Refuses to mutate an existing divergent mapping unless
    `overwrite=True`.

    Returns the absolute path to the updated file on success.
    Raises AttachError on validation failure (no write performed).
    """
    project_root = Path(project_root).resolve()
    target = _improvement_path(project_root, proposal)
    valid_projects = list_valid_projects(project_root)
    valid_phases = list_valid_phases(project_root)
    if project_id not in valid_projects:
        raise AttachError(
            f"project_id not in roadmap: {project_id!r}; valid: {sorted(valid_projects)}"
        )
    if phase not in valid_phases:
        raise AttachError(
            f"phase not in roadmap: {phase!r}; valid: {sorted(valid_phases)}"
        )

    new_ref = {"project_id": project_id, "phase": phase}
    if theme is not None:
        new_ref["theme"] = theme

    lock_path = target.with_suffix(target.suffix + ".lock")
    with FileLock(str(lock_path), timeout=10.0):
        text = target.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter_block(text)
        existing = fm.get("roadmap_ref")
        if isinstance(existing, dict):
            existing_normalized = {k: v for k, v in existing.items() if k != "theme"}
            new_normalized = {k: v for k, v in new_ref.items() if k != "theme"}
            if existing_normalized == new_normalized:
                return target
            if not overwrite:
                raise AttachError(
                    f"existing roadmap_ref differs: {existing!r}; pass --overwrite to replace"
                )
        fm["roadmap_ref"] = new_ref
        new_text = _serialize_frontmatter(fm) + "\n" + body
        atomic_write_text(target, new_text)
    return target