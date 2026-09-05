"""Wave 2 shim usage logger (per spec §4.2).

Records each invocation of legacy guide-* CLI to .rddf/state/.shim-usage.jsonl
for Wave 3 trigger condition monitoring (zero entries for >=7 consecutive days).
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def record_shim_usage(source: str, args: list, redirected_to: str, project_root: str = None) -> dict:
    """Append one entry to .rddf/state/.shim-usage.jsonl.

    Args:
        source: legacy CLI name (e.g. 'guide-design', 'guide-plan', 'guide-ship')
        args: original CLI args passed to source
        redirected_to: target CLI name (always 'rddf builder')
        project_root: project root; defaults to RDDF_PROJECT_ROOT env var or cwd

    Returns:
        dict entry that was written
    """
    if project_root is None:
        project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "args": list(args),
        "redirected_to": redirected_to,
    }

    state_dir = Path(project_root) / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    log_path = state_dir / ".shim-usage.jsonl"

    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def count_shim_usage_recent_days(days: int = 7, project_root: str = None) -> int:
    """Count shim usage entries within last `days` calendar days.

    Used by Wave 3 trigger condition: 'shim埋点 zero for >=7 days'.
    """
    if project_root is None:
        project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()

    log_path = Path(project_root) / ".rddf" / "state" / ".shim-usage.jsonl"
    if not log_path.exists():
        return 0

    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    count = 0
    with open(log_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                if ts >= cutoff:
                    count += 1
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return count