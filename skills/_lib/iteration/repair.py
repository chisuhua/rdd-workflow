"""On-disk reconciliation helpers for iteration.json after archive.

When ``mark_iteration_archived`` (bash wrapper around
``sync_iteration_after_archive``) fails to update iteration.json — typically
due to a transient exception in the Python helper — this module provides a
deterministic fallback: scan the on-disk archive directory and force-set
the iteration entry.

Public surface:
    - ``force_mark_archived(project_root, change_name, archive_commit_sha=None)``
      Returns ``True`` if iteration.json was modified, ``False`` on no-op.
"""
from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _find_archive_dir(project_root: str, change_name: str) -> Optional[str]:
    """Locate the archive directory for a change.

    Returns the path of ``openspec/changes/archive/<date>-<change_name>/``
    if it exists, otherwise ``None``.
    """
    pattern = os.path.join(
        project_root, "openspec", "changes", "archive", f"*-{change_name}"
    )
    matches = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    return matches[0] if matches else None


def force_mark_archived(
    project_root: str,
    change_name: str,
    archive_commit_sha: Optional[str] = None,
) -> bool:
    """Force-mark a change as archived in iteration.json from on-disk truth.

    Returns ``True`` if iteration.json was modified, ``False`` if no-op.

    Idempotent: if the entry already has ``archived_at``, only forces
    ``status`` to 'archived' (preserves the original timestamp). A second
    call when nothing changed returns ``False``.
    """
    archive_dir = _find_archive_dir(project_root, change_name)
    if archive_dir is None:
        return False

    iter_file = Path(project_root) / ".rddf" / "state" / "iteration.json"
    if not iter_file.is_file():
        return False

    try:
        data = json.loads(iter_file.read_text())
    except (json.JSONDecodeError, OSError):
        return False

    changes = data.get("changes", [])
    existing = None
    for c in changes:
        if c.get("name") == change_name:
            existing = c
            break
    if existing is None:
        # Create a synthetic entry so future lookups don't fail.
        existing = {
            "name": change_name,
            "added_at": datetime.now(timezone.utc).isoformat(),
        }
        changes.append(existing)

    fields: dict = {}
    if existing.get("status") != "archived":
        fields["status"] = "archived"
    if "archived_at" not in existing:
        fields["archived_at"] = datetime.now(timezone.utc).isoformat()
    if archive_commit_sha and "archive_commit_sha" not in existing:
        fields["archive_commit_sha"] = archive_commit_sha

    if not fields:
        return False

    existing.update(fields)
    data["changes"] = changes

    iter_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return True