#!/usr/bin/env python3
"""Env-var validation for add-improve --from-roadmap mode (Oracle C1 anti-injection).

Usage:
    python3 from_roadmap.env.py validate    # validates env-vars, exits 0/1
    python3 from_roadmap.env.py describe    # prints validated values as JSON

Exit codes:
    0 — valid
    1 — validation error (writes to stderr)

Validates:
    - ADD_IMPROVE_FROM_ROADMAP (required, format: phase_id/category_id)
    - ADD_IMPROVE_THEME (required when FROM_ROADMAP set, no shell metachars)
    - BRAINSTORM_RATIONALE_DRAFT (optional, no shell metachars)
    - ADD_IMPROVE_NAME_PREFIX / ADD_IMPROVE_NAME_SUFFIX (optional, kebab-case)
    - ADD_IMPROVE_AUTO_NAME (optional, yes/true/1)
    - ADD_IMPROVE_MULTI (optional, positive integer)

Disallowed characters in theme/rationale (anti-injection):
    $ ` " ' ; | & \\n \\r  ( ) { } < >  ! ~ #
"""
import json
import os
import re
import sys
from typing import Optional


_DISALLOWED_RE = re.compile(r'[$`"\';|&\n\r(){}<>!~#]')
_FROM_ROADMAP_RE = re.compile(r"^[a-z0-9-]+/[a-z0-9-]+$")
_KEBAB_RE = re.compile(r"^[a-z0-9-]+$")
_AUTO_NAME_TRUE = {"yes", "true", "1"}
_MULTI_RE = re.compile(r"^[1-9][0-9]*$")


def _check_text(value: str, name: str) -> Optional[str]:
    if not value:
        return f"{name} is empty"
    if _DISALLOWED_RE.search(value):
        return f"{name} contains disallowed shell metacharacters: {value!r}"
    if len(value) > 200:
        return f"{name} exceeds 200 chars (got {len(value)})"
    return None


def validate_env() -> dict:
    from_roadmap = os.environ.get("ADD_IMPROVE_FROM_ROADMAP", "").strip()
    theme = os.environ.get("ADD_IMPROVE_THEME", "").strip()
    rationale = os.environ.get("BRAINSTORM_RATIONALE_DRAFT", "").strip()
    name_prefix = os.environ.get("ADD_IMPROVE_NAME_PREFIX", "").strip()
    name_suffix = os.environ.get("ADD_IMPROVE_NAME_SUFFIX", "").strip()
    auto_name = os.environ.get("ADD_IMPROVE_AUTO_NAME", "").strip()
    multi = os.environ.get("ADD_IMPROVE_MULTI", "").strip()

    errors = []

    if from_roadmap:
        if not _FROM_ROADMAP_RE.match(from_roadmap):
            errors.append(
                f"ADD_IMPROVE_FROM_ROADMAP must match phase_id/category_id "
                f"(got {from_roadmap!r})"
            )
        err = _check_text(theme, "ADD_IMPROVE_THEME")
        if err:
            errors.append(err)
        if rationale:
            err = _check_text(rationale, "BRAINSTORM_RATIONALE_DRAFT")
            if err:
                errors.append(err)

    for name, value in (
        ("ADD_IMPROVE_NAME_PREFIX", name_prefix),
        ("ADD_IMPROVE_NAME_SUFFIX", name_suffix),
    ):
        if value and not _KEBAB_RE.match(value):
            errors.append(
                f"{name} must be kebab-case (lowercase letters, digits, hyphens only; "
                f"got {value!r})"
            )

    if auto_name and auto_name.lower() not in _AUTO_NAME_TRUE:
        errors.append(
            f"ADD_IMPROVE_AUTO_NAME must be yes/true/1 (got {auto_name!r})"
        )

    if multi and not _MULTI_RE.match(multi):
        errors.append(
            f"ADD_IMPROVE_MULTI must be a positive integer (got {multi!r})"
        )

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    return {
        "from_roadmap": from_roadmap,
        "theme": theme,
        "rationale": rationale,
        "name_prefix": name_prefix,
        "name_suffix": name_suffix,
        "auto_name": auto_name,
        "multi": multi,
    }


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"validate", "describe"}:
        print(
            "Usage: from_roadmap.env.py {validate|describe}",
            file=sys.stderr,
        )
        return 1

    values = validate_env()

    if sys.argv[1] == "describe":
        print(json.dumps(values, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())