"""Loop execution memory — history, interruption recovery, and config suggestion.

Per ADR-0006, ``LoopMemory`` records each loop execution to a JSONL file at
``.rddf/state/memory.jsonl``. The module supports:

- **Execution history** — append-only JSONL writes serialized via :class:`FileLock`
  (consistent with :class:`EventLog`).
- **Interruption recovery** — the most recent record with ``result ==
  "interrupted"`` can be retrieved to resume or roll back.
- **Repeated-failure warning** — surfaces when a change has ≥ 3 failures so
  users can pause and review before re-running.
- **Config recommendation** — Jaccard similarity on goal token sets (threshold
  ≥ 0.6) returns a config from a prior successful execution.
- **Archival** — when the record count exceeds :pyattr:`LoopMemory.MAX_RECORDS`,
  the oldest records are moved to a sibling ``memory.archive.jsonl`` file.
"""
from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from skills._lib.core.lock import FileLock
from skills._lib.core.defaults import MEMORY_PATH


# Threshold above which a past goal is considered similar enough to recommend.
_SIMILARITY_THRESHOLD = 0.6

# Number of consecutive failures for the same change that triggers a warning.
_FAILURE_WARNING_THRESHOLD = 3

# Lock acquisition timeout for memory file writes (matches EventLog convention).
_LOCK_TIMEOUT = 10.0


@dataclass
class ExecutionRecord:
    """One loop execution outcome. Serialized to JSONL on write."""

    change_name: str
    goal: str
    config: Dict[str, Any] = field(default_factory=dict)
    iterations: int = 1
    result: str = "success"  # "success" / "failure" / "interrupted"
    failure_reason: Optional[str] = None
    timestamp: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExecutionRecord":
        return cls(
            change_name=d.get("change_name", ""),
            goal=d.get("goal", ""),
            config=dict(d.get("config") or {}),
            iterations=int(d.get("iterations", 0)),
            result=d.get("result", "success"),
            failure_reason=d.get("failure_reason"),
            timestamp=d.get("timestamp", ""),
            duration_seconds=float(d.get("duration_seconds", 0.0)),
        )


def _tokenize(text: str) -> set:
    """Lowercase word tokens used for Jaccard similarity."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two sets. Returns 0.0 when both are empty."""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


class LoopMemory:
    """Execution history store backed by a JSONL file.

    Attributes:
        DEFAULT_PATH: Default JSONL path when no override is provided.
        MAX_RECORDS: Soft cap — ``archive()`` trims the oldest records when
            the count exceeds this number.
    """

    DEFAULT_PATH = MEMORY_PATH
    MAX_RECORDS = 10000

    def __init__(self, path: Optional[str] = None):
        self.path = path or self.DEFAULT_PATH
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    # ----- Read primitives ----------------------------------------------

    def _read_all(self) -> List[ExecutionRecord]:
        """Read every record on disk, skipping corrupt lines. Best-effort."""
        if not os.path.exists(self.path):
            return []
        records: List[ExecutionRecord] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    records.append(ExecutionRecord.from_dict(d))
                except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                    continue  # skip corrupt lines
        return records

    # ----- Recording ----------------------------------------------------

    def record_execution(self, record: ExecutionRecord) -> None:
        """Append one record to the JSONL log under a file lock."""
        payload = json.dumps(record.to_dict(), ensure_ascii=False)
        with FileLock(self.path + ".lock", timeout=_LOCK_TIMEOUT):
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(payload + "\n")

    # ----- History ------------------------------------------------------

    def get_execution_history(
        self,
        change_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[ExecutionRecord]:
        """Return records filtered by ``change_name`` (if given), most recent first.

        The result is bounded by ``limit`` (default 100) to keep queries fast.
        """
        records = self._read_all()
        if change_name is not None:
            records = [r for r in records if r.change_name == change_name]
        records.reverse()  # most recent first
        return records[:limit]

    def get_insights_for_change(self, change_name: str) -> Dict[str, Any]:
        """Aggregate record counts for one change."""
        records = [r for r in self._read_all() if r.change_name == change_name]
        return {
            "change_name": change_name,
            "total": len(records),
            "successes": sum(1 for r in records if r.result == "success"),
            "failures": sum(1 for r in records if r.result == "failure"),
            "interrupted": sum(1 for r in records if r.result == "interrupted"),
        }

    # ----- Suggestion ---------------------------------------------------

    def suggest_config(self, goal: str) -> Optional[Dict[str, Any]]:
        """Return config from the most-similar successful past execution.

        Uses Jaccard similarity on lowercased word tokens; returns ``None`` when
        no past execution meets :data:`_SIMILARITY_THRESHOLD`.
        """
        if not goal:
            return None
        target = _tokenize(goal)
        best_record: Optional[ExecutionRecord] = None
        best_score = 0.0
        for r in self._read_all():
            if r.result != "success":
                continue
            score = _jaccard(target, _tokenize(r.goal))
            if score >= _SIMILARITY_THRESHOLD and score > best_score:
                best_score = score
                best_record = r
        return dict(best_record.config) if best_record is not None else None

    # ----- Recovery / warnings -----------------------------------------

    def get_last_interrupted(self) -> Optional[ExecutionRecord]:
        """Return the most recent record whose ``result == "interrupted"``."""
        for r in reversed(self._read_all()):
            if r.result == "interrupted":
                return r
        return None

    def repeated_failure_warning(self, change_name: str) -> Optional[str]:
        """Return a warning string when ≥ 3 failures exist for ``change_name``."""
        failures = [
            r for r in self._read_all()
            if r.change_name == change_name and r.result == "failure"
        ]
        if len(failures) < _FAILURE_WARNING_THRESHOLD:
            return None
        last_reason = next(
            (r.failure_reason for r in reversed(failures) if r.failure_reason),
            None,
        )
        return (
            f"Change '{change_name}' has {len(failures)} failures in memory"
            + (f"; last reason: {last_reason}" if last_reason else "")
        )

    # ----- Archival -----------------------------------------------------

    def archive(self) -> int:
        """Move oldest records past :pyattr:`MAX_RECORDS` to an archive file.

        Returns the number of records archived. No-op (returns 0) when the
        record count is at or below the cap. Archive file lives next to the
        main file with a ``.archive.jsonl`` suffix.
        """
        records = self._read_all()
        if len(records) <= self.MAX_RECORDS:
            return 0

        records.sort(key=lambda r: r.timestamp)  # oldest first
        to_archive, to_keep = (
            records[: len(records) - self.MAX_RECORDS],
            records[len(records) - self.MAX_RECORDS:],
        )

        archive_path = self.path + ".archive.jsonl"
        with FileLock(self.path + ".lock", timeout=_LOCK_TIMEOUT):
            # Append the oldest records to the archive file (creates if absent)
            with open(archive_path, "a", encoding="utf-8") as f:
                for r in to_archive:
                    f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
            # Rewrite main file with only the newest MAX_RECORDS records
            with open(self.path, "w", encoding="utf-8") as f:
                for r in to_keep:
                    f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

        return len(to_archive)