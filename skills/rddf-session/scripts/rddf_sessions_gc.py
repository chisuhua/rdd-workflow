#!/usr/bin/env python3
"""Garbage collection for stale rddf-sessions."""
import json, os, sys, datetime

def gc_sessions(project_root: str, dry_run: bool = True, max_age_days: int = 7) -> int:
    path = os.path.join(project_root, ".rddf", "state", "sessions.json")
    if not os.path.exists(path):
        return 0

    with open(path) as f:
        data = json.load(f)

    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=max_age_days)
    remaining = []
    removed = []

    for session in data.get("sessions", []):
        owner = session.get("owner_opencode_session_id", "")
        status = session.get("status", "")
        started = session.get("started_at", "")

        is_stale = (
            owner == "current" and
            status in ("abandoned", "orphaned") and
            started
        )
        if is_stale:
            try:
                session_time = datetime.datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ")
                if session_time < cutoff:
                    removed.append(session.get("id", "unknown"))
                    if not dry_run:
                        continue
            except ValueError:
                pass
        remaining.append(session)

    if not dry_run:
        data["sessions"] = remaining
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    return len(removed)

if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    project_root = "."
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            project_root = arg
    removed = gc_sessions(project_root, dry_run=dry)
    mode = "Would remove" if dry else "Removed"
    print(f"{mode} {removed} stale session(s)")
