"""SHA-fingerprint verdict cache for rdd-verifier (v2 schema).

Per fix-rdd-verifier-lifecycle-dashboard Task 3 + ADR-0034 §7.2:
- Avoids double LLM calls when archive_gate_check runs after rdd-verifier
- v2 schema adds verification_state, failed_acs, schema_version, implementation_ref, source
- Backward compat: v1 entries are read but not upgraded

Cache file: `.rddf/state/verifier/.ac-verdict-<change>.json` (gitignored).

Per consolidate-verifier-state: `.rddf/state/verifier/` is the single namespace
for verifier state. `verdict_cache_path()` below is the ONLY place that spells
the cache path; every other module calls it.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCHEMA_VERSION_V1 = 1
SCHEMA_VERSION_V2 = 2
_SCHEMA_VERSION = SCHEMA_VERSION_V2

# Verifier state namespace (per consolidate-verifier-state / ADR-0034 amendment).
VERIFIER_STATE_DIRNAME = "verifier"


def verdict_cache_path(root: Path, change_name: str) -> Path:
    """Canonical verdict cache path — the single definition point.

    `root` is the caller's project root. Callers that need the *main* repository
    root (archive gate, worktree mode) MUST pass their own root: this function
    resolves no repository root of its own.
    """
    return (Path(root) / ".rddf" / "state" / VERIFIER_STATE_DIRNAME
            / f".ac-verdict-{change_name}.json")


def legacy_verdict_cache_path(root: Path, change_name: str) -> Path:
    """Pre-consolidation cache path (`.rddf/state/.ac-verdict-<change>.json`)."""
    return Path(root) / ".rddf" / "state" / f".ac-verdict-{change_name}.json"


def _cache_path(project_root: Path, change_name: str) -> Path:
    # Kept for backward compatibility (tests import this name); the path
    # expression itself now lives in verdict_cache_path().
    return verdict_cache_path(project_root, change_name)


def audit_log_path(root: Path) -> Path:
    """Canonical shared verification audit log path."""
    return (Path(root) / ".rddf" / "state" / VERIFIER_STATE_DIRNAME
            / ".ac-verification.jsonl")


def blocked_audit_log_path(root: Path) -> Path:
    """Canonical halted-verification audit log path."""
    return (Path(root) / ".rddf" / "state" / VERIFIER_STATE_DIRNAME
            / ".ac-verifier-blocked.jsonl")


def verify_context_path(root: Path, change_name: str) -> Path:
    """Canonical staged verification context path."""
    return (Path(root) / ".rddf" / "state" / VERIFIER_STATE_DIRNAME
            / f"rdd-verify-context-{change_name}.json")


def cache_key(
    change_name: str,
    project_root: Path,
    *,
    provider: str = "llm",
    hook_path: Optional[Path] = None,
) -> str:
    """Compute SHA256 content-derived cache key for a verification verdict.

    Per complete-project-yaml-config-gaps M2 Task 2.4 + spec.md
    'verifier-cache-hook-key' requirement: keys differ across providers
    to prevent cross-provider cache poisoning (e.g. LLM cached verdict
    must not be reused when user switches verification.provider: hook).

    Args:
        change_name: OpenSpec change name.
        project_root: Absolute project root path.
        provider: Verification provider ('llm' or 'hook'). Defaults to 'llm'.
        hook_path: Required when provider='hook' to scope cache by command.

    Returns:
        SHA256 hex digest (64 chars) of canonical JSON payload.
    """
    payload = {
        "change": change_name,
        "root": str(Path(project_root).resolve()),
        "provider": provider,
    }
    if provider == "hook":
        resolved = str(Path(hook_path).resolve()) if hook_path else ""
        payload["hook"] = resolved
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def verdict_cache(
    project_root: Path,
    change_name: str,
    codebase_commit: str,
    verdict: list,
    ran_by: str,
    *,
    verification_state: Optional[str] = None,
    failed_acs: Optional[list] = None,
    implementation_ref: Optional[str] = None,
) -> Path:
    """Write verdict cache v2 for a change.

    Args:
        project_root: Path to project root (must contain .rddf/state/).
        change_name: OpenSpec change name.
        codebase_commit: git SHA at the time of verification.
        verdict: list of verdict items from ac-verifier.
        ran_by: "rdd-verifier" or "archive_gate_check".
        verification_state: optional state string.
        failed_acs: optional list of failed AC IDs.
        implementation_ref: optional implementation branch reference.

    Returns:
        Path to the written cache file.
    """
    path = _cache_path(Path(project_root), change_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = {
        "schema_version": _SCHEMA_VERSION,
        "version": _SCHEMA_VERSION,
        "change": change_name,
        "codebase_commit": codebase_commit,
        "verdict": verdict,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "ran_by": ran_by,
        "source": ran_by,
        "verification_state": verification_state,
        "failed_acs": failed_acs or [],
        "implementation_ref": implementation_ref,
    }
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return path


def read_verdict_cache(project_root: Path, change_name: str) -> Optional[dict]:
    """Read verdict cache. Returns None if missing or corrupt.

    verifier-v2-hardening (oracle risk #5): returns None when schema_version
    is missing, == 1 (ac-verifier era, deprecated by ADR-0034, superseded
    by ADR-0045), or unknown. This is fail-closed — readers must treat the
    cache as unusable and re-run `rddf rdd-verify` to populate a v2 cache.
    """
    path = _cache_path(Path(project_root), change_name)
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    sv = doc.get("schema_version")
    if sv != _SCHEMA_VERSION:
        # Fail closed: unknown / legacy / missing schema_version.
        return None
    return doc


def is_cache_fresh(project_root: Path, change_name: str, current_commit: str) -> bool:
    """Check if cached verdict matches current codebase commit.

    Returns False if cache is missing, corrupt, or stale.
    """
    cached = read_verdict_cache(project_root, change_name)
    if cached is None:
        return False
    return cached.get("codebase_commit") == current_commit


def cache_has_failed_ac(project_root: Path, change_name: str) -> bool:
    """True if cached verdict contains a failing AC."""
    cached = read_verdict_cache(project_root, change_name)
    if cached is None:
        return False
    failed = cached.get("failed_acs") or []
    if failed:
        return True
    for v in cached.get("verdict", []) or []:
        if v.get("status") == "fail":
            return True
    return False


# ── One-shot migration (per consolidate-verifier-state) ─────────────────────
# Pre-consolidation, four kinds of verifier state lived directly under
# `.rddf/state/`. They now live under `.rddf/state/verifier/`. The migration is
# explicit (not a dual-path read fallback) so that exactly ONE path is in play
# afterwards — a dual-path read would let the bash archive gate and the python
# reader disagree about whether a cache exists.
_LEGACY_EXACT_NAMES = (
    ".ac-verification.jsonl",
    ".ac-verifier-blocked.jsonl",
)
_LEGACY_GLOBS = (
    ".ac-verdict-*.json",
    "rdd-verify-context-*.json",
)


def migrate_legacy_state(project_root: Path) -> list[tuple[str, str]]:
    """Move pre-consolidation verifier state files into `.rddf/state/verifier/`.

    Returns a list of `(action, filename)` tuples where action is one of
    `moved` / `skipped` / `failed`.

    Conservative rules (mirroring the legacy `.verifier-loop.json` migration):
      - an existing destination is never overwritten (`skipped`);
      - each file is handled independently — one failure never aborts the rest
        and never raises (`failed`);
      - missing files are not reported.
    """
    state_dir = Path(project_root) / ".rddf" / "state"
    target_dir = state_dir / VERIFIER_STATE_DIRNAME
    if not state_dir.is_dir():
        return []

    candidates: list[Path] = []
    for name in _LEGACY_EXACT_NAMES:
        candidates.append(state_dir / name)
    for pattern in _LEGACY_GLOBS:
        candidates.extend(sorted(state_dir.glob(pattern)))

    results: list[tuple[str, str]] = []
    for src in candidates:
        if not src.is_file():
            continue
        dest = target_dir / src.name
        if dest.exists():
            results.append(("skipped", src.name))
            continue
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            results.append(("moved", src.name))
        except OSError:
            results.append(("failed", src.name))
    return results
