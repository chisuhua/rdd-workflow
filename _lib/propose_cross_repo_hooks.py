"""Propose-phase auto cross-repo detection.

Triggered from skills.propose.scripts.propose_change::create_skeleton_change.
Scans the change's specs/ tree for capability names that look cross-repo
(`api-*` / `cross-*` / `hub-*` prefix), injects a Hub RFC placeholder into
proposal.md, and writes a cache entry to .rddf/state/.cross-repo-deps-cache.json.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional


CROSS_REPO_PREFIXES = ("api-", "cross-", "hub-")
CACHE_PATH_DEFAULT = ".rddf/state/.cross-repo-deps-cache.json"


def _is_cross_repo(cap_name: str) -> bool:
    return any(cap_name.startswith(p) for p in CROSS_REPO_PREFIXES)


def detect_hub_scope(change_dir) -> list:
    """Return capability names in `change_dir/specs/` matching cross-repo prefixes."""
    specs = Path(change_dir) / "specs"
    if not specs.is_dir():
        return []
    out: list = []
    for cap_dir in sorted(specs.iterdir()):
        if cap_dir.is_dir() and _is_cross_repo(cap_dir.name):
            out.append(cap_dir.name)
    return out


def inject_hub_rfc_placeholder(proposal_md: str, hub_scopes) -> str:
    """If `hub_scopes` non-empty, append a Hub RFC placeholder section.

    Per proposal MUST NOT, this only generates text — no GitHub API calls.
    The Hub issue is filed after approval by change #7.
    """
    if not hub_scopes:
        return proposal_md
    placeholder = (
        "\n\n## Hub RFC Placeholder\n\n"
        f"This change touches {len(hub_scopes)} Hub-scoped capability(ies):\n"
        + "\n".join(f"- `{c}`" for c in hub_scopes)
        + "\n\n"
        "Per ADR-0031, this requires a Hub approval before archive.\n"
        "Hub issue link: _to be filed after design approval (see #7)_\n"
    )
    return proposal_md + placeholder


def update_cross_repo_cache(
    change_name: str,
    scopes,
    cache_path: Optional[Path] = None,
) -> list:
    """Read/write the cross-repo cache.

    Returns cached scopes for `change_name` if present (cache hit —
    skip re-scan), else writes `scopes` and returns them.
    """
    cache_file = Path(cache_path) if cache_path else Path(CACHE_PATH_DEFAULT)
    cache: dict = {}
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}

    if change_name in cache and cache[change_name]:
        return list(cache[change_name])

    cache[change_name] = list(scopes)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    return list(scopes)