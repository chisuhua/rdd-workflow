"""Verifier contract enforcement for archive gate.

Root + anchor contract (fix-verifier-gate-cache-root)
-----------------------------------------------------
**Two roots, one job each** — the previous implementation mixed them up, so
the bash gate and this module looked for the same cache in different places:

  **gate root** — the caller's root (the ``tasks_root`` handed to
  ``archive_gate_check``). Holds the change's ARTIFACTS (``tasks.md``,
  ``proposal.md``) and, per the CONTRACT in
  ``skills/rdd-builder/scripts/phase3_archive.sh``, the verdict cache.

  **state root** — the canonical project root, resolved with the
  submodule-aware ``resolve_project_root`` (ADR-0033). Holds the project-wide
  REGISTRY (``.rddf/state/iteration.json``) and the batch verifier's own
  state. ``.rddf/state/`` is gitignored, so a linked worktree never carries
  it — the registry is only ever in the main repository.

**One anchor, root-independent** — the implementation branch tip
(``openspec/<change>``). The same SHA is visible from the main repository and
from every linked worktree, so a verdict cache stamped with it stays fresh no
matter which root the reader picks it up from. This is exactly what the write
side records (``_lib/verifier/branch.py::resolve_implementation_commit``).
The previous bash gate compared against ``HEAD``, which in the
``openspec_tracked=false`` path had just been switched to the default branch
— so a perfectly good cache was reported as stale.

**Cache lookup** — the gate reads the verdict cache from the gate root and
falls back to the state root (that is where the batch CLI ``rddf rdd-verify``
writes it); whichever side it used is reported. It never reads two *paths*
for the same root: a dual-path read would let the bash gate and this module
disagree about whether a cache exists (see ``_lib/verifier/cache.py`` §
one-shot migration).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from _lib.verifier.cache import (
    read_verdict_cache, cache_has_failed_ac, verdict_cache_path,
)


def _caller_root() -> Path:
    """The root the caller handed us (the gate root).

    ``RDDF_PROJECT_ROOT`` is what ``verifier_contract_check`` exports; it is
    the gate root (= ``tasks_root``), NOT a repository root we derive.
    """
    env = os.environ.get("RDDF_PROJECT_ROOT") or os.environ.get("PROJECT_ROOT")
    if env:
        return Path(env)
    return Path(os.getcwd())


def _state_root(gate_root: Path) -> Path:
    """Canonical project root for `gate_root` (submodule-aware, ADR-0033).

    Replaces the previous hand-rolled ``--git-common-dir`` derivation, which
    pointed at the superproject's ``.git/modules/<n>`` inside a submodule.
    """
    try:
        from _lib.cli import resolve_project_root
        return Path(resolve_project_root(str(gate_root)))
    except Exception:  # noqa: BLE001 - resolution must never break the gate
        return Path(gate_root)


def _registry_root(gate_root: Path, state_root: Path) -> Path:
    """Root that holds ``.rddf/state/iteration.json``.

    ``.rddf/state/`` is gitignored, so a linked worktree never carries the
    registry: it lives in the canonical state root. When the gate root does
    hold one (lightweight mode, ``openspec_tracked=false``, or a test
    fixture), the gate root wins — it is the project the caller is archiving.
    """
    if gate_root == state_root:
        return gate_root
    if (gate_root / ".rddf" / "state" / "iteration.json").is_file():
        return gate_root
    return state_root


def _cache_path(root: Path, change_name: str) -> Path:
    """Cache path for the archive gate — the root is supplied, never derived.

    The path EXPRESSION lives in `cache.verdict_cache_path` (single definition
    point, asserted by tests/unit/test_verifier_state_consolidation.py); this
    wrapper only exists so the archive gate spells the root explicitly. That
    is the whole point of fix-verifier-gate-cache-root: the caller decides
    between the gate root and the canonical state root.
    """
    return verdict_cache_path(root, change_name)


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
    """Implementation branch tip — the freshness anchor.

    Root-independent: the ref lives in the shared repository, so the main
    repo and every linked worktree resolve the same SHA.
    """
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


def _resolve_anchor(gate_root: Path, state_root: Path, change_name: str) -> Optional[str]:
    """Resolve the freshness anchor (implementation branch tip).

    The ref lives in the shared repository, so both roots answer the same.
    The gate root is tried first (it is the root the bash segment anchors on);
    the state root is the fallback for the case where the gate root is not a
    git working tree at all.
    """
    for root in _cache_roots(gate_root, state_root):
        tip = resolve_branch_tip(root, change_name)
        if tip is not None:
            return tip
    return None


def find_verdict_cache(
    gate_root: Path,
    state_root: Path,
    change_name: str,
) -> tuple[Optional[dict], Optional[Path]]:
    """Locate the verdict cache; return ``(cache_doc, root_it_was_found_in)``.

    The gate root wins (that is the CONTRACT root); the canonical state root
    is the fallback (that is where the batch CLI writes). ``(None, None)``
    when neither side has a usable cache.
    """
    for root in _cache_roots(gate_root, state_root):
        cache = read_verdict_cache(root, change_name)
        if cache is not None:
            return cache, root
    return None, None


def _cache_roots(gate_root: Path, state_root: Path) -> list[Path]:
    """Candidate roots, gate root first, de-duplicated."""
    roots: list[Path] = []
    for root in (gate_root, state_root):
        if root not in roots:
            roots.append(root)
    return roots


def check_archive_readiness(
    project_root: Optional[Path] = None,
    change_name: str = "",
    *,
    force_bypass: bool = False,
    feature_archive_gate: str = "off",
    state_root: Optional[Path] = None,
) -> dict:
    """Check whether a change is archive-ready.

    Args:
        project_root: the gate root (the caller's root). Defaults to
            ``RDDF_PROJECT_ROOT`` / ``PROJECT_ROOT`` / cwd.
        change_name: the OpenSpec change name.
        force_bypass: reserved for callers that already bypassed the gate.
        feature_archive_gate: ``"hard"`` blocks unconditionally.
        state_root: override for the canonical state root (tests).

    Returns a dict:
        {
          "ready": bool,
          "reason": str,           # empty when ready
          "verification_state": str|None,
          "verdict_sha": str|None,
          "archive_ready": bool,
          "cache_present": bool,
          "cache_failed": bool,
          "cache_root": str|None,  # which root the cache was read from
        }
    """
    gate_root = Path(project_root) if project_root else _caller_root()
    if feature_archive_gate == "hard" and not force_bypass:
        return {"ready": False, "reason": "feature_archive_gate=hard blocks archive",
                "verification_state": None, "verdict_sha": None,
                "archive_ready": False, "cache_present": False, "cache_failed": False,
                "cache_root": None}

    resolved_state_root = Path(state_root) if state_root else _state_root(gate_root)
    registry_root = _registry_root(gate_root, resolved_state_root)

    verification = find_change_verification(registry_root, change_name)
    if verification is None:
        return {"ready": False, "reason": "verification missing: rdd-verifier not run",
                "verification_state": None, "verdict_sha": None,
                "archive_ready": False, "cache_present": False, "cache_failed": False,
                "cache_root": None}

    state = verification.get("state")
    archive_ready = bool(verification.get("archive_ready"))
    verdict_sha = verification.get("verdict_sha")

    if state == "bypassed":
        if not verification.get("bypass_reason"):
            return {"ready": False, "reason": "bypassed without reason",
                    "verification_state": state, "verdict_sha": verdict_sha,
                    "archive_ready": archive_ready, "cache_present": False,
                    "cache_failed": False, "cache_root": None}
        return {"ready": True, "reason": "",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": True, "cache_present": False, "cache_failed": False,
                "cache_root": None}

    if state != "passed":
        return {"ready": False, "reason": f"verification state is {state!r}",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": False, "cache_present": False, "cache_failed": False,
                "cache_root": None}

    if not archive_ready:
        return {"ready": False, "reason": "archive_ready=false",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": False, "cache_present": False, "cache_failed": False,
                "cache_root": None}

    if not verdict_sha:
        return {"ready": False, "reason": "verdict_sha missing",
                "verification_state": state, "verdict_sha": None,
                "archive_ready": archive_ready, "cache_present": False,
                "cache_failed": False, "cache_root": None}

    branch_tip = _resolve_anchor(gate_root, resolved_state_root, change_name)
    if branch_tip is None:
        return {"ready": False, "reason": "openspec/<change> branch missing",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": archive_ready, "cache_present": False,
                "cache_failed": False, "cache_root": None}
    if branch_tip != verdict_sha:
        return {"ready": False, "reason": "verdict_sha stale (branch moved)",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": archive_ready, "cache_present": False,
                "cache_failed": False, "cache_root": None}

    cache, cache_root = find_verdict_cache(gate_root, resolved_state_root, change_name)
    cache_failed = cache is not None and cache_has_failed_ac(cache_root, change_name)
    if cache_failed:
        return {"ready": False, "reason": "cache has failed AC",
                "verification_state": state, "verdict_sha": verdict_sha,
                "archive_ready": archive_ready, "cache_present": cache is not None,
                "cache_failed": True,
                "cache_root": str(cache_root) if cache_root else None}

    return {"ready": True, "reason": "",
            "verification_state": state, "verdict_sha": verdict_sha,
            "archive_ready": True, "cache_present": cache is not None,
            "cache_failed": False,
            "cache_root": str(cache_root) if cache_root else None}


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
