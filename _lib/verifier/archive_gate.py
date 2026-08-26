"""Verifier contract enforcement for archive gate.

Per fix-rdd-verifier-lifecycle-dashboard Tasks 11-14:
- Consume iteration.verification.state, archive_ready, verdict_sha
- Resolve canonical cache path via main_repo_root (no shell interpolation)
- Return structured reason code for bash archive_gate_check to act on
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from _lib.verifier.cache import read_verdict_cache, cache_has_failed_ac


def _project_root() -> Path:
    return Path(os.environ.get("RDDF_PROJECT_ROOT")
                or os.environ.get("PROJECT_ROOT")
                or os.getcwd())


def _main_repo_root(cwd: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return cwd
        common = result.stdout.strip()
        common_path = Path(common)
        if common_path.is_absolute():
            return common_path.parent
        return (cwd / common).resolve().parent
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return cwd


def _cache_path(main_root: Path, change_name: str) -> Path:
    return main_root / ".rddf" / "state" / f".ac-verdict-{change_name}.json"


def load_iteration_doc(project_root: Path) -> dict:
    state_file = project_root / ".rddf" / "state" / "iteration.json"
    if not state_file.is_file():
        return {"version": 7, "changes": []}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {"version": 7, "changes": []}


def find_change_verification(project_root: Path, change_name: str) -> Optional[dict]:
    doc = load_iteration_doc(project_root)
    for ch in doc.get("changes", []):
        if ch.get("name") == change_name:
            return ch.get("verification")
    return None


def resolve_branch_tip(cwd: Path, change_name: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--verify", "--quiet",
             f"openspec/{change_name}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def check_archive_readiness(
    project_root: Optional[Path] = None,
    change_name: str = "",
    *,
    force_bypass: bool = False,
    feature_archive_gate: str = "off",
) -> dict:
    """Check whether a change is archive-ready.

    Returns a dict:
        {
          "ready": bool,
          "reason": str,           # empty when ready
          "verification_state": str|None,
          "verdict_sha": str|None,
          "archive_ready": bool,
          "cache_present": bool,
          "cache_failed": bool,
        }
    """
    cwd = project_root or _project_root()
    if feature_archive_gate == "hard" and not force_bypass:
        return {"ready": False, "reason": "feature_archive_gate=hard blocks archive",
                "verification_state": None, "verdict_sha": None,
                "archive_ready": False, "cache_present": False, "cache_failed": False}

    main_root = _main_repo_root(cwd)
    verification = find_change_verification(main_root, change_name)
    if verification is None:
        return {"ready": False, "reason": "verification missing: rdd-verifier not run",
                "verification_state": None, "verdict_sha": None,
                "archive_ready": False, "cache_present": False, "cache_failed": False}

    state = verification.get("state")
    archive_ready = bool(verification.get("archive_ready"))
    verdict_sha = verification.get("verdict_sha")

    if state == "bypassed":
        if not verification.get("bypass_reason"):
            return {"ready": False, "reason": "bypassed without reason",
                    "verification_state": state, "verdict_sha": verdict_sha,
                    "archive_ready": archive_ready, "cache_present": False,
                    "cache_failed": False}
        return {"ready": True, "reason": "",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": True, "cache_present": False, "cache_failed": False}

    if state != "passed":
        return {"ready": False, "reason": f"verification state is {state!r}",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": False, "cache_present": False, "cache_failed": False}

    if not archive_ready:
        return {"ready": False, "reason": "archive_ready=false",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": False, "cache_present": False, "cache_failed": False}

    if not verdict_sha:
        return {"ready": False, "reason": "verdict_sha missing",
                "verification_state": state, "verdict_sha": None,
                "archive_ready": archive_ready, "cache_present": False,
                "cache_failed": False}

    branch_tip = resolve_branch_tip(cwd, change_name)
    if branch_tip is None:
        return {"ready": False, "reason": "openspec/<change> branch missing",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": archive_ready, "cache_present": False,
                "cache_failed": False}
    if branch_tip != verdict_sha:
        return {"ready": False, "reason": "verdict_sha stale (branch moved)",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": archive_ready, "cache_present": False,
                "cache_failed": False}

    cache = read_verdict_cache(main_root, change_name)
    cache_failed = cache is not None and cache_has_failed_ac(main_root, change_name)
    if cache_failed:
        return {"ready": False, "reason": "cache has failed AC",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": archive_ready, "cache_present": cache is not None,
                "cache_failed": True}

    return {"ready": True, "reason": "",
            "verification_state": state, "verdict_sha": verdict_sha,
            "archive_ready": True, "cache_present": cache is not None,
            "cache_failed": False}


def write_structured_cache_fallback(
    project_root: Path,
    change_name: str,
    verdict_doc: dict,
    *,
    implementation_ref: Optional[str] = None,
) -> Path:
    """Persist ac-verifier structured verdict to canonical cache.

    Used by archive_gate_check fallback path. Writes v2 schema with
    ran_by=archive_gate_check.
    """
    from _lib.verifier.cache import verdict_cache
    if isinstance(verdict_doc, dict) and "verdict" in verdict_doc:
        verdict = verdict_doc.get("verdict") or []
        failed = [v.get("ac_id", "?") for v in verdict if v.get("status") == "fail"]
    else:
        verdict = verdict_doc if isinstance(verdict_doc, list) else []
        failed = [v.get("ac_id", "?") for v in verdict if isinstance(v, dict)
                   and v.get("status") == "fail"]

    has_failures = bool(failed)
    state = "failed" if has_failures else "passed"
    codebase_commit = verdict_doc.get("codebase_commit") if isinstance(verdict_doc, dict) else None
    if not codebase_commit:
        codebase_commit = resolve_branch_tip(project_root, change_name) or "unknown"
    return verdict_cache(
        project_root, change_name, codebase_commit, verdict,
        ran_by="archive_gate_check",
        verification_state=state,
        failed_acs=failed,
        implementation_ref=implementation_ref,
    )


def _cli(argv: list) -> int:
    """CLI entrypoint for `python3 -m _lib.verifier.archive_gate check <name>`."""
    import sys
    if len(argv) < 2 or argv[0] != "check":
        print("usage: python3 -m _lib.verifier.archive_gate check <change_name>",
              file=sys.stderr)
        return 2
    change_name = argv[1]
    feature_gate = os.environ.get("FEATURE_ARCHIVE_GATE", "off")
    result = check_archive_readiness(None, change_name,
                                      feature_archive_gate=feature_gate)
    if result["ready"]:
        print("READY")
        return 0
    print(result["reason"] or "not ready")
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(_cli(sys.argv[1:]))
