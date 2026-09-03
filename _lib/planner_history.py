"""Append-only JSONL history storage for planner sprints.

Maintains `.rddf/state/.planner-history.jsonl`.
Provides safe append under FileLock, line-by-line parsing with corruption tolerance,
and explicit pruning.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from _lib.core.atomic_write import atomic_write_text
from _lib.core.lock import FileLock

logger = logging.getLogger(__name__)

HISTORY_FILENAME = ".planner-history.jsonl"


class HistoryError(Exception):
    """Base error for planner_history."""


@dataclass
class HistoryEntry:
    version: int
    sprint: str
    closed_at: str
    started_at: str
    snapshot: Dict[str, Any]


def _history_path(project_root: Path) -> Path:
    return project_root / ".rddf" / "state" / HISTORY_FILENAME


def append_history_entry(project_root: Path, entry: HistoryEntry) -> None:
    """Append a HistoryEntry line to .planner-history.jsonl under lock."""
    path = _history_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")

    line = json.dumps(asdict(entry), ensure_ascii=False) + "\n"
    with FileLock(str(lock_path), timeout=10.0):
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()


def read_history(
    project_root: Path,
) -> Tuple[List[HistoryEntry], int]:
    """Read all entries from history.

    Returns (entries, corrupt_line_count).
    Corrupted lines log a warning and are skipped.
    """
    path = _history_path(project_root)
    if not path.exists():
        return [], 0

    entries: List[HistoryEntry] = []
    corrupt_count = 0

    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                entries.append(HistoryEntry(
                    version=data.get("version", 1),
                    sprint=data["sprint"],
                    closed_at=data["closed_at"],
                    started_at=data["started_at"],
                    snapshot=data.get("snapshot", {}),
                ))
            except Exception as exc:
                corrupt_count += 1
                logger.warning("Corrupted line %d in %s: %s", idx, path, exc)

    return entries, corrupt_count


def prune_history(
    project_root: Path,
    *,
    keep: int,
    dry_run: bool = True,
) -> int:
    """Retain only the latest `keep` entries. Returns number of pruned entries."""
    if keep < 0:
        raise HistoryError("keep must be non-negative")

    path = _history_path(project_root)
    if not path.exists():
        return 0

    lock_path = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_path), timeout=10.0):
        entries, corrupt = read_history(project_root)
        if len(entries) <= keep:
            return 0

        prune_count = len(entries) - keep
        if not dry_run:
            retained = entries[prune_count:]
            content = "".join(json.dumps(asdict(e), ensure_ascii=False) + "\n" for e in retained)
            atomic_write_text(path, content)

        return prune_count
