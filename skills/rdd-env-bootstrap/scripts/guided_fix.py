"""Phase 4: Guided Fix (writes via subprocess forks).

Forks subprocesses for [auto-fixable] findings with try/except + report aggregation.
Each fix is wrapped to never crash the whole phase.

Safety principle (per fix-decisions.md):
- Only `ai-context-bootstrap: 未部署` / `块已陈旧` are auto-fixable
- No modifications to .gitignore / tracked files / .rddf/state/*.json
  (other than .env-bootstrap-report.json)
"""
from __future__ import annotations

import subprocess
from typing import Any, Callable


def run_fix(
    finding: dict[str, Any],
    command: list[str],
    target_root: str,
    timeout: int = 5,
) -> dict[str, Any]:
    """Run a single fix subprocess. Returns dict with finding/command/status/stderr.

    Never raises. Wraps TimeoutExpired + OSError as failed status.
    """
    try:
        r = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, cwd=target_root,
        )
        return {
            "finding": finding.get("message", ""),
            "command": " ".join(command),
            "status": "success" if r.returncode == 0 else "failed",
            "returncode": r.returncode,
            "stderr": (r.stderr or "")[:200],
        }
    except subprocess.TimeoutExpired as e:
        return {
            "finding": finding.get("message", ""),
            "command": " ".join(command),
            "status": "failed",
            "returncode": -1,
            "stderr": f"TimeoutExpired after {timeout}s: {str(e)[:100]}",
        }
    except OSError as e:
        return {
            "finding": finding.get("message", ""),
            "command": " ".join(command),
            "status": "failed",
            "returncode": -1,
            "stderr": f"OSError: {str(e)[:200]}",
        }


def run_guided_fix(
    auto_fixable_findings: list[dict[str, Any]],
    target_root: str,
    fix_command_for: Callable[[dict[str, Any]], list[str]],
    auto_fix: bool = False,
    confirm: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    """Phase 4 entry. Returns {executed, skipped, manual_required} dict."""
    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    manual_required: list[dict[str, Any]] = []

    for finding in auto_fixable_findings:
        cmd = fix_command_for(finding)
        should_run = auto_fix
        if not auto_fix and confirm is not None:
            should_run = confirm(f"运行 `{cmd[0]} {' '.join(cmd[1:])}`? [Y/n] ")

        if not should_run:
            skipped.append({
                "finding": finding.get("message", ""),
                "command": " ".join(cmd),
            })
            continue

        executed.append(run_fix(finding, cmd, target_root))

    return {
        "executed": executed,
        "skipped": skipped,
        "manual_required": manual_required,
    }


__all__ = ["run_fix", "run_guided_fix"]
