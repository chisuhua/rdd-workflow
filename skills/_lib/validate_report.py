"""Structured `openspec validate` output (ADR-0015).

`openspec-validate.json` is the machine-readable counterpart to
the human output of `openspec validate --all --strict --json`.
It lives at `.rddf/state/openspec-validate.json` (gitignored, sibling
of `deps-analysis.json` and `iteration.json`).

Why a separate JSON file rather than re-invoking the CLI?

- `gate._check_openspec_validate` runs inside transition-time
  decision logic; re-running `openspec validate` on every gate
  invocation adds latency and (for large projects) measurable cost.
- Downstream consumers (plan-done gate, future archive hooks, the
  proposed `plan.review_validation` human-in-loop menu) want
  O(structure), not O(text) — gate.py reads `summary.failed` and
  `failed_items[].id` directly.
- The JSON schema is owned by `@fission-ai/openspec`; we mirror it
  rather than re-modeling. Schema-level changes there require bumping
  the `openspec_cli_version` recorded here.

Schema (v1):
- `version`: int = 1
- `updated_at`: ISO 8601 timestamp (UTC)
- `openspec_cli_version`: str (e.g. "1.4.1") — recorded so consumers
  can warn if their stored report is from an older CLI revision.
- `passed`: bool — `summary.totals.failed == 0`
- `summary`: dict — verbatim copy of `openspec validate --json` summary.
- `failed_items`: list[dict] — every `items[]` entry whose `valid == false`,
  each with `id`, `type`, `issues`. Empty when all pass.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

logger = logging.getLogger(__name__)

REPORT_PATH_TEMPLATE = ".rddf/state/openspec-validate.json"
SCHEMA_VERSION = 1


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


def normalize_report(
    raw: dict,
    openspec_cli_version: str = "",
) -> dict:
    """Normalize a raw `openspec validate --json` payload into our persisted shape."""
    summary = raw.get("summary", {}) or {}
    totals = summary.get("totals", {}) or {}
    failed_count = int(totals.get("failed", 0))
    items = raw.get("items", []) or []
    failed_items = [
        {
            "id": it.get("id"),
            "type": it.get("type"),
            "issues": list(it.get("issues") or []),
        }
        for it in items
        if not it.get("valid", True)
    ]
    return {
        "version": SCHEMA_VERSION,
        "updated_at": _now_iso(),
        "openspec_cli_version": openspec_cli_version,
        "passed": failed_count == 0,
        "summary": summary,
        "failed_items": failed_items,
    }


def write_report(
    project_root: str,
    raw_report: dict,
    openspec_cli_version: str = "",
) -> str:
    """Persist the normalized report. Returns the absolute path written."""
    rel = REPORT_PATH_TEMPLATE
    abs_path = os.path.join(project_root, rel) if project_root else rel
    data = normalize_report(raw_report, openspec_cli_version=openspec_cli_version)
    _atomic_write(abs_path, data)
    logger.info("wrote %s (passed=%s, failed=%d)", rel, data["passed"], len(data["failed_items"]))
    return abs_path


def load_report(project_root: str = "") -> Optional[dict]:
    """Read the most recent report. Returns None if absent or unreadable."""
    rel = REPORT_PATH_TEMPLATE
    abs_path = os.path.join(project_root, rel) if project_root else rel
    if not os.path.isfile(abs_path):
        return None
    try:
        with open(abs_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("could not read %s: %s", abs_path, exc)
        return None
    return data


@dataclass
class ValidateReport:
    """Dataclass view of `.rddf/state/openspec-validate.json`.

    Mirrors the JSON schema documented in the module docstring so
    consumers can use attribute access rather than dict lookups.
    """

    version: int = SCHEMA_VERSION
    updated_at: str = ""
    openspec_cli_version: str = ""
    passed: bool = True
    summary: dict = field(default_factory=dict)
    failed_items: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ValidateReport":
        return cls(
            version=int(data.get("version", SCHEMA_VERSION)),
            updated_at=str(data.get("updated_at", "")),
            openspec_cli_version=str(data.get("openspec_cli_version", "")),
            passed=bool(data.get("passed", True)),
            summary=dict(data.get("summary") or {}),
            failed_items=list(data.get("failed_items") or []),
        )

    def to_dict(self) -> dict:
        return asdict(self)
