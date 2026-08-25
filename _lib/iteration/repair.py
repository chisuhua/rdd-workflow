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
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Archive dirs follow the format ``<YYYY>-<MM>-<DD>-<name>/``. The
# date prefix must be enforced as an exact prefix (not a suffix) to
# avoid glob matching bugs where ``*-<name>`` matches ``<YYYY>-<MM>-<DD>-
# <name>`` even when ``<name>`` itself starts with digits (e.g. ``*-08-
# 16-foo`` matches ``2026-08-16-foo`` because the dir happens to end
# with ``-08-16-foo``). See P0 fix-iteration-phantom-from-deps.
_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def _find_archive_dir(project_root: str, change_name: str) -> Optional[str]:
    """Locate the archive directory for a change.

    Returns the path of ``openspec/changes/archive/<date>-<change_name>/``
    if it exists, otherwise ``None``.

    Strict matching: the directory name MUST start with a valid
    ``<YYYY>-<MM>-<DD>-`` date prefix and, after stripping the prefix,
    the remainder MUST equal ``change_name`` exactly. The previous
    glob ``*-<change_name>`` was too permissive — it matched dirs
    whose names happened to end with the suffix (e.g. wrong-name
    "08-16-foo" matched real dir "2026-08-16-foo" because the dir
    ends with ``-08-16-foo``). See P0 fix-iteration-phantom-from-deps.
    """
    archive_base = os.path.join(project_root, "openspec", "changes", "archive")
    if not os.path.isdir(archive_base):
        return None
    try:
        entries = os.listdir(archive_base)
    except OSError:
        return None
    for entry in entries:
        m = _DATE_PREFIX_RE.match(entry)
        if not m:
            continue
        # Strip the date prefix and compare exactly to change_name.
        # This is the only correct way — suffix matching would re-introduce
        # the suffix-overlap bug we just fixed.
        remainder = entry[m.end():]
        if remainder == change_name:
            full = os.path.join(archive_base, entry)
            if os.path.isdir(full):
                return full
    # Backward-compat: also check the no-date-prefix form
    # ``openspec/changes/archive/<name>/`` (used by some legacy entries).
    legacy = os.path.join(archive_base, change_name)
    if os.path.isdir(legacy):
        return legacy
    return None


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