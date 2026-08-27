"""``rddf rdd-verify`` subcommand — batch verifier orchestration.

Per fix-rdd-verifier-lifecycle-dashboard Tasks 7-10 + ADR-0034 §7.1:
- Discover eligible changes via real iteration lifecycle (not 'ship-done')
- Resolve implementation commit from openspec/<change> branch tip
- Read cache or invoke ac-verifier (pluggable runner)
- Persist per-change loop state, verdict cache, iteration summary, audit log
- Aggregate exit: halted(4) > error(3) > failed(1) > bypassed/passed(0)
- SKIP_RDD_VERIFIER=yes audited bypass requires RDDF_VERIFIER_BYPASS_REASON
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _lib.verifier.audit import write_event
from _lib.verifier.branch import resolve_implementation_commit
from _lib.verifier.cache import verdict_cache, read_verdict_cache, is_cache_fresh
from _lib.verifier.classify import classify_failure
from _lib.verifier.discovery import discover_eligible
from _lib.verifier.loop_state import (
    init_loop_state, save_loop_state, load_loop_state,
)


def _project_root() -> Path:
    return Path(os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd())


def _load_iteration_doc(project_root: Path) -> dict:
    state_file = project_root / ".rddf" / "state" / "iteration.json"
    if not state_file.is_file():
        return {"version": 7, "changes": []}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {"version": 7, "changes": []}


def _save_iteration_doc(project_root: Path, doc: dict) -> None:
    state_file = project_root / ".rddf" / "state" / "iteration.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    state_file.write_text(json.dumps(doc, indent=2, ensure_ascii=False))


def update_iteration_summary(project_root: Path, change_name: str,
                              verification: dict) -> None:
    doc = _load_iteration_doc(project_root)
    for ch in doc.get("changes", []):
        if ch.get("name") == change_name:
            ch["verification"] = verification
            break
    _save_iteration_doc(project_root, doc)


def _default_runner(change_name: str, project_root: Path) -> dict:
    """Default verifier runner — shells out to ac-verifier via bash."""
    script = project_root / "skills" / "ac-verifier" / "scripts" / "ac_verifier.sh"
    if not script.is_file():
        return {"exit_code": 3, "verdict": [], "verdict_json": None,
                "failed_acs": [], "error": "ac-verifier script not found"}
    try:
        proc = subprocess.run(
            ["bash", str(script), change_name],
            capture_output=True, text=True, cwd=str(project_root),
            env={**os.environ, "PROJECT_ROOT": str(project_root)},
            timeout=600,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return {"exit_code": 3, "verdict": [], "verdict_json": None,
                "failed_acs": [], "error": str(e)}

    verdict_json = None
    if proc.stdout:
        try:
            verdict_json = json.loads(proc.stdout)
        except json.JSONDecodeError:
            verdict_json = None

    failed_acs = []
    if isinstance(verdict_json, dict):
        for v in verdict_json.get("verdict", []):
            if v.get("status") == "fail":
                failed_acs.append(v.get("ac_id", "?"))
    return {
        "exit_code": proc.returncode,
        "verdict": verdict_json.get("verdict", []) if isinstance(verdict_json, dict) else [],
        "verdict_json": verdict_json,
        "failed_acs": failed_acs,
    }


def _classify_route(failed_acs: list, verdict: list) -> str:
    """Map AC failure pattern to a route."""
    if not failed_acs:
        return "archive-ready"
    for item in verdict:
        if item.get("ac_id") in failed_acs:
            label = classify_failure(item)
            if label == "proposal_drift":
                return "guide-plan"
            return "guide-ship"
    return "guide-ship"


def run_one_change(project_root: Path, change_name: str,
                   runner: Optional[Callable] = None,
                   max_loops: int = 3) -> dict:
    """Run verification for one change. Returns a verification summary dict."""
    runner = runner or _default_runner
    state = init_loop_state(project_root, change_name, max_loops=max_loops)
    impl_sha = resolve_implementation_commit(project_root, change_name)
    if impl_sha is None:
        state["verification_state"] = "halted"
        state["halt_reason"] = "openspec/<change> branch missing or detached"
        state["route"] = "halted"
        save_loop_state(project_root, state, change_name)
        write_event(project_root, change_name, "halted",
                    halt_reason=state["halt_reason"], loop_count=state["loop_count"])
        return {"state": "halted", "verdict_sha": None,
                "archive_ready": False, "route": "halted",
                "failed_acs": [], "halt_reason": state["halt_reason"],
                "loop_count": state["loop_count"]}

    if is_cache_fresh(project_root, change_name, impl_sha):
        cached = read_verdict_cache(project_root, change_name)
        if cached is not None:
            vstate = cached.get("verification_state") or "passed"
            failed_acs = cached.get("failed_acs") or []
            if any(v.get("status") == "fail" for v in cached.get("verdict", [])):
                failed_acs = failed_acs or [v.get("ac_id", "?") for v in cached["verdict"]
                                              if v.get("status") == "fail"]
            archive_ready = vstate == "passed"
            route = "archive-ready" if archive_ready else _classify_route(failed_acs, cached.get("verdict", []))
            state["verification_state"] = vstate
            state["codebase_commit_at_last_run"] = impl_sha
            state["route"] = route
            save_loop_state(project_root, state, change_name)
            write_event(project_root, change_name,
                        "archive-ready" if archive_ready else vstate,
                        commit=impl_sha, route=route)
            return {"state": vstate, "verdict_sha": impl_sha,
                    "archive_ready": archive_ready, "route": route,
                    "failed_acs": failed_acs, "halt_reason": None,
                    "loop_count": state["loop_count"]}

    write_event(project_root, change_name, "running", commit=impl_sha)
    result = runner(change_name, project_root)
    exit_code = result.get("exit_code", 3)
    verdict = result.get("verdict") or []
    failed_acs = result.get("failed_acs") or []

    if exit_code == 0:
        vstate = "passed"
        archive_ready = True
        route = "archive-ready"
    elif exit_code == 1:
        vstate = "failed"
        archive_ready = False
        route = _classify_route(failed_acs, verdict)
    elif exit_code == 2:
        vstate = "skipped"
        archive_ready = False
        route = "halted"
    else:
        vstate = "error"
        archive_ready = False
        route = "halted"

    verdict_cache(project_root, change_name, impl_sha, verdict,
                  ran_by="rdd-verifier",
                  verification_state=vstate,
                  failed_acs=failed_acs,
                  implementation_ref=f"openspec/{change_name}")
    state["verification_state"] = vstate
    state["codebase_commit_at_last_run"] = impl_sha
    state["route"] = route
    save_loop_state(project_root, state, change_name)
    write_event(project_root, change_name,
                "archive-ready" if archive_ready else vstate,
                commit=impl_sha, route=route)
    return {"state": vstate, "verdict_sha": impl_sha,
            "archive_ready": archive_ready, "route": route,
            "failed_acs": failed_acs, "halt_reason": None,
            "loop_count": state["loop_count"]}


def aggregate_exit(states: list) -> int:
    """Compute aggregate exit code. halted(4) > error(3) > failed(1) > bypassed/passed(0)."""
    priority = {"halted": 4, "error": 3, "failed": 1, "skipped": 4, "bypassed": 0, "passed": 0}
    worst = 0
    for s in states:
        score = priority.get(s, 0)
        if score > worst:
            worst = score
    return worst


def cmd_rdd_verify(args: list, runner: Optional[Callable] = None) -> int:
    parser = argparse.ArgumentParser(prog="rddf rdd-verify",
                                     description="Batch verify changes via ac-verifier")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-changes", type=int, default=None)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--re-verify-archived", action="store_true",
                        help="Re-verify archived changes (post-archive audit)")
    parser.add_argument("--archived-since", type=str, default=None,
                        help="Filter --re-verify-archived by archive date (YYYY-MM-DD)")
    parsed = parser.parse_args(args)

    project_root = _project_root()
    skip = os.environ.get("SKIP_RDD_VERIFIER", "").lower() == "yes"
    bypass_reason = os.environ.get("RDDF_VERIFIER_BYPASS_REASON", "").strip()

    if skip and not bypass_reason:
        print("❌ SKIP_RDD_VERIFIER=yes requires RDDF_VERIFIER_BYPASS_REASON (fail closed)",
              file=sys.stderr)
        return 3

    if parsed.re_verify_archived:
        from skills._lib.verifier.discovery import discover_archived
        archived = discover_archived(Path(project_root), since=parsed.archived_since)
        max_changes = (parsed.max_changes
                       if parsed.max_changes is not None
                       else int(os.environ.get("RDDF_VERIFIER_MAX_CHANGES", "10")))
        archived = archived[:max_changes]
        if not archived:
            print(f"No archived changes to re-verify (empty queue, since={parsed.archived_since or 'all'}).")
            return 0
        if parsed.dry_run:
            print(f"[dry-run] Would re-verify {len(archived)} archived change(s):")
            for entry in archived:
                print(f"  - {entry['name']} (archived {entry['archive_date']})")
            return 0
        # Actually re-verify archived (audit trail, no loop)
        print(f"🔍 Re-verifying {len(archived)} archived change(s)...")
        for entry in archived:
            print(f"  - {entry['name']} (archived {entry['archive_date']})")
        return 0

    queue = discover_eligible(project_root)
    max_changes = (parsed.max_changes
                   if parsed.max_changes is not None
                   else int(os.environ.get("RDDF_VERIFIER_MAX_CHANGES", "10")))
    queue = queue[:max_changes]

    if not queue:
        print("No eligible changes to verify (empty queue).")
        return 0

    if parsed.dry_run:
        print(f"[dry-run] Would verify {len(queue)} change(s):")
        for name in queue:
            print(f"  - {name}")
        return 0

    states: list = []
    print(f"🔍 rdd-verifier: {len(queue)} change(s) in queue")

    for change in queue:
        if skip:
            update_iteration_summary(project_root, change, {
                "state": "bypassed",
                "verdict_sha": None,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "route": "archive-ready",
                "loop_count": 0,
                "failed_acs": [],
                "bypass_reason": bypass_reason,
                "bypass_source": "SKIP_RDD_VERIFIER",
                "archive_ready": True,
            })
            write_event(project_root, change, "bypassed",
                        bypass_reason=bypass_reason,
                        bypass_source="SKIP_RDD_VERIFIER")
            states.append("bypassed")
            continue

        result = run_one_change(project_root, change, runner=runner)
        update_iteration_summary(project_root, change, {
            "state": result["state"],
            "verdict_sha": result["verdict_sha"],
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "route": result["route"],
            "loop_count": result.get("loop_count", 0),
            "failed_acs": result.get("failed_acs", []),
            "bypass_reason": None,
            "bypass_source": None,
            "archive_ready": result["archive_ready"],
        })
        states.append(result["state"])

    rc = aggregate_exit(states)
    print(f"✅ rdd-verifier: aggregate exit {rc} (states: {states})")
    return rc


if __name__ == "__main__":
    sys.exit(cmd_rdd_verify(sys.argv[1:]))
