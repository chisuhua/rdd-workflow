"""Hub contract metadata fetcher (filename + x-owners).

Used by detect_cross_repo_impact.py to scan Hub contracts and extract
ownership information for stakeholder auto-suggestion.

Contract files in Hub `contracts/` MAY carry an OpenAPI extension field
`x-owners:` listing GitHub `org/repo` strings. Missing `x-owners` is
gracefully defaulted to empty list.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from typing import List, Optional


def list_hub_contracts(hub_repo: str) -> List[dict]:
    """List all files under `contracts/` in Hub repo.

    Returns list of dicts with `name`, `path`, `sha`. Files at root or
    other directories are ignored. Network/permission failures return [].
    """
    if "/" not in hub_repo:
        print(f"ERROR: hub_repo must be <owner>/<repo>: {hub_repo}", file=sys.stderr)
        return []

    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{hub_repo}/contents/contracts"],
            capture_output=True, text=True, check=True, timeout=20,
        )
        data = json.loads(result.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return []

    if not isinstance(data, list):
        return []

    contracts = []
    for entry in data:
        if isinstance(entry, dict) and entry.get("type") == "file":
            name = entry.get("name", "")
            path = entry.get("path", "")
            if not name or not path:
                continue
            contracts.append({
                "name": name,
                "path": path,
                "sha": entry.get("sha", ""),
            })
    return contracts


_OWNERS_RE = re.compile(
    r"x-owners\s*:\s*\[([^\]]+)\]",
    re.IGNORECASE | re.MULTILINE,
)


def parse_x_owners(yaml_text: str) -> List[str]:
    """Parse `x-owners: [org/repo-a, org/repo-b]` from contract YAML/JSON.

    Supports YAML list syntax (inline) and JSON array string. Returns [] if
    `x-owners` is missing or malformed. Owner strings are stripped of
    whitespace; invalid `org/repo` formats are filtered out.
    """
    if not yaml_text:
        return []

    m = _OWNERS_RE.search(yaml_text)
    if not m:
        return []

    raw = m.group(1)
    items = [s.strip().strip('"').strip("'") for s in raw.split(",")]
    items = [s for s in items if s and _ORG_REPO_RE.match(s)]
    return items


_ORG_REPO_RE = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")


def fetch_contract_content(hub_repo: str, path: str, sha: str) -> Optional[str]:
    """Fetch contract file content from Hub. Returns decoded text or None."""
    if "/" not in hub_repo:
        return None
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{hub_repo}/contents/{path}", "-H", f"If-None-Match: {sha}"],
            capture_output=True, text=True, check=True, timeout=20,
        )
        data = json.loads(result.stdout)
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, KeyError):
        return None


def extract_match_keywords(contract_name: str) -> List[str]:
    """Extract searchable keywords from a contract filename.

    Example: 'auth-v2.yaml' -> ['auth', 'v2', 'auth-v2', 'auth-v2.yaml']
    """
    name = contract_name
    for ext in (".yaml", ".yml", ".json"):
        if name.endswith(ext):
            name = name[: -len(ext)]
            break

    parts = re.split(r"[-_.]", name)
    keywords = set()
    keywords.add(name)
    keywords.add(name + ".yaml")
    keywords.add(name + ".json")
    for p in parts:
        if p:
            keywords.add(p)
    return sorted(keywords)