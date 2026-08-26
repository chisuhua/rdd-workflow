"""rdd-verifier phase Python helpers.

Per fix-rdd-verifier-lifecycle-dashboard + ADR-0034 §4.1: re-exports the
public API for use by both the CLI backend and the SKILL.md state machine.

Modules:
  - classify: heuristic failure labeling
  - cache: SHA-fingerprint verdict cache (v2 schema)
  - loop_state: per-change .verifier-loop.json load/save (migrated from global)
  - branch: implementation commit resolver (openspec/<change> branch tip)
  - discovery: eligible-change discovery from iteration lifecycle
  - audit: append-only JSONL audit log writer
"""
from _lib.verifier.classify import classify_failure  # noqa: F401
from _lib.verifier.cache import (  # noqa: F401
    verdict_cache, read_verdict_cache, is_cache_fresh, cache_has_failed_ac,
)
from _lib.verifier.loop_state import (  # noqa: F401
    load_loop_state, save_loop_state, init_loop_state, append_classification,
)
from _lib.verifier.branch import resolve_implementation_commit  # noqa: F401
from _lib.verifier.discovery import discover_eligible  # noqa: F401
from _lib.verifier.audit import write_event, read_events  # noqa: F401
from _lib.verifier.archive_gate import (  # noqa: F401
    check_archive_readiness,
    write_structured_cache_fallback,
    find_change_verification,
    resolve_branch_tip,
)

__all__ = [
    "classify_failure",
    "verdict_cache", "read_verdict_cache", "is_cache_fresh", "cache_has_failed_ac",
    "load_loop_state", "save_loop_state", "init_loop_state", "append_classification",
    "resolve_implementation_commit",
    "discover_eligible",
    "write_event", "read_events",
    "check_archive_readiness",
    "write_structured_cache_fallback",
    "find_change_verification",
    "resolve_branch_tip",
]
