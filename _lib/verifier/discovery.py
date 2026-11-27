"""Discover verifier-eligible changes **from disk**.

Eligibility (rule semantics unchanged — only the source moved):

- the change lives under ``openspec/changes/<name>/`` and has a ``tasks.md``
  (archived changes are out of scope by construction: they live under
  ``openspec/changes/archive/``);
- its disk-derived status is ``in_worktree`` or ``completed``;
- its task counter is non-zero and fully checked.

``iteration.json`` is **not consulted** — it is procedural bookkeeping, not the
truth source (per change ``rddf-status-based-on-improvements``). Two failures
disappeared with that: a missing file no longer empties the queue silently, and
a stale entry can no longer override what is on disk. The status derivation is
shared with ``rddf status`` Mode A (``_lib/change_status.derive_status``) so
there is exactly one implementation of "what status is this change".
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from _lib.change_status import derive_status as _derive
from _lib.tasks_count import count_tasks

_ARCHIVED = {"archived", "archived_partial"}
_IMPLEMENTED = {"in_worktree", "completed"}

#: Changes whose disk status makes them verification candidates.
_ELIGIBLE_STATUSES = _IMPLEMENTED


def _is_eligible(change: dict) -> bool:
    """Rule predicate for a single change dict (kept for its unit tests).

    ``derive_status`` answers the status half from disk; this function stays
    the one place the *rule* is spelled out.
    """
    status = change.get("status")
    if status in _ARCHIVED:
        return False
    if status not in _IMPLEMENTED:
        return False
    done = change.get("tasks_done") or 0
    total = change.get("tasks_total") or 0
    if total <= 0:
        return False
    return done == total


@dataclass(frozen=True)
class DiscoveryResult:
    """Outcome of a queue scan — never a silent empty list.

    ``reasons`` explains an empty queue (one line per cause); ``notices``
    carries non-fatal remarks such as "iteration.json disagrees with disk".
    """

    eligible: list = field(default_factory=list)
    reasons: list = field(default_factory=list)
    notices: list = field(default_factory=list)


def _iteration_statuses(project_root: Path) -> dict:
    """``{name: status}`` from ``iteration.json`` (empty when absent/corrupt).

    Used **only** to report staleness — never to include or exclude a change.
    """
    state_file = project_root / ".rddf" / "state" / "iteration.json"
    if not state_file.is_file():
        return {}
    try:
        doc = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}
    out = {}
    for change in doc.get("changes", []):
        name = change.get("name")
        if name:
            out[name] = change.get("status")
    return out


def discover_eligible_detailed(project_root: Path) -> DiscoveryResult:
    """Scan ``openspec/changes/*/tasks.md`` and classify each active change."""
    root = Path(project_root)
    changes_dir = root / "openspec" / "changes"
    if not changes_dir.is_dir():
        return DiscoveryResult(
            eligible=[],
            reasons=["no active change under openspec/changes/"],
        )

    iteration = _iteration_statuses(root)
    eligible: list = []
    notices: list = []
    incomplete: list = []
    complete_but_not_implemented: list = []

    for entry in sorted(changes_dir.iterdir()):
        if not entry.is_dir() or entry.name == "archive":
            continue
        tasks_file = entry / "tasks.md"
        if not tasks_file.is_file():
            continue
        try:
            done, total = count_tasks(tasks_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        status = _derive(str(root), entry.name)

        recorded = iteration.get(entry.name)
        if recorded is not None and (recorded in _ELIGIBLE_STATUSES) != (
            status in _ELIGIBLE_STATUSES
        ):
            # Only a **verdict-changing** disagreement is worth a notice: every
            # planned change disagreeing on wording ('proposed' vs 'planned')
            # would otherwise bury the signal.
            notices.append(
                f"iteration.json records '{entry.name}' as '{recorded}' but disk says "
                f"'{status}' ⇒ disk wins"
            )

        if total <= 0:
            continue
        if done != total:
            incomplete.append(entry.name)
            continue
        if status in _ELIGIBLE_STATUSES:
            eligible.append(entry.name)
        else:
            complete_but_not_implemented.append(entry.name)

    reasons: list = []
    if not eligible:
        if not any(changes_dir.iterdir()):
            reasons.append("no active change under openspec/changes/")
        elif incomplete:
            reasons.append(
                f"no change has all tasks checked ({len(incomplete)} change(s) incomplete: "
                f"{', '.join(incomplete[:5])})"
            )
        if complete_but_not_implemented:
            reasons.append(
                "task-complete change(s) whose disk status is neither in_worktree nor "
                f"completed: {', '.join(complete_but_not_implemented[:5])}"
            )
        if not reasons:
            reasons.append(
                "no change under openspec/changes/ has a tasks.md with checked tasks"
            )
    return DiscoveryResult(eligible=eligible, reasons=reasons, notices=notices)


def discover_eligible(project_root: Path) -> list:
    """Return the names of changes eligible for verification (ordered)."""
    return discover_eligible_detailed(project_root).eligible


def discover_archived(project_root: Path, since: Optional[str] = None) -> list:
    """Return list of archived change names for post-archive audit.

    Per verifier-re-verify-archived-flag proposal:
    - Scans openspec/changes/archive/<date>-<name>/ directories
    - Optionally filters by archive date prefix (since=YYYY-MM-DD)
    - Returns [{name, archive_date}] dicts

    Args:
        project_root: absolute path to project root
        since: optional ISO date (YYYY-MM-DD); only include changes archived on/after this date

    Returns:
        List of dicts {name, archive_date, archive_path}
    """
    archive_root = Path(project_root) / "openspec" / "changes" / "archive"
    if not archive_root.is_dir():
        return []

    since_date = None
    if since:
        try:
            since_date = date.fromisoformat(since)
        except ValueError:
            since_date = None  # invalid → ignore filter

    results = []
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")
    for entry in sorted(archive_root.iterdir()):
        if not entry.is_dir():
            continue
        m = pattern.match(entry.name)
        if not m:
            continue
        archive_date_str, change_name = m.group(1), m.group(2)
        if since_date:
            try:
                entry_date = date.fromisoformat(archive_date_str)
                if entry_date < since_date:
                    continue
            except ValueError:
                continue
        results.append({
            "name": change_name,
            "archive_date": archive_date_str,
            "archive_path": str(entry),
        })
    return results
