"""``rddf builder ...`` subcommand dispatcher (per spec §5.2).

Subcommands: run / phase0 / phase1 / phase1.5 / phase2 / phase2.5 / phase3 /
list / status / --help.

Pause contract (per spec §5.2):
- HARD pause at Phase 0 / 2.5 (cannot bypass)
- SOFT pause at Phase 1 / 1.5 / verifier back-route (skippable via --no-pause)
- --from-phase N: resume from phase N
- --retry-on-fail: auto-back-route on verifier verdict

Exit codes (per spec §5.2 / Oracle H4):
- 0 = success
- 1 = Phase 0 rejected/deferred
- 2 = plan quality FAIL
- 3 = worktree / COMMIT GATE fail
- 4 = verifier halted
- 5 = review revise/abandon
- 6 = deps gate FAIL
- 7 = archive gate FAIL
"""
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PHASES_SCRIPT_MAP = {
    "phase0": "approval",
    "phase1": "plan",
    "phase1.5": "deps",
    "phase2": "execute",
    "phase2.5": "review",
    "phase3": "archive",
}


def _help_text() -> str:
    return """rddf builder — v4 stage-merge builder (per spec §5.2)

Usage:
  rddf builder run <change> [--no-pause] [--from-phase N] [--retry-on-fail]
  rddf builder phase0 <change>
  rddf builder phase1 <change>
  rddf builder phase1.5 <change>
  rddf builder phase2 <change>
  rddf builder phase2.5 <change>
  rddf builder phase3 <change>
  rddf builder list
  rddf builder status <change>
  rddf builder --help

Pause contract:
  HARD pause: Phase 0 / 2.5 (cannot bypass via --no-pause)
  SOFT pause: Phase 1 / 1.5 / verifier back-route (--no-pause skips)

Exit codes:
  0 = success
  1 = Phase 0 rejected/deferred
  2 = plan quality FAIL
  3 = worktree / COMMIT GATE fail
  4 = verifier halted (retry exceeded or needs_human)
  5 = review revise/abandon
  6 = deps gate FAIL (STRICT_DEPS_GATE)
  7 = archive gate FAIL
"""


def cmd_builder(args, project_root=None, **kwargs) -> int:
    project_root = project_root or os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    if not args or args[0] in ("--help", "-h"):
        print(_help_text())
        return 0
    subcommand = args[0]
    if subcommand == "run":
        return _cmd_run(args[1:], project_root)
    elif subcommand in PHASES_SCRIPT_MAP:
        return _cmd_phase(subcommand, args[1:], project_root)
    elif subcommand == "list":
        return _cmd_list(project_root)
    elif subcommand == "status":
        change_name = args[1] if len(args) > 1 else None
        return _cmd_status(change_name, project_root)
    else:
        print(f"Unknown subcommand: {subcommand}", file=sys.stderr)
        print(_help_text())
        return 2


def _cmd_run(args, project_root):
    if not args:
        print("run requires <change-name>", file=sys.stderr)
        return 2
    change_name = args[0]
    no_pause = "--no-pause" in args
    retry_on_fail = "--retry-on-fail" in args

    from_phase = 0
    if "--from-phase" in args:
        idx = args.index("--from-phase")
        if idx + 1 < len(args):
            try:
                from_phase = int(args[idx + 1])
            except ValueError:
                print("--from-phase requires integer", file=sys.stderr)
                return 2

    from _lib.builder_handoff import read_builder_handoff, write_builder_handoff
    if not read_builder_handoff(project_root, change_name):
        write_builder_handoff(
            project_root=project_root,
            change_name=change_name,
            current_phase=f"phase-{from_phase}",
            approval_status="pending",
        )

    PHASES = [
        ("phase0", True),
        ("phase1", False),
        ("phase1.5", False),
        ("phase2", False),
        ("phase2.5", True),
        ("phase3", False),
    ]

    for i, (phase, is_hard_pause) in enumerate(PHASES):
        phase_num = i
        if phase_num < from_phase:
            continue

        script_path = Path(project_root) / f"skills/rdd-builder/scripts/{phase}_{PHASES_SCRIPT_MAP[phase]}.sh"
        if not script_path.is_file():
            print(f"{phase}: script not found at {script_path}", file=sys.stderr)
            return 3

        proc = subprocess.run(
            ["bash", str(script_path), change_name],
            cwd=str(project_root),
        )
        phase_exit = proc.returncode

        if is_hard_pause and phase_exit == 0:
            try:
                user_input = input(f"\n[PAUSE] {phase} completed. Type 'continue' to proceed: ")
            except EOFError:
                user_input = ""
            if user_input.strip() != "continue":
                print(f"user declined at HARD pause after {phase}")
                return phase_exit if phase_exit != 0 else 5
            handoff = read_builder_handoff(project_root, change_name)
            handoff.setdefault("phase_pause_history", []).append({
                "phase_transition": f"{phase}->next",
                "pause_type": "hard",
                "skipped": False,
                "user_input": user_input.strip(),
                "at": datetime.now(timezone.utc).isoformat(),
            })
            write_builder_handoff(project_root, change_name, **handoff)

        elif (not is_hard_pause) and (not no_pause) and phase_exit == 0:
            try:
                user_input = input(f"\n[PAUSE] {phase} completed. Type 'continue' to proceed (Ctrl+C to abort): ")
            except EOFError:
                user_input = ""
            if user_input.strip() != "continue":
                print(f"user declined at SOFT pause after {phase}")
                return 5
            handoff = read_builder_handoff(project_root, change_name)
            handoff.setdefault("phase_pause_history", []).append({
                "phase_transition": f"{phase}->next",
                "pause_type": "soft",
                "skipped": False,
                "user_input": user_input.strip(),
                "at": datetime.now(timezone.utc).isoformat(),
            })
            write_builder_handoff(project_root, change_name, **handoff)

        if phase_exit != 0:
            if phase == "phase3" and retry_on_fail:
                from _lib.builder_retry import route_verifier_verdict
                decision = route_verifier_verdict(verifier_exit_code=phase_exit)
                if decision["should_back_route"]:
                    back_phase = decision["next_phase"]
                    back_num = {"phase-1": 1, "phase-2": 3}.get(back_phase, 0)
                    if back_num > 0:
                        return _cmd_run(
                            [change_name, "--from-phase", str(back_num)] +
                            (["--no-pause"] if no_pause else []) +
                            (["--retry-on-fail"] if retry_on_fail else []),
                            project_root,
                        )
            return phase_exit

    print(f"builder run {change_name}: all 6 phases completed")
    return 0


def _cmd_phase(phase, args, project_root):
    change_name = args[0] if args else None
    if not change_name:
        print(f"{phase} requires <change-name>", file=sys.stderr)
        return 2
    script_path = Path(project_root) / f"skills/rdd-builder/scripts/{phase}_{PHASES_SCRIPT_MAP[phase]}.sh"
    if not script_path.is_file():
        print(f"{phase}: script not found at {script_path}", file=sys.stderr)
        return 3
    result = subprocess.run(
        ["bash", str(script_path), change_name],
        cwd=str(project_root),
    )
    return result.returncode


def _cmd_list(project_root):
    builder_dir = Path(project_root) / ".rddf" / "state" / "builder"
    if not builder_dir.exists():
        print("(no active builder changes)")
        return 0
    for f in sorted(builder_dir.glob("*.json")):
        print(f.stem)
    return 0


def _cmd_status(change_name, project_root):
    if not change_name:
        print("status requires <change-name>", file=sys.stderr)
        return 2
    handoff_path = Path(project_root) / ".rddf" / "state" / "builder" / f"{change_name}.json"
    if not handoff_path.exists():
        print(f"(no builder state for {change_name})")
        return 0
    import json
    data = json.loads(handoff_path.read_text())
    print(f"change: {change_name}")
    print(f"phase: {data.get('current_phase')}")
    print(f"retry_count: {data.get('retry_count')} / {data.get('max_retries')}")
    print(f"pause_history entries: {len(data.get('phase_pause_history', []))}")
    return 0