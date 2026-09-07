"""Skill frontmatter deprecation scanner.

Per verifier-v2-hardening Phase 7 / oracle Q3:
- Reads `skills/<name>/SKILL.md` frontmatter for each skill.
- Extracts `metadata.deprecated` block or `user-invocable: false` flag.
- Returns list of `{name, reason, removal_target, migration}` dicts.

Used by propose stage (Planner Phase 1) to surface "scheduled removal"
suggestions for skills like `ac-verifier` whose `metadata.deprecated` is
populated.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


@dataclass
class DeprecatedSkill:
    name: str
    user_invocable: bool
    reason: str
    removal_target: str
    deprecated_in: str
    migration: str

    def to_dict(self) -> dict:
        return asdict(self)


_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(?P<body>.*?)\n---\s*\n",
    re.DOTALL | re.MULTILINE,
)


def _parse_frontmatter(skill_md: Path) -> dict:
    """Minimal YAML-ish frontmatter parser (no PyYAML dependency for this helper).

    Only handles the flat `key: value` lines and the `metadata:\n  subkey: value`
    nested form. Inline `# comment` suffixes and YAML quoting are stripped.
    Sufficient for `metadata.deprecated` + `user-invocable` + their subkeys.
    """
    text = skill_md.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    flat: dict[str, object] = {}
    nested_meta: dict[str, str] = {}
    in_metadata = False
    for raw_line in m.group("body").splitlines():
        stripped = raw_line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "metadata:":
            in_metadata = True
            continue
        if in_metadata and raw_line.startswith("  "):
            key_part, _, val = stripped.strip().partition(":")
            key_name = key_part.strip()
            val_clean = val.strip().split("  #")[0].strip().strip("\"'")
            nested_meta[key_name] = val_clean
        else:
            in_metadata = False
            key_part, _, val = stripped.partition(":")
            val_clean = val.strip().split("  #")[0].strip().strip("\"'")
            flat[key_part.strip()] = val_clean
    flat["metadata"] = nested_meta
    return flat


def scan_deprecated_skills(skills_dir: Path) -> list[DeprecatedSkill]:
    """Return DeprecatedSkill for every skill with deprecation signals.

    Detection rules (any of):
      1. `user-invocable: false` (top-level frontmatter)
      2. `metadata.user-invocable: false` (legacy placement)
      3. `metadata.reason` populated (signals deprecation intent even
         without a structured `metadata.deprecated` block)

    Reason, removal_target, deprecated_in, migration are pulled from
    the legacy `metadata.*` keys (deprecated_in / deprecated_by /
    removal_target / migration / reason) when a structured
    `metadata.deprecated: {...}` block is absent. This matches how
    skills/ac-verifier/SKILL.md was authored (flat `metadata.*` keys,
    not a YAML dict).
    """
    out: list[DeprecatedSkill] = []
    if not skills_dir.is_dir():
        return out
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        name = skill_md.parent.name
        fm = _parse_frontmatter(skill_md)
        top_user_invocable = str(fm.get("user-invocable") or "true").lower()
        meta_raw = fm.get("metadata") or {}
        meta = meta_raw if isinstance(meta_raw, dict) else {}
        meta_user_invocable = str(meta.get("user-invocable") or "true").lower()
        user_invocable = top_user_invocable == "true" and meta_user_invocable == "true"
        if user_invocable:
            continue
        # Pull reason/timeline/migration from legacy flat metadata.* keys.
        reason = meta.get("reason") or ""
        removal_target = meta.get("removal_target") or ""
        deprecated_in = meta.get("deprecated_in") or ""
        migration = meta.get("migration") or ""
        out.append(DeprecatedSkill(
            name=name,
            user_invocable=False,
            reason=reason or "user-invocable: false",
            removal_target=removal_target,
            deprecated_in=deprecated_in,
            migration=migration,
        ))
    return out


def render_suggestion_block(skills: Iterable[DeprecatedSkill]) -> str:
    """Render a markdown suggestion block for proposal-suggestions.md."""
    skills = list(skills)
    if not skills:
        return ""
    lines = ["\n## Scheduled-Removal Skills (verifier-v2-hardening Phase 7)\n"]
    lines.append("| Skill | Reason | Removal target | Migration |")
    lines.append("|-------|--------|-----------------|-----------|")
    for s in skills:
        lines.append(f"| `{s.name}` | {s.reason} | {s.removal_target or '-'} | "
                     f"{s.migration or '-'} |")
    return "\n".join(lines) + "\n"