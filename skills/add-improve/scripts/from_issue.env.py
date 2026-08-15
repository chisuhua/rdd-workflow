#!/usr/bin/env python3
"""Env-var validation for add-improve --from-issue mode (Oracle C1 anti-injection).

Usage:
    python3 from_issue.env.py validate    # validates env-vars, exits 0/1
    python3 from_issue.env.py describe    # prints validated values as JSON

Exit codes:
    0 — valid
    1 — validation error (writes to stderr)

Validates:
    - ADD_IMPROVE_FROM_ISSUE (required, positive integer)
    - ADD_IMPROVE_GH_REPO (required, format: owner/repo)
    - ADD_IMPROVE_ISSUE_TITLE (required, <= 200 chars, no shell metachars)
    - ADD_IMPROVE_ISSUE_BODY (optional, <= 4000 chars, no shell metachars if present)

Disallowed characters in title/body (anti-injection):
    $ ` " ' ; | & \\n \\r  ( ) { } < >  ! ~ #
"""
import json
import os
import re
import sys
from typing import Optional


_DISALLOWED_RE = re.compile(r'[$`"\';|&\n\r(){}<>!~#]')
_GH_REPO_RE = re.compile(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$")
_ISSUE_NUM_RE = re.compile(r"^[1-9][0-9]{0,9}$")


def _check_text(value: str, name: str, max_len: int) -> Optional[str]:
    if not value:
        return f"{name} is empty"
    if _DISALLOWED_RE.search(value):
        return f"{name} contains disallowed shell metacharacters: {value!r}"
    if len(value) > max_len:
        return f"{name} exceeds {max_len} chars (got {len(value)})"
    return None


def validate_env() -> dict:
    from_issue = os.environ.get("ADD_IMPROVE_FROM_ISSUE", "").strip()
    gh_repo = os.environ.get("ADD_IMPROVE_GH_REPO", "").strip()
    title = os.environ.get("ADD_IMPROVE_ISSUE_TITLE", "").strip()
    body = os.environ.get("ADD_IMPROVE_ISSUE_BODY", "").strip()

    errors = []

    if not _ISSUE_NUM_RE.match(from_issue):
        errors.append(
            f"ADD_IMPROVE_FROM_ISSUE must be a positive integer (got {from_issue!r})"
        )

    if not _GH_REPO_RE.match(gh_repo):
        errors.append(
            f"ADD_IMPROVE_GH_REPO must match owner/repo pattern (got {gh_repo!r})"
        )

    err = _check_text(title, "ADD_IMPROVE_ISSUE_TITLE", 200)
    if err:
        errors.append(err)

    if body:
        err = _check_text(body, "ADD_IMPROVE_ISSUE_BODY", 4000)
        if err:
            errors.append(err)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    return {
        "issue_num": int(from_issue),
        "gh_repo": gh_repo,
        "title": title,
        "body": body,
    }


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"validate", "describe"}:
        print(
            "Usage: from_issue.env.py {validate|describe}",
            file=sys.stderr,
        )
        return 1

    values = validate_env()

    if sys.argv[1] == "describe":
        print(json.dumps(values, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())