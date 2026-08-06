"""L2 violation count collection (collect-l2-violation-count-on-archive, P2).

Created: collect-l2-violation-count-on-archive (P2, 2026-08-05).
Captures project-wide L2 violation count at archive time so ADR-072
target is auditable from git history.

Public API:
  collect_l2_count(project_root, change_name) — runs a grep command,
    parses integer output, updates iteration.json with
    l2_violation_count_after + l2_violation_kind.

Configurable: set RDDF_L2_COUNT_CMD env var to override default.

Failure mode: fail-open. If command fails, returns warning string;
iteration.json is NOT updated. Archive succeeds regardless.
"""
from __future__ import annotations

import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_CMD = "grep -rn '#include.*\"sim/' plugins/gpu_driver/drv/ | wc -l"
DEFAULT_KIND = "sim_include_drv"


def _resolve_cmd() -> str:
    return os.environ.get("RDDF_L2_COUNT_CMD", DEFAULT_CMD)


def _run_cmd(cmd: str, timeout: int = 10) -> int:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("collect_l2_count: command failed: %s", exc)
        return -1
    out = result.stdout.strip()
    try:
        return int(out)
    except ValueError:
        logger.warning("collect_l2_count: non-numeric output: %r", out)
        return -1


def collect_l2_count(project_root: str, change_name: str) -> Optional[str]:
    """Run the L2-count command and write to iteration.json.

    Returns None on success, warning string on failure.
    """
    cmd = _resolve_cmd()
    count = _run_cmd(cmd)
    if count < 0:
        return f"collect_l2_count: command returned invalid result for {change_name}"
    try:
        from skills._lib.iteration import store
        data = store.load(project_root)
        for c in data.get("changes", []):
            if c.get("name") == change_name:
                c["l2_violation_count_after"] = count
                c["l2_violation_kind"] = DEFAULT_KIND
                break
        else:
            return f"change {change_name} not in iteration.json"
        store.save(project_root, data)
    except Exception as exc:
        return f"collect_l2_count: failed to update iteration.json: {exc}"
    return None


__all__ = ["collect_l2_count", "DEFAULT_CMD", "DEFAULT_KIND"]
