"""Structured deps analysis output.

`deps-analysis.json` is the machine-readable counterpart to
`.rddf/state/.deps-output.md` (the human-readable markdown report).
It lives at `.rddf/state/deps-analysis.json` and is the **preferred
source** for downstream consumers (notably the iteration.json sync
hook in `deps.md` Step 6 and any future "sprint planner" tooling).

Why a separate JSON file rather than parsing the markdown?
- The markdown format is for human eyes and may evolve (column
  reordering, additional columns, footnotes). Regex-parse-then-update
  is fragile.
- The JSON contract here is locked by a JSON Schema and by
  `tests/integration/test_deps_analysis.py`. Breaking changes require
  bumping `version`.
- Downstream consumers (iteration sync, future planner) want
  O(structure), not O(text).

Schema (v1):
- `version`: int = 1
- `updated_at`: ISO 8601 timestamp
- `fallback`: bool. True when deps ran in static-only mode (AI subagent
  unavailable). Consumers should treat `semantic_deps` and
  `suggestions` as empty/absent in this case.
- `changes`: dict[name, ChangeAnalysis]
- `execution_order`: list[name] in recommended order (already merged
  with parallel groups: items at the same index may run together)

ChangeAnalysis:
- `name`: str
- `phase` / `category`: from roadmap-meta.yaml (may be null)
- `status`: enum "ready" | "blocked_by" | "prerequisite" | "conflict"
- `blocker`: change name that hard-blocks this one (null if ready)
- `blocks`: list[change name] this change blocks
- `parallel_group`: int. 0 = first wave (no deps), 1 = depends on wave 0, ...
- `conflicts`: list[change name] with file-level conflicts
- `confidence`: "high" | "low" (low = AI-inferred only, no static evidence)
- `recommendation`: human-readable execution hint
"""
from __future__ import annotations

import datetime
import json
import logging
import os
from typing import Any, Optional

from skills._lib.lock import FileLock, LockTimeout

logger = logging.getLogger(__name__)

ANALYSIS_PATH_TEMPLATE = ".rddf/state/deps-analysis.json"
SCHEMA_VERSION = 1
_LOCK_TIMEOUT = 5.0


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _atomic_write(path: str, data: dict) -> None:
    target_dir = os.path.dirname(path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_analysis(
    changes: list[dict],
    execution_order: Optional[list[str]] = None,
    fallback: bool = True,
) -> dict:
    """Build a deps-analysis.json structure from per-change records.

    `changes` is a list of dicts, one per analyzed change, each with
    fields:
      - name (str, required)
      - phase, category (str | None)
      - status: "ready" | "blocked_by" | "prerequisite" | "conflict"
      - blocker (str | None)
      - blocks (list[str])
      - parallel_group (int)
      - conflicts (list[str])
      - confidence (str)
      - recommendation (str)

    `execution_order` defaults to the input order, filtered to only
    include names that appear in `changes`.
    """
    change_map = {}
    for c in changes:
        if "name" not in c:
            raise ValueError("each change record requires 'name'")
        # Normalize defaults
        record = {
            "name": c["name"],
            "phase": c.get("phase"),
            "category": c.get("category"),
            "status": c.get("status", "ready"),
            "blocker": c.get("blocker"),
            "blocks": list(c.get("blocks", [])),
            "parallel_group": int(c.get("parallel_group", 0)),
            "conflicts": list(c.get("conflicts", [])),
            "confidence": c.get("confidence", "high"),
            "recommendation": c.get("recommendation", ""),
        }
        change_map[c["name"]] = record

    if execution_order is None:
        execution_order = [c["name"] for c in changes]
    else:
        # Filter to only include known changes, preserving order
        known = set(change_map.keys())
        execution_order = [n for n in execution_order if n in known]

    return {
        "version": SCHEMA_VERSION,
        "updated_at": _now_iso(),
        "fallback": fallback,
        "changes": change_map,
        "execution_order": execution_order,
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def write_analysis(project_root: str, data: dict) -> str:
    """Write deps-analysis.json atomically with merge-on-save by change name.

    See iteration.save for the rationale on merge-on-save. Briefly:
    two hooks both reading state, both mutating different entries,
    second save overwriting first is the lost-update bug. Merging
    inside the lock prevents it.

    Raises LockTimeout on contention beyond timeout.
    """
    path = os.path.join(project_root, ANALYSIS_PATH_TEMPLATE)
    lock_path = path + ".lock"
    with FileLock(lock_path, timeout=_LOCK_TIMEOUT):
        # Re-read inside the lock and merge by change name. Incoming wins.
        existing = _load_unlocked(path)
        if existing is not None:
            data = dict(data)
            existing_by_name = dict(existing.get("changes", {}))
            existing_by_name.update(data.get("changes", {}))
            data["changes"] = existing_by_name
            data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        _atomic_write(path, data)
    logger.debug("deps-analysis.json written to %s (%d changes)", path, len(data.get("changes", {})))
    return path


def _load_unlocked(path: str) -> Optional[dict]:
    """Read deps-analysis.json without acquiring the lock."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict) or data.get("version") != SCHEMA_VERSION:
        return None
    if "changes" not in data or not isinstance(data["changes"], dict):
        return None
    return data


def load_analysis(project_root: str) -> Optional[dict]:
    """Load deps-analysis.json. Returns None if missing or invalid.

    Consumers should treat None as "deps has not run yet" and skip
    iteration sync. The deps.md Step 6 hook falls back to markdown
    parsing when JSON is unavailable.
    """
    path = os.path.join(project_root, ANALYSIS_PATH_TEMPLATE)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("deps-analysis.json at %s unreadable: %s", path, e)
        return None
    if not isinstance(data, dict) or data.get("version") != SCHEMA_VERSION:
        logger.warning(
            "deps-analysis.json at %s has wrong version: %s (expected %s)",
            path, data.get("version"), SCHEMA_VERSION,
        )
        return None
    if "changes" not in data or not isinstance(data["changes"], dict):
        logger.warning("deps-analysis.json at %s has malformed 'changes' field", path)
        return None
    return data


# ---------------------------------------------------------------------------
# Iteration sync helper (used by deps.md Step 6)
# ---------------------------------------------------------------------------

def sync_iteration_from_analysis(project_root: str, iteration_module: Any) -> int:
    """Sync iteration.json from deps-analysis.json.

    Returns the number of changes updated. 0 means nothing to do
    (deps-analysis.json missing, or all changes already up to date).
    Raises nothing on failure: logs and returns 0.
    """
    analysis = load_analysis(project_root)
    if analysis is None:
        return 0

    data = iteration_module.load(project_root)
    count = 0
    for name, info in analysis.get("changes", {}).items():
        kwargs = {
            "name": name,
            "blocker": info.get("blocker"),
            "parallel_group": info.get("parallel_group", 0),
            "conflicts": info.get("conflicts", []),
        }
        data = iteration_module.set_deps_info(data, **kwargs)
        count += 1
    if count > 0:
        iteration_module.save(project_root, data)
    return count
