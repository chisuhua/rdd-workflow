"""Canonical verifier state paths — single source for the skill's `owns:` block.

Per `consolidate-verifier-state` (openspec/changes/archive/2026-11-14-consolidate-verifier-state/):
`.rddf/state/verifier/` is the **single namespace** for verifier state. Six
paths make up that surface:

  1. per-change loop state            `.rddf/state/verifier/<name>.json`
  2. per-change audit log             `.rddf/state/verifier/<name>.audit.jsonl`
  3. SHA-bound verdict cache          `.rddf/state/verifier/.ac-verdict-*.json`
  4. shared verification audit log     `.rddf/state/verifier/.ac-verification.jsonl`
  5. halted-verification audit log     `.rddf/state/verifier/.ac-verifier-blocked.jsonl`
  6. staged verification context       `.rddf/state/verifier/rdd-verify-context-<name>.json`

This module exists so the **`owns:` block in `skills/rdd-verifier/SKILL.md`** and
the **code that writes those files** are tied to one list:

  - `SKILL.md` must contain `render_owns_block()` **byte for byte**
    (asserted by `tests/unit/test_verifier_owns_block.py` — same repo ⇒ CI can check it);
  - every path the code produces must match one of the patterns.

Why a module and not a comment: the previous arrangement let `SKILL.md` claim
4 paths while the skill actually wrote 6 (two were never declared). A list the
code and the manifest both derive from cannot drift that way.
"""
from __future__ import annotations

import re
from pathlib import Path

# The verifier state namespace directory (under `.rddf/state/`).
VERIFIER_STATE_DIRNAME = "verifier"

# The skill's `owns:` surface — the six paths above, in manifest order.
SKILL_OWNS_PATHS: tuple[str, ...] = (
    ".rddf/state/verifier/<name>.json",
    ".rddf/state/verifier/<name>.audit.jsonl",
    ".rddf/state/verifier/.ac-verdict-*.json",
    ".rddf/state/verifier/.ac-verification.jsonl",
    ".rddf/state/verifier/.ac-verifier-blocked.jsonl",
    ".rddf/state/verifier/rdd-verify-context-<name>.json",
)

# Indentation of the `owns:` list items inside `skills/rdd-verifier/SKILL.md`.
OWNS_ITEM_INDENT = "      "


def owns_block_lines() -> list[str]:
    """The canonical `owns:` block lines (YAML list items, manifest indentation)."""
    return [f'{OWNS_ITEM_INDENT}- "{p}"' for p in SKILL_OWNS_PATHS]


def render_owns_block() -> str:
    """The canonical `owns:` block as one string (for byte-for-byte comparison)."""
    return "\n".join(owns_block_lines())


def pattern_to_regex(pattern: str) -> re.Pattern[str]:
    """Turn an owns pattern into a matcher.

    `<name>` / `<change>` → one path segment; `*` → any characters within a
    segment (never across `/`).
    """
    out: list[str] = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "<":
            end = pattern.index(">", i)
            out.append("[^/]+")
            i = end + 1
            continue
        if ch == "*":
            out.append("[^/]*")
            i += 1
            continue
        out.append(re.escape(ch))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def matches_any_owns(path: str | Path) -> bool:
    """True when `path` (relative to the project root) matches an owns pattern."""
    text = str(path).replace("\\", "/")
    return any(pattern_to_regex(p).match(text) for p in SKILL_OWNS_PATHS)


def verifier_state_dir(project_root: Path) -> Path:
    """The verifier state namespace directory for a project."""
    return Path(project_root) / ".rddf" / "state" / VERIFIER_STATE_DIRNAME
